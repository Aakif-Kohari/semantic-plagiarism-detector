"""
auth.py
-------
SQLite-backed authentication with bcrypt password hashing.

Public API
----------
init_db()                          → create tables + seed default admin
verify_user(username, password)    → bool
get_user_role(username)            → str | None
add_user(username, password, role) → None
get_all_users()                    → list[dict]
delete_user(username)              → None
update_password(username, password)→ None
get_tour_completed(username)       → bool
set_tour_completed(username, completed) → None
"""

import sqlite3
import bcrypt
import os

_DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "users.db")
)


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(_DB_PATH, check_same_thread=False)
def _hash_password(password: str) -> str:
    """Return a bcrypt hash for the given password."""
    return bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt(10),
    ).decode()


def init_db() -> None:
    """Create users table and seed default admin if not exists."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT    UNIQUE NOT NULL,
                password TEXT    NOT NULL,
                role     TEXT    NOT NULL DEFAULT 'teacher',
                tour_completed INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        
        # Schema migration: add tour_completed column if it doesn't exist
        cursor = conn.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        if "tour_completed" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN tour_completed INTEGER DEFAULT 0")
            conn.commit()
        
        exists = conn.execute(
            "SELECT 1 FROM users WHERE username = ?", ("admin",)
        ).fetchone()
        if not exists:
            hashed = _hash_password("admin123")
            conn.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                ("admin", hashed, "admin"),
            )
        conn.commit()


def verify_user(username: str, password: str) -> bool:
    """Return True if username exists and password matches the stored hash."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT password FROM users WHERE username = ?", (username.lower(),)
        ).fetchone()
    if not row:
        return False
    return bcrypt.checkpw(password.encode(), row[0].encode())


def get_user_role(username: str) -> str | None:
    """Return the role of a user, or None if not found."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT role FROM users WHERE username = ?", (username.lower(),)
        ).fetchone()
    return row[0] if row else None


def add_user(username: str, password: str, role: str = "teacher") -> None:
    """Insert a new user with a bcrypt-hashed password."""
    hashed = _hash_password(password)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username.lower(), hashed, role),
        )
        conn.commit()


def get_all_users() -> list:
    """Return all users as a list of dicts (excludes password hashes)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, username, role FROM users ORDER BY id"
        ).fetchall()
    return [{"id": r[0], "username": r[1], "role": r[2]} for r in rows]


def delete_user(username: str) -> None:
    """Delete a user by username."""
    with _connect() as conn:
        conn.execute("DELETE FROM users WHERE username = ?", (username.lower(),))
        conn.commit()


def update_password(username: str, new_password: str) -> None:
    """Update a user's password with a new bcrypt hash."""
    hashed = _hash_password(new_password)
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET password = ? WHERE username = ?",
            (hashed, username.lower()),
        )
        conn.commit()


def get_tour_completed(username: str) -> bool:
    """Return whether a user has completed the onboarding tour."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT tour_completed FROM users WHERE username = ?", (username.lower(),)
        ).fetchone()
    return bool(row[0]) if row else False


def set_tour_completed(username: str, completed: bool = True) -> None:
    """Mark a user as having completed the onboarding tour."""
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET tour_completed = ? WHERE username = ?",
            (1 if completed else 0, username.lower()),
        )
        conn.commit()


def get_security_audit_logs(limit: int = 50, offset: int = 0, username: str | None = None) -> list[dict]:
    """Return a paginated list of security audit logs, ordered by timestamp DESC."""
    if limit < 0 or offset < 0:
        raise ValueError("Limit and offset must be non-negative.")
        
    query = "SELECT * FROM security_audit_log"
    params = []
    
    if username is not None:
        query += " WHERE username = ?"
        params.append(username)
        
    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    with _connect() as conn:
        # Use Row factory to easily convert rows to dicts
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, tuple(params)).fetchall()
        
    return [dict(row) for row in rows]
def test_get_all_users():
    username = uuid.uuid4().hex

    add_user(username, "password123")

    users = get_all_users()

    usernames = [user["username"] for user in users]

    assert username in usernames
def test_verify_nonexistent_user():
    assert verify_user("unknown_user", "password") is False
def test_update_password_changes_password():
    username = uuid.uuid4().hex

    add_user(username, "oldpassword")

    update_password(username, "newpassword")

    assert verify_user(username, "oldpassword") is False
    assert verify_user(username, "newpassword") is True
def test_delete_nonexistent_user():
    delete_user("does_not_exist")

    assert get_user_role("does_not_exist") is None
def test_default_admin_exists():
    init_db()

    assert verify_user("admin", "admin123") is True
    assert get_user_role("admin") == "admin"
def test_add_user_default_role():
    username = uuid.uuid4().hex

    add_user(username, "password123")

    assert get_user_role(username) == "teacher"
def test_add_user_custom_role():
    username = uuid.uuid4().hex

    add_user(username, "password123", "admin")

    assert get_user_role(username) == "admin"
def test_tour_completed():
    username = uuid.uuid4().hex

    add_user(username, "password123")

    assert get_tour_completed(username) is False

    set_tour_completed(username, True)

    assert get_tour_completed(username) is True
def test_reset_tour_completed():
    username = uuid.uuid4().hex

    add_user(username, "password123")

    set_tour_completed(username, True)
    set_tour_completed(username, False)

    assert get_tour_completed(username) is False