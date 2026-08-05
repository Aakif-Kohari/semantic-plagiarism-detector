"""
tests/db/test_common.py
------------------------
Unit tests for SQLite concurrency retry decorator (with_sqlite_retry).
"""

import sqlite3
from unittest.mock import MagicMock

import pytest

from src.db.common import with_sqlite_retry


def test_with_sqlite_retry_succeeds_without_error():
    @with_sqlite_retry
    def simple_func(x, y):
        return x + y

    assert simple_func(2, 3) == 5


def test_with_sqlite_retry_retries_on_locked_operational_error():
    mock_func = MagicMock()
    mock_func.side_effect = [
        sqlite3.OperationalError("database is locked"),
        sqlite3.OperationalError("database is busy"),
        "success",
    ]

    decorated = with_sqlite_retry(max_retries=3, delay=0.01, backoff=1.0)(mock_func)

    result = decorated()

    assert result == "success"
    assert mock_func.call_count == 3


def test_with_sqlite_retry_raises_after_max_retries():
    mock_func = MagicMock()
    mock_func.side_effect = sqlite3.OperationalError("database is locked")

    decorated = with_sqlite_retry(max_retries=2, delay=0.01, backoff=1.0)(mock_func)

    with pytest.raises(sqlite3.OperationalError, match="database is locked"):
        decorated()

    # Initial attempt + 2 retries = 3 total calls
    assert mock_func.call_count == 3


def test_with_sqlite_retry_raises_non_locking_error_immediately():
    mock_func = MagicMock()
    mock_func.side_effect = sqlite3.OperationalError("no such table: non_existent")

    decorated = with_sqlite_retry(max_retries=3, delay=0.01)(mock_func)

    with pytest.raises(sqlite3.OperationalError, match="no such table"):
        decorated()

    assert mock_func.call_count == 1


def test_with_sqlite_retry_decorator_without_arguments():
    attempts = 0

    @with_sqlite_retry
    def flaky_func():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise sqlite3.OperationalError("database is locked")
        return "ok"

    assert flaky_func() == "ok"
    assert attempts == 2


def test_with_sqlite_retry_decorator_with_arguments():
    attempts = 0

    @with_sqlite_retry(max_retries=4, delay=0.001, backoff=1.5)
    def flaky_func():
        nonlocal attempts
        attempts += 1
        if attempts < 4:
            raise sqlite3.OperationalError("database is busy")
        return "completed"

    assert flaky_func() == "completed"
    assert attempts == 4
