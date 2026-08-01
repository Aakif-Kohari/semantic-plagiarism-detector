import sqlite3
import uuid

import pytest

from src.db.auth import (
    add_user,
    delete_user,
    disable_2fa,
    enable_2fa,
    format_user_created_date,
    get_2fa_status,
    get_user_active_status,
    get_user_role,
    get_user_theme,
    init_db,
    is_user_active,
    log_security_event,
    set_user_active_status,
    set_user_theme,
    update_password,
    get_security_audit_logs,
    verify_user,
)


@pytest.fixture(autouse=True)
def setup_test_db(mock_db):
    """Uses the mock_db fixture from conftest.py to isolate DB operations."""
    init_db()
    yield


def test_init_db():
    init_db()
    assert verify_user("admin", "Admin123!") is True
    assert verify_user("admin", "wrongpassword") is False


def test_add_user():
    user = f"user_{uuid.uuid4().hex[:8]}"
    add_user(user, "SecurePass123!")
    check = get_user_role(user)
    assert check is not None


def test_duplicate_user():
    user = f"user_{uuid.uuid4().hex[:8]}"
    add_user(user, "SecurePass123!")
    with pytest.raises((ValueError, sqlite3.IntegrityError)):
        add_user(user, "SecurePass123!")


def test_verify_user():
    user = f"user_{uuid.uuid4().hex[:8]}"
    add_user(user, "SecurePass123!")
    assert verify_user(user, "SecurePass123!") is True
    assert verify_user(user, "WrongPass123!") is False


def test_get_user_role():
    user = f"user_{uuid.uuid4().hex[:8]}"
    add_user(user, "password123")
    assert get_user_role(user) is not None
    assert get_user_role("non_existent_user_999") is None


def test_update_password():
    user = f"user_{uuid.uuid4().hex[:8]}"
    add_user(user, "password123")
    update_password(user, "new_secret_123!")
    assert verify_user(user, "new_secret_123!") is True


def test_delete_user():
    delete_user("hnsdf9")
    assert get_user_role("hnsdf9") is None


import unittest.mock as mock

@pytest.fixture
def mock_audit_db():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE security_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            action TEXT,
            timestamp DATETIME
        )
    """)
    conn.execute("INSERT INTO security_audit_log (username, action, timestamp) VALUES ('alice', 'login', '2023-01-01 10:00:00')")
    conn.execute("INSERT INTO security_audit_log (username, action, timestamp) VALUES ('bob', 'login', '2023-01-02 10:00:00')")
    conn.execute("INSERT INTO security_audit_log (username, action, timestamp) VALUES ('alice', 'logout', '2023-01-03 10:00:00')")
    conn.commit()
    
    with mock.patch("src.db.auth._connect", return_value=conn):
        yield conn
    conn.close()

def test_get_security_audit_logs_default(mock_audit_db):
    logs = get_security_audit_logs()
    assert len(logs) == 3
    # Order by timestamp DESC
    assert logs[0]["username"] == "alice"
    assert logs[0]["action"] == "logout"
    assert logs[2]["username"] == "alice"
    assert logs[2]["action"] == "login"

def test_get_security_audit_logs_pagination(mock_audit_db):
    logs = get_security_audit_logs(limit=1, offset=1)
    assert len(logs) == 1
    # 2nd in desc order is bob
    assert logs[0]["username"] == "bob"

def test_get_security_audit_logs_username_filter(mock_audit_db):
    logs = get_security_audit_logs(username="alice")
    assert len(logs) == 2
    assert logs[0]["action"] == "logout"
    assert logs[1]["action"] == "login"
    
def test_get_security_audit_logs_empty(mock_audit_db):
    logs = get_security_audit_logs(username="charlie")
    assert len(logs) == 0

def test_get_security_audit_logs_invalid_limit_offset(mock_audit_db):
    with pytest.raises(ValueError):
        get_security_audit_logs(limit=-1)
    with pytest.raises(ValueError):
        get_security_audit_logs(offset=-1)
    user = f"user_{uuid.uuid4().hex[:8]}"
    add_user(user, "password123")
    delete_user(user)
    assert get_user_role(user) is None


def test_2fa_flow():
    username = f"user2fa_{uuid.uuid4().hex[:8]}"
    add_user(username, "pass1234567!")

    enabled, secret = get_2fa_status(username)
    assert enabled is False
    assert secret is None

    test_secret = "JBSWY3DPEHPK3PXP"
    enable_2fa(username, test_secret)

    enabled, secret = get_2fa_status(username)
    assert enabled is True
    assert secret == test_secret

    disable_2fa(username)

    enabled, secret = get_2fa_status(username)
    assert enabled is False
    assert secret is None

    delete_user(username)


def test_suspend_account():
    username = f"user_{uuid.uuid4().hex[:8]}"
    add_user(username, "password123!")

    # Verify default is active
    assert get_user_active_status(username) is True
    assert is_user_active(username) is True

    # Suspend user
    set_user_active_status(username, False)
    assert get_user_active_status(username) is False
    assert is_user_active(username) is False

    # Try suspending default 'admin' user (must raise ValueError)
    with pytest.raises(ValueError, match="The admin account cannot be suspended."):
        set_user_active_status("admin", False)

    # Reactivate user
    set_user_active_status(username, True)
    assert get_user_active_status(username) is True
    assert is_user_active(username) is True

    delete_user(username)


def test_sqlite_file_lock_exception(mock_db):
    """Test that acquiring an exclusive lock on SQLite database triggers a clean sqlite3.Error when attempting add_user."""
    conn = sqlite3.connect(mock_db)
    conn.execute("BEGIN EXCLUSIVE TRANSACTION")
    try:
        with pytest.raises(sqlite3.Error) as exc_info:
            add_user("locked_user", "password123!")
        assert "Failed to add user" in str(exc_info.value) or "locked" in str(exc_info.value)
    finally:
        conn.rollback()
        conn.close()


def test_user_theme(mock_db):
    """Test get and set theme for a user."""
    user = f"theme_user_{uuid.uuid4().hex[:8]}"
    add_user(user, "password123!")

    # Default should be light
    assert get_user_theme(user) == "light"

    # Set to dark
    set_user_theme(user, "dark")
    assert get_user_theme(user) == "dark"


def test_delete_user_removes_user_row_and_audit_log(mock_db):
    """delete_user() must remove the user row and associated security_audit_log entries."""
    user = f"user_{uuid.uuid4().hex[:8]}"
    add_user(user, "password123")

    # Seed an audit log entry for this user
    log_security_event("password_change", user, "test entry")

    # Confirm the audit entry exists before deletion
    with sqlite3.connect(mock_db) as conn:
        audit_before = conn.execute(
            "SELECT COUNT(*) FROM security_audit_log WHERE username = ?", (user,)
        ).fetchone()[0]
    assert audit_before >= 1

    delete_user(user)

    # User row must be gone
    assert get_user_role(user) is None

    # Audit log entries for the deleted user must also be removed
    with sqlite3.connect(mock_db) as conn:
        audit_after = conn.execute(
            "SELECT COUNT(*) FROM security_audit_log WHERE username = ?", (user,)
        ).fetchone()[0]
    assert audit_after == 0


def test_delete_user_removes_matching_session_and_authorization_rows(mock_db):
    """delete_user() should remove matching session and authorization rows for the deleted user."""
    user = f"user_{uuid.uuid4().hex[:8]}"
    add_user(user, "password123")

    with sqlite3.connect(mock_db) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                session_state TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS authorization_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                token TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO user_sessions (username, session_state) VALUES (?, ?)",
            (user, '{"page": "dashboard"}'),
        )
        conn.execute(
            "INSERT INTO authorization_tokens (username, token) VALUES (?, ?)",
            (user, "token-for-user"),
        )
        conn.execute(
            "INSERT INTO user_sessions (username, session_state) VALUES (?, ?)",
            ("other_user", '{"page": "dashboard"}'),
        )
        conn.execute(
            "INSERT INTO authorization_tokens (username, token) VALUES (?, ?)",
            ("other_user", "token-for-other"),
        )
        conn.commit()

    delete_user(user)

    with sqlite3.connect(mock_db) as conn:
        user_session_count = conn.execute(
            "SELECT COUNT(*) FROM user_sessions WHERE username = ?", (user,)
        ).fetchone()[0]
        user_token_count = conn.execute(
            "SELECT COUNT(*) FROM authorization_tokens WHERE username = ?", (user,)
        ).fetchone()[0]
        other_session_count = conn.execute(
            "SELECT COUNT(*) FROM user_sessions WHERE username = ?", ("other_user",)
        ).fetchone()[0]
        other_token_count = conn.execute(
            "SELECT COUNT(*) FROM authorization_tokens WHERE username = ?", ("other_user",)
        ).fetchone()[0]

    assert get_user_role(user) is None
    assert user_session_count == 0
    assert user_token_count == 0
    assert other_session_count == 1
    assert other_token_count == 1

# ──────────────────────────────────────────────────────────────────────────────
# format_user_created_date — issue #1049
# ──────────────────────────────────────────────────────────────────────────────

def test_connect_uses_fifteen_second_timeout():
    """Verify that _connect helper sets sqlite3 timeout to 15.0 seconds."""
    from unittest.mock import patch
    from src.db.auth import _connect

    with patch("sqlite3.connect") as mock_connect:
        _connect()
        mock_connect.assert_called_once()
        kwargs = mock_connect.call_args[1]
        assert kwargs.get("timeout") == 15.0



