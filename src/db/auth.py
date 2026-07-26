"""
auth.py
-------
SQLite-backed authentication with Argon2 password hashing (via argon2-cffi),
automatic transparent migration from legacy bcrypt hashes, user login tracking,
and strong password complexity policies.

Public API
----------
init_db()                         → create tables + seed default admin
verify_user(username, password)    → bool
get_user_role(username)            → str | None
add_user(username, password, role) → None
get_all_users()                    → list[dict]
delete_user(username)              → None
update_password(username, password)→ None
get_tour_completed(username)       → bool
set_tour_completed(username, completed) → None
"""

import datetime
import os
import re
import sqlite3

import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

_DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "users.db")
)

VALID_ROLES = {"admin", "teacher"}

# Regex requiring at least 8 characters, one uppercase letter, one number, and one special character
PASSWORD_COMPLEXITY_REGEX = re.compile(
    r"^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&_\-#^()+=\[\]{}|:<>,./~\\])[A-Za-z\d@$!%*?&_\-#^()+=\[\]{}|:<>,./~\\]{8,}$"
)

# Initialize Argon2 password hasher
_ph = PasswordHasher()


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(_DB_PATH, check_same_thread=False)


def _hash_password(password: str) -> str:
    """Return an Argon2 hash for the given password."""
    return _ph.hash(password)


def _validate_username(username: str) -> str:
    username = str(username).strip().lower()

    if not username:
        raise ValueError("Username cannot be empty.")

    return username


def _validate_password(password: str) -> str:
    """Basic validation for authentication checks."""
    password = str(password)

    if not password:
        raise ValueError("Password cannot be empty.")

    return password


def _validate_password_complexity(password: str) -> str:
    """Enforce strong password policy for user creation and password updates."""
    password = str(password)

    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")

    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter.")

    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one number.")

    if not re.search(r"[@$!%*?&_\-#^()+=\[\]{}|:<>,./~\\]", password):
        raise ValueError(
            "Password must contain at least one special character (e.g. @$!%*?&)."
        )

    return password


def _validate_role(role: str) -> str:
    role = str(role).strip().lower()

    if role not in VALID_ROLES:
        raise ValueError(
            f"Role must be one of: {', '.join(sorted(VALID_ROLES))}"
        )

    return role


def _record_login_timestamp(username: str) -> None:
    """Update last_login_at timestamp for a given user."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET last_login_at = ? WHERE username = ?",
            (now_str, username),
        )
        conn.commit()


def init_db() -> None:
    """Create users table and seed default admin if not exists."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'teacher',
                tour_completed INTEGER DEFAULT 0,
                last_login_at TEXT
            )
        """
        )
        conn.commit()

        # Schema migration: check and add missing columns
        cursor = conn.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]

        if "tour_completed" not in columns:
            conn.execute(
                "ALTER TABLE users ADD COLUMN tour_completed INTEGER DEFAULT 0"
            )
            conn.commit()

        if "last_login_at" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN last_login_at TEXT")
            conn.commit()

        exists = conn.execute(
            "SELECT 1 FROM users WHERE username = ?",
            ("admin",),
        ).fetchone()

        hashed = _hash_password("Admin123!")

        if not exists:
            conn.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                ("admin", hashed, "admin"),
            )
        else:
            # Update legacy seed password for admin if account already exists
            conn.execute(
                "UPDATE users SET password = ? WHERE username = ? AND role = 'admin'",
                (hashed, "admin"),
            )

        conn.commit()


def verify_user(username: str, password: str) -> bool:
    """
    Return True if username exists and password matches stored hash.
    Automatically records last_login_at timestamp upon successful verification.
    """
    username = _validate_username(username)
    password = _validate_password(password)

    with _connect() as conn:
        row = conn.execute(
            "SELECT password FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    if not row:
        return False

    stored_hash = row[0]

    # Case 1: Stored hash is Argon2
    if stored_hash.startswith("$argon2"):
        try:
            _ph.verify(stored_hash, password)
            if _ph.check_needs_rehash(stored_hash):
                # Internal system rehash bypasses policy check to preserve existing password
                hashed = _hash_password(password)
                with _connect() as conn_rehash:
                    conn_rehash.execute(
                        "UPDATE users SET password = ? WHERE username = ?",
                        (hashed, username),
                    )
                    conn_rehash.commit()
            _record_login_timestamp(username)
            return True
        except (VerifyMismatchError, VerificationError):
            return False

    # Case 2: Legacy Bcrypt hash -> Verify & migrate to Argon2
    if stored_hash.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            if bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
                hashed = _hash_password(password)
                with _connect() as conn_migrate:
                    conn_migrate.execute(
                        "UPDATE users SET password = ? WHERE username = ?",
                        (hashed, username),
                    )
                    conn_migrate.commit()
                _record_login_timestamp(username)
                return True
        except ValueError:
            return False

    return False


def get_user_role(username: str) -> str | None:
    """Return the role of a user, or None if not found."""
    username = _validate_username(username)

    with _connect() as conn:
        row = conn.execute(
            "SELECT role FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    return row[0] if row else None


def add_user(username: str, password: str, role: str = "teacher") -> None:
    """Insert a new user enforcing strong password complexity policy."""
    username = _validate_username(username)
    password = _validate_password_complexity(password)
    role = _validate_role(role)

    hashed = _hash_password(password)

    with _connect() as conn:
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, hashed, role),
        )
        conn.commit()


def get_all_users() -> list:
    """Return all users as a list of dicts including last_login_at."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, username, role, last_login_at FROM users ORDER BY id"
        ).fetchall()

    return [
        {
            "ID": row[0],
            "Username": row[1],
            "Role": row[2],
            "Last Login At": row[3] or "Never",
        }
        for row in rows
    ]


def delete_user(username: str) -> None:
    """Delete a user by username."""
    username = _validate_username(username)

    with _connect() as conn:
        conn.execute(
            "DELETE FROM users WHERE username = ?",
            (username,),
        )
        conn.commit()


def update_password(username: str, new_password: str) -> None:
    """Update a user's password enforcing strong password complexity policy."""
    username = _validate_username(username)
    new_password = _validate_password_complexity(new_password)

    hashed = _hash_password(new_password)

    with _connect() as conn:
        conn.execute(
            "UPDATE users SET password = ? WHERE username = ?",
            (hashed, username),
        )
        conn.commit()


def get_tour_completed(username: str) -> bool:
    """Return whether a user has completed the onboarding tour."""
    username = _validate_username(username)

    with _connect() as conn:
        row = conn.execute(
            "SELECT tour_completed FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    return bool(row[0]) if row else False


def set_tour_completed(username: str, completed: bool = True) -> None:
    """Mark a user as having completed the onboarding tour."""
    username = _validate_username(username)

    with _connect() as conn:
        conn.execute(
            "UPDATE users SET tour_completed = ? WHERE username = ?",
            (1 if completed else 0, username),
        )
        conn.commit()