"""src/db/connection.py - Centralized SQLite database connection configuration."""

from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

logger = logging.getLogger(__name__)

DEFAULT_SQLITE_TIMEOUT: float = 15.0


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
        Busy timeout in seconds (default: 15.0).
    read_only : bool
        If True, opens the connection in read-only mode using a URI string.

    Returns
    -------
    sqlite3.Connection
        Configured SQLite connection instance with sqlite3.Row factory.
    """
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
    conn.execute("PRAGMA busy_timeout = 5000")

    if not read_only:
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
        except sqlite3.OperationalError as exc:
            logger.debug(f"[db.connection] Could not set WAL mode for '{db_path}': {exc}")

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
