

def get_recent_audit_events(
    limit: int = 20,
    offset: int = 0,
    event_type: str | None = None,
    username: str | None = None,
    db_path: str | None = None,
) -> list[dict]:
    """Fetch recent security audit events with pagination support.

    Retrieves audit log entries ordered by timestamp descending (most recent first).
    Supports filtering by event type and username, as well as pagination via
    limit and offset parameters for building paginated UIs (Issue #2732).

    Args:
        limit: Maximum number of events to return. Defaults to 20.
        offset: Number of events to skip (for pagination). Defaults to 0.
        event_type: Optional filter for specific event types (e.g., 'login_failed').
        username: Optional filter for specific usernames.
        db_path: Optional path to the SQLite database.

    Returns:
        List of dictionaries representing audit events, ordered by timestamp DESC.
    """
    if limit < 1:
        limit = 20
    if offset < 0:
        offset = 0

    if db_path is None:
        from src.db.auth import get_auth_db_path

        db_path = str(get_auth_db_path())

    query = """
        SELECT id, timestamp, event_type, username, details 
        FROM security_audit_log 
        WHERE 1=1
    """
    params: list = []

    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)

    if username:
        query += " AND username = ?"
        params.append(username.strip().lower())

    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    except sqlite3.Error as e:
        logger.error("Failed to fetch audit events: %s", e)
        return []


def get_audit_events_count(
    event_type: str | None = None,
    username: str | None = None,
    db_path: str | None = None,
) -> int:
    """Get the total count of audit events matching the filters.

    Used in conjunction with get_recent_audit_events to calculate total
    pages for paginated UIs.
    """
    if db_path is None:
        from src.db.auth import get_auth_db_path

        db_path = str(get_auth_db_path())

    query = "SELECT COUNT(*) FROM security_audit_log WHERE 1=1"
    params: list = []

    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)

    if username:
        query += " AND username = ?"
        params.append(username.strip().lower())

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(query, params)
            result = cursor.fetchone()
            return result[0] if result else 0

    except sqlite3.Error as e:
        logger.error("Failed to count audit events: %s", e)
        return 0

