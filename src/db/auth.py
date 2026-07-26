from __future__ import annotations
import json
import logging
import os
import re
import sqlite3
import tempfile
import datetime

import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

from src.db.migrations import migrate_auth_database
import logging


logger = logging.getLogger(__name__)

_DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "users.db")
)

VALID_ROLES = {"admin", "teacher"}

PASSWORD_COMPLEXITY_REGEX = re.compile(
    r"^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&_\-#^()+=\[\]{}|:<>,./~\\])[A-Za-z\d@$!%*?&_\-#^()+=\[\]{}|:<>,./~\\]{8,}$"
)

_ph = PasswordHasher()


def configure_db_path(db_path: str | os.PathLike) -> None:
    """Configure the SQLite database path used by the authentication module."""
    global _DB_PATH
    _DB_PATH = os.path.abspath(os.fspath(db_path))


def _connect() -> sqlite3.Connection:
    path = os.path.abspath(_DB_PATH)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return sqlite3.connect(path, check_same_thread=False)
    except (sqlite3.OperationalError, OSError, PermissionError):
        path = os.path.join(tempfile.gettempdir(), "semantic_plagiarism_detector", "data", "users.db")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return sqlite3.connect(path, check_same_thread=False)


def log_security_event(
    event_type: str,
    username: str,
    details: str | None = None,
) -> None:
    """Record a security-relevant event in the security_audit_log table."""
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO security_audit_log (event_type, username, timestamp, details)
                VALUES (?, ?, ?, ?)
                """,
                (event_type, username, timestamp, details),
            )
            conn.commit()
    except Exception as exc:  # pragma: no cover
        logger.warning(
            "Failed to write security audit log entry [%s, %s]: %s",
            event_type,
            username,
            exc,
        )


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
        raise ValueError(f"Role must be one of: {', '.join(sorted(VALID_ROLES))}")
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
    """Create or upgrade users.db and seed the default administrator."""
    try:
        with _connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'teacher'
                )
                """
            )
            conn.commit()
            migrate_auth_database(conn)

            # Check for admin
            row = conn.execute(
                "SELECT COUNT(1) FROM users WHERE username = ?",
                ("admin",),
            ).fetchone()
            exists = bool(row and row[0])

            if not exists:
                hashed = _hash_password("Admin123!")
                conn.execute(
                    """
                    INSERT INTO users (username, password, role)
                    VALUES (?, ?, ?)
                    """,
                    ("admin", hashed, "admin"),
                )
                conn.commit()
    except sqlite3.Error as e:
        raise sqlite3.Error(f"Failed to initialize authentication database: {e}") from e

    try:
        os.chmod(_DB_PATH, 0o600)
    except OSError:
        pass


def verify_user(username: str, password: str) -> bool:
    """
    Return True if username exists, account is active, and password matches.
    Automatically migrates legacy bcrypt hashes to Argon2.
    """
    try:
        username = _validate_username(username)
        password = _validate_password(password)
    except ValueError:
        return False

    with _connect() as conn:
        row = conn.execute(
            "SELECT password, is_active FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    if not row:
        return False

    stored_hash, is_active = row
    if not is_active:
        return False

    is_valid = False
    needs_rehash = False

    if stored_hash.startswith("$argon2"):
        try:
            _ph.verify(stored_hash, password)
            is_valid = True
            if _ph.check_needs_rehash(stored_hash):
                needs_rehash = True
        except (VerifyMismatchError, VerificationError):
            return False
    elif stored_hash.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            if bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
                is_valid = True
                needs_rehash = True
        except ValueError:
            return False

    if is_valid:
        if needs_rehash:
            # Rehash bypasses policy check to preserve existing password
            hashed = _hash_password(password)
            with _connect() as conn_rehash:
                conn_rehash.execute(
                    "UPDATE users SET password = ? WHERE username = ?",
                    (hashed, username),
                )
                conn_rehash.commit()
        
        _record_login_timestamp(username)
        return True
    
    return False

# Alias for compatibility
authenticate_user = verify_user


def get_user_role(username: str) -> str | None:
    try:
        username = _validate_username(username)
        with _connect() as conn:
            row = conn.execute(
                "SELECT role FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            return row[0] if row else None
    except sqlite3.Error as e:
        raise sqlite3.Error(f"Failed to retrieve user role: {e}") from e


def get_user_roles(user_ids: list[int]) -> dict[int, str]:
    if not user_ids:
        return {}
    try:
        placeholders = ",".join("?" for _ in user_ids)
        with _connect() as conn:
            rows = conn.execute(
                f"SELECT id, role FROM users WHERE id IN ({placeholders})",
                user_ids,
            ).fetchall()
            return {row[0]: row[1] for row in rows}
    except sqlite3.Error as e:
        raise sqlite3.Error(f"Failed to batch query user roles: {e}") from e


def add_user(username: str, password: str, role: str = "teacher") -> None:
    try:
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
    except sqlite3.IntegrityError as e:
        raise ValueError(f"Username '{username}' already exists.") from e
    except sqlite3.Error as e:
        raise sqlite3.Error(f"Failed to add user: {e}") from e



def get_all_users() -> list:
    try:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT id, username, role, is_active, last_login_at FROM users ORDER BY id"
            ).fetchall()
            
            # Mix dictionary keys to support existing varied uses
            return [
                {
                    "id": r[0],
                    "ID": r[0],
                    "username": r[1],
                    "Username": r[1],
                    "role": r[2],
                    "Role": r[2],
                    "is_active": bool(r[3]),
                    "Last Login At": r[4] or "Never",
                    "last_login_at": r[4] or "Never"
                }
                for r in rows
            ]
    except sqlite3.Error as e:
        raise sqlite3.Error(f"Failed to retrieve users: {e}") from e


def delete_user(username: str) -> None:
    try:
        username = _validate_username(username)
        with _connect() as conn:
            conn.execute(
                "DELETE FROM users WHERE username = ?",
                (username,),
            )
            conn.commit()
    except sqlite3.Error as e:
        raise sqlite3.Error(f"Failed to delete user: {e}") from e


def update_password(username: str, new_password: str) -> None:
    try:
        username = _validate_username(username)
        new_password = _validate_password_complexity(new_password)

        with _connect() as conn:
            cursor = conn.execute(
                "SELECT COUNT(1) FROM users WHERE username = ?",
                (username,),
            )
            if cursor.fetchone()[0] == 0:
                raise ValueError("User not found.")

            hashed = _hash_password(new_password)
            conn.execute(
                "UPDATE users SET password = ? WHERE username = ?",
                (hashed, username),
            )
            conn.commit()

        log_security_event(
            event_type="password_change",
            username=username,
            details="Password updated successfully.",
        )
    except sqlite3.Error as e:
        raise sqlite3.Error(f"Failed to update password: {e}") from e


def get_tour_completed(username: str) -> bool:
    try:
        username = _validate_username(username)
        with _connect() as conn:
            row = conn.execute(
                "SELECT tour_completed FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            return bool(row[0]) if row else False
    except sqlite3.Error as e:
        raise sqlite3.Error(f"Failed to retrieve tour status: {e}") from e


def set_tour_completed(username: str, completed: bool = True) -> None:
    try:
        username = _validate_username(username)
        with _connect() as conn:
            conn.execute(
                "UPDATE users SET tour_completed = ? WHERE username = ?",
                (1 if completed else 0, username),
            )
            conn.commit()
    except sqlite3.Error as e:
        raise sqlite3.Error(f"Failed to update tour status: {e}") from e


def get_2fa_status(username: str) -> tuple[bool, str | None]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT two_factor_enabled, otp_secret FROM users WHERE username = ?",
            (username.lower(),),
        ).fetchone()
    if not row:
        return False, None
    return bool(row[0]), row[1]




def enable_2fa(username: str, secret: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET two_factor_enabled = 1, otp_secret = ? WHERE username = ?",
            (secret, username.lower()),
        )
        conn.commit()


def disable_2fa(username: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET two_factor_enabled = 0, otp_secret = NULL WHERE username = ?",
            (username.lower(),),
        )
        conn.commit()


def check_login_rate_limit(username: str) -> tuple[bool, str | None]:
    try:
        from src.utils.redis_cache import is_login_locked_out, get_login_attempts
        identifier = username.lower()
        if is_login_locked_out(identifier):
            attempts = get_login_attempts(identifier)
            return (
                False,
                f"Account locked due to too many failed attempts. Please try again in 15 minutes. ({attempts}/5 attempts)",
            )
        return True, None
    except ImportError:
        return True, None


def record_failed_login(username: str) -> None:
    try:
        from src.utils.redis_cache import increment_login_attempts
        identifier = username.lower()
        increment_login_attempts(identifier)
    except ImportError:
        pass


def clear_login_attempts(username: str) -> None:
    try:
        from src.utils.redis_cache import clear_login_attempts as redis_clear_login_attempts
        identifier = username.lower()
        redis_clear_login_attempts(identifier)
    except ImportError:
        pass


def get_user_preferences(username: str) -> dict:
    username = username.lower()
    with _connect() as conn:
        row = conn.execute(
            "SELECT preferences FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    if row and row[0]:
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return {}
    return {}


def update_user_preferences(username: str, preferences: dict) -> None:
    username = username.lower()
    prefs_str = json.dumps(preferences)
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET preferences = ? WHERE username = ?",
            (prefs_str, username),
        )
        conn.commit()


def get_user_theme(username: str) -> str:
    username = username.lower()
    with _connect() as conn:
        row = conn.execute(
            "SELECT theme FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        return row[0] if row else "light"


def set_user_theme(username: str, theme: str) -> None:
    username = username.lower()
    if theme not in ("light", "dark"):
        theme = "light"
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET theme = ? WHERE username = ?",
            (theme, username),
        )
        conn.commit()


def get_or_create_sso_user(email: str, default_role: str = "teacher") -> str:
    username = _validate_username(email)
    with _connect() as conn:
        row = conn.execute(
            "SELECT role FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if row:
            return row[0]

        hashed = _hash_password("!")
        role = _validate_role(default_role)

        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, hashed, role),
        )
        conn.commit()
        return role


def get_user_active_status(username: str) -> bool:
    try:
        username = _validate_username(username)
        with _connect() as conn:
            row = conn.execute(
                "SELECT is_active FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            return bool(row[0]) if row else False
    except sqlite3.Error as e:
        raise sqlite3.Error(f"Failed to retrieve user active status: {e}") from e


def set_user_active_status(username: str, is_active: bool) -> None:
    try:
        username = _validate_username(username)
        with _connect() as conn:
            if username == "admin" and not is_active:
                raise ValueError("The admin account cannot be suspended.")

            conn.execute(
                "UPDATE users SET is_active = ? WHERE username = ?",
                (1 if is_active else 0, username),
            )
            conn.commit()
    except sqlite3.Error as e:
        raise sqlite3.Error(f"Failed to update user active status: {e}") from e


def is_user_active(username: str) -> bool:
    try:
        username = _validate_username(username)
        with _connect() as conn:
            row = conn.execute(
                "SELECT is_active FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            return bool(row[0]) if row else True
    except sqlite3.Error:
        return True


def get_user_count() -> int:
    with _connect() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM users")
        row = cursor.fetchone()
        return row[0] if row else 0