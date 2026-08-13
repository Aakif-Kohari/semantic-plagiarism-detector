"""src/db/connection.py - Centralized SQLite database connection configuration."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

logger = logging.getLogger(__name__)

DEFAULT_SQLITE_TIMEOUT: float = 15.0

# Lower bound for the busy timeout actually handed to SQLite. A caller may ask
# for a very small timeout, but anything under ~100 ms means a lock contended by
# a concurrent WAL writer is effectively never waited on, which shows up as
# spurious "database is locked" errors rather than as a slow query.
MIN_BUSY_TIMEOUT_MS: int = 100


def resolve_busy_timeout_ms(timeout: float) -> int:
    """Convert a timeout expressed in seconds into a SQLite busy timeout in ms.

    ``sqlite3.connect(timeout=...)`` already configures ``PRAGMA busy_timeout``
    for us, but several call sites open connections directly and need the same
    conversion. Keeping the arithmetic (and the floor) in one place means the
    two paths cannot drift apart.

    Parameters
    ----------
    timeout : float
        Busy timeout in seconds. Must be a positive, finite number.

    Returns
    -------
    int
        Busy timeout in milliseconds, never below :data:`MIN_BUSY_TIMEOUT_MS`.

    Raises
    ------
    ValueError
        If *timeout* is not a positive number.
    TypeError
        If *timeout* is not numeric.
    """
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise TypeError(f"timeout must be a number, got {type(timeout).__name__}")

    if timeout != timeout or timeout in (float("inf"), float("-inf")):
        raise ValueError(f"timeout must be a finite number, got {timeout!r}")

    if timeout <= 0:
        raise ValueError(f"timeout must be > 0 seconds, got {timeout!r}")

    return max(MIN_BUSY_TIMEOUT_MS, int(timeout * 1000))


def apply_busy_timeout(conn: sqlite3.Connection, timeout: float) -> int:
    """Apply ``PRAGMA busy_timeout`` to *conn* based on a timeout in seconds.

    Parameters
    ----------
    conn : sqlite3.Connection
        An open SQLite connection.
    timeout : float
        Busy timeout in seconds.

    Returns
    -------
    int
        The busy timeout in milliseconds that was applied.
    """
    timeout_ms = resolve_busy_timeout_ms(timeout)
    conn.execute(f"PRAGMA busy_timeout = {timeout_ms}")
    return timeout_ms


def create_connection(
    db_path: str | Path,
    timeout: float = DEFAULT_SQLITE_TIMEOUT,
    read_only: bool = False,
) -> sqlite3.Connection:
    """Create and configure a SQLite connection with WAL mode and PRAGMA settings.

    Parameters
    ----------
    db_path : str | Path
        Path to the SQLite database file.
    timeout : float
        Busy timeout in seconds (default: 15.0). This value is honoured by the
        connection's ``busy_timeout`` pragma, so a caller asking for 30 seconds
        really does wait up to 30 seconds for a contended lock.
    read_only : bool
        If True, opens the connection in read-only mode using a URI string.

    Returns
    -------
    sqlite3.Connection
        Configured SQLite connection instance with sqlite3.Row factory.

    Raises
    ------
    ValueError
        If *timeout* is not a positive, finite number.
    """
    # Validate before touching the file system so a bad argument fails fast
    # instead of leaving a half-configured connection behind.
    timeout_ms = resolve_busy_timeout_ms(timeout)

    path_obj = Path(db_path).expanduser().resolve(strict=False)

    if read_only:
        if not path_obj.exists():
            raise FileNotFoundError(f"SQLite database does not exist: {path_obj}")
        if not path_obj.is_file():
            raise IsADirectoryError(f"SQLite database path is not a file: {path_obj}")
        uri = f"{path_obj.as_uri()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=timeout, check_same_thread=False)
    else:
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path_obj), timeout=timeout, check_same_thread=False)

    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    # sqlite3.connect() already derives busy_timeout from `timeout`, but we set
    # it explicitly so the value is guaranteed regardless of how the connection
    # was opened (URI mode, future driver changes) and so the floor in
    # resolve_busy_timeout_ms() is applied consistently.
    conn.execute(f"PRAGMA busy_timeout = {timeout_ms}")

    if not read_only:
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
        except sqlite3.OperationalError as exc:
            logger.debug(
                f"[db.connection] Could not set WAL mode for '{db_path}': {exc}"
            )

    return conn


@contextmanager
def get_connection(
    db_path: str | Path,
    timeout: float = DEFAULT_SQLITE_TIMEOUT,
    read_only: bool = False,
) -> Generator[sqlite3.Connection, None, None]:
    """Context manager yielding a managed SQLite connection that closes on exit."""
    conn = create_connection(db_path, timeout=timeout, read_only=read_only)
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass
