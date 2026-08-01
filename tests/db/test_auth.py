from src.db.auth import (
    init_db,
    add_user,
    verify_user,
    get_user_role,
    delete_user,
    update_password,
    get_security_audit_logs,
)
import pytest
import sqlite3
import uuid


@pytest.fixture(autouse=True)
def db_connection():
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT    UNIQUE NOT NULL,
                    password TEXT    NOT NULL,
                    role     TEXT    NOT NULL DEFAULT 'teacher'
                )
            """)
    conn.commit()
    yield conn
    print("In-memory database ready for testing")
    conn.close()


# Calls the init_db function and then uses verify_user to check if default admin user created
def test_init_db():
    init_db()
    assert verify_user("admin", "admin123") is not False


# Adds new user via uuid and uses get_user_role to check if user added
def test_add_user():
    user = uuid.uuid4().hex
    add_user(user, "ac_123")
    check = get_user_role(user)
    assert check is not None


# Adds a user and then checks whether adding same user again raises exception
def test_duplicate_user():
    add_user("hnsdf9", "ehns-1")
    with pytest.raises(sqlite3.IntegrityError):
        add_user("hnsdf9", "ehns-1")


# Checks whether adding incorrect password returns False
def test_verify_user():
    assert verify_user("hnsdf9", "ehns-1") is True
    assert verify_user("hnsdf9", "ehns_1") is False


def test_get_user_role():
    assert get_user_role("hnsdf9") is not None
    assert get_user_role("sdgk") is None


def test_update_password():
    update_password("hnsdf9", "sfgxv")
    assert verify_user("hnsdf9", "sfgxv") is not False


# Deletes a user and then verifies if it still exists
# No need to change the username as for each run since del is last operation and
# duplicate_user first it gets created and deleted for each run
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
