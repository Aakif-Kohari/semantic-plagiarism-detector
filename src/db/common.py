"""src/db/common.py
------------------
Common database utilities and concurrency handling for SQLite operations.
"""

from __future__ import annotations

import functools
import logging
import os
import sqlite3
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


def with_sqlite_retry(
    fn: Callable | None = None,
    *,
    max_retries: int = 3,
    delay: float = 0.1,
    backoff: float = 2.0,
) -> Callable:
    """
    Decorator that retries SQLite operations when a sqlite3.OperationalError occurs
    due to a locked or busy database ("database is locked" / "database is busy").

    Applies exponential backoff on subsequent retry attempts.

    Args:
        fn (Callable, optional): Function being decorated when used as @with_sqlite_retry.
        max_retries (int): Maximum number of retry attempts (default: 3).
        delay (float): Initial delay in seconds before the first retry (default: 0.1).
        backoff (float): Multiplier for exponential backoff (default: 2.0).

    Returns:
        Callable: Wrapped function with SQLite lock retry logic.
    """
    if fn is not None and callable(fn):
        return _make_wrapper(fn, max_retries=3, delay=0.1, backoff=2.0)

    def decorator(func: Callable) -> Callable:
        return _make_wrapper(func, max_retries=max_retries, delay=delay, backoff=backoff)

    return decorator


def _make_wrapper(func: Callable, max_retries: int, delay: float, backoff: float) -> Callable:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        current_delay = delay
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except sqlite3.OperationalError as exc:
                err_msg = str(exc).lower()
                is_locked_err = "locked" in err_msg or "busy" in err_msg
                if is_locked_err and attempt < max_retries:
                    func_name = getattr(func, "__name__", str(func))
                    logger.warning(
                        f"SQLite database locked/busy in '{func_name}' "
                        f"(attempt {attempt + 1}/{max_retries}). Retrying in {current_delay:.2f}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
                else:
                    raise
    return wrapper


from contextlib import contextmanager
from typing import Generator

@contextmanager
def managed_connection(db_path: str | os.PathLike) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for SQLite connections that guarantees conn.close() on exit,
    preventing unclosed connection handle leaks (Issue #1707).
    """
    conn = sqlite3.connect(db_path, timeout=15.0, check_same_thread=False)
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass
