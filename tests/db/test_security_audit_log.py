"""Tests for security audit log — password change event recording (Issue #620)."""

from __future__ import annotations

import sqlite3
import uuid

import pytest

import src.db.auth
from src.db.auth import (
    _connect,
    add_user,
    init_db,
    log_security_event,
    update_password,
)


@pytest.fixture(autouse=True)
def setup_test_db(mock_db):
    """Use the shared mock_db fixture to isolate DB operations."""
    init_db()
    yield


def test_log_security_event_inserts_row():
    """log_security_event should write a row into security_audit_log."""
    username = f"user_{uuid.uuid4().hex[:8]}"
    add_user(username, "Password1!")
    log_security_event(event_type="password_change", username=username)
    with _connect() as conn:
        row = conn.execute(
            "SELECT event_type, username FROM security_audit_log WHERE username = ?",
            (username,),
        ).fetchone()
    assert row is not None
    assert row[0] == "password_change"
    assert row[1] == username


def test_log_security_event_stores_timestamp():
    """log_security_event should store a non-empty ISO 8601 UTC timestamp."""
    username = f"user_{uuid.uuid4().hex[:8]}"
    add_user(username, "Password1!")
    log_security_event(event_type="password_change", username=username)
    with _connect() as conn:
        row = conn.execute(
            "SELECT timestamp FROM security_audit_log WHERE username = ?",
            (username,),
        ).fetchone()
    assert row is not None
    timestamp = row[0]
    assert len(timestamp) == 20
    assert timestamp.endswith("Z")
    assert "T" in timestamp


def test_log_security_event_stores_optional_details():
    """log_security_event should persist the details field when provided."""
    username = f"user_{uuid.uuid4().hex[:8]}"
    add_user(username, "Password1!")
    log_security_event(
        event_type="password_change",
        username=username,
        details="Password updated successfully.",
    )
    with _connect() as conn:
        row = conn.execute(
            "SELECT details FROM security_audit_log WHERE username = ?",
            (username,),
        ).fetchone()
    assert row is not None
    assert row[0] == "Password updated successfully."


def test_log_security_event_insertion():
    """log_security_event() must commit a real row against the actual
    migrated SQLite schema, verifiable from an independent connection.

    Unlike the tests above (which reuse the module's own ``_connect()``
    helper), this test opens a brand new ``sqlite3.connect()`` against the
    on-disk database file directly. Since SQLite connections only see rows
    committed by other connections, a successful SELECT here proves
    ``log_security_event`` actually called ``conn.commit()`` rather than
    merely writing to an uncommitted transaction that a same-connection
    read could still observe.
    """
    username = f"user_{uuid.uuid4().hex[:8]}"
    add_user(username, "Password1!")

    log_security_event(
        event_type="login_success",
        username=username,
        details="Insertion test event",
    )

    # Independent connection, opened fresh against the real DB file/schema
    # created by init_db() (via the migration pipeline), not the
    # connection log_security_event() itself used.
    conn = sqlite3.connect(src.db.auth._DB_PATH)
    try:
        row = conn.execute(
            "SELECT event_type, username, timestamp, details "
            "FROM security_audit_log WHERE username = ? AND event_type = ?",
            (username, "login_success"),
        ).fetchone()
    finally:
        conn.close()

    assert row is not None, "log_security_event() did not commit a row"
    event_type, stored_username, timestamp, details = row
    assert event_type == "login_success"
    assert stored_username == username
    assert timestamp  # non-empty ISO-8601 timestamp
    assert details == "Insertion test event"


def test_update_password_creates_audit_log_entry():
    """Calling update_password should create at least one audit log entry."""
    username = f"user_{uuid.uuid4().hex[:8]}"
    add_user(username, "OldPassword1!")
    update_password(username, "NewPassword2@")
    with _connect() as conn:
        rows = conn.execute(
            "SELECT event_type, username FROM security_audit_log WHERE username = ?",
            (username,),
        ).fetchall()
    assert len(rows) >= 1
    assert any(r[0] == "password_change" and r[1] == username for r in rows)


def test_update_password_audit_log_entry_has_timestamp():
    """Audit log entry created by update_password must have a valid timestamp."""
    username = f"user_{uuid.uuid4().hex[:8]}"
    add_user(username, "OldPassword1!")
    update_password(username, "NewPassword2@")
    with _connect() as conn:
        row = conn.execute(
            "SELECT timestamp FROM security_audit_log "
            "WHERE username = ? AND event_type = 'password_change'",
            (username,),
        ).fetchone()
    assert row is not None
    assert row[0].endswith("Z")


def test_update_password_logs_multiple_changes():
    """Each call to update_password should produce a separate audit log entry."""
    username = f"user_{uuid.uuid4().hex[:8]}"
    add_user(username, "FirstPass1!")
    update_password(username, "SecondPass2@")
    update_password(username, "ThirdPass3#")
    with _connect() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM security_audit_log "
            "WHERE username = ? AND event_type = 'password_change'",
            (username,),
        ).fetchone()[0]
    assert count >= 2
