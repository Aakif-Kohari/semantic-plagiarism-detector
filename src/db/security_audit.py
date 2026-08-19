"""
src/db/security_audit.py
------------------------
Security audit logging and account lockout mechanism.

Tracks failed login attempts and provides utilities to enforce
account lockout policies to prevent brute-force attacks (Issue #2704).
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


def log_security_event(
    event_type: str,
    username: Optional[str] = None,
    details: Optional[str] = None,
    db_path: Optional[str] = None,
) -> None:
    """Log a security-related event to the audit log.

    Args:
        event_type: Type of event (e.g., 'login_failed', 'login_success').
        username: The username associated with the event.
        details: Additional context about the event.
        db_path: Optional path to the SQLite database. If None, uses default auth DB.
    """
    if db_path is None:
        from src.db.auth import get_auth_db_path

        db_path = str(get_auth_db_path())

    timestamp = datetime.utcnow().isoformat()

    try:
        with sqlite3.connect(db_path) as conn:
            # Ensure table exists
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS security_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    username TEXT,
                    details TEXT
                )
            """
            )

            conn.execute(
                """
                INSERT INTO security_audit_log (timestamp, event_type, username, details)
                VALUES (?, ?, ?, ?)
                """,
                (timestamp, event_type, username, details),
            )
            conn.commit()

    except sqlite3.Error as e:
        logger.error("Failed to log security event %s: %s", event_type, e)


def count_recent_failed_logins(
    username: str, window_minutes: int = 15, db_path: Optional[str] = None
) -> int:
    """Count the number of failed login attempts for a user within a time window.

    Queries the security_audit_log table for events of type 'login_failed'
    associated with the given username that occurred within the last
    `window_minutes`. This is used to enforce account lockout policies
    and prevent brute-force attacks.

    Args:
        username: The username to check for failed attempts.
        window_minutes: The time window in minutes to look back. Defaults to 15.
        db_path: Optional path to the SQLite database. If None, uses the default auth DB.

    Returns:
        The number of failed login attempts within the specified window.
        Returns 0 if the username is empty or an error occurs.
    """
    if not username or not isinstance(username, str):
        return 0

    if db_path is None:
        from src.db.auth import get_auth_db_path

        db_path = str(get_auth_db_path())

    cutoff_time = (datetime.utcnow() - timedelta(minutes=window_minutes)).isoformat()

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                """
                SELECT COUNT(*) 
                FROM security_audit_log 
                WHERE event_type = 'login_failed' 
                  AND username = ? 
                  AND timestamp >= ?
                """,
                (username.strip().lower(), cutoff_time),
            )
            result = cursor.fetchone()
            return result[0] if result else 0

    except sqlite3.Error as e:
        logger.error("Failed to count recent failed logins for %s: %s", username, e)
        # Fail open: if we can't read the audit log, don't lock the user out
        # but log the error for investigation. In high-security environments,
        # this might be changed to fail closed (return infinity).
        return 0
