"""
tests/core/test_parse_durations.py
----------------------------------
Unit tests for the parse duration registry (Issue #1728).
"""

from src.core.parse_durations import (
    record_parse_duration,
    get_parse_duration,
    get_all_parse_durations,
    clear_parse_durations,
    format_duration,
)


def test_record_and_get():
    clear_parse_durations()
    record_parse_duration("test.pdf", 0.42)
    assert get_parse_duration("test.pdf") == 0.42


def test_get_missing_returns_none():
    clear_parse_durations()
    assert get_parse_duration("nonexistent.pdf") is None


def test_get_all():
    clear_parse_durations()
    record_parse_duration("a.pdf", 0.1)
    record_parse_duration("b.pdf", 0.2)
    all_durations = get_all_parse_durations()
    assert all_durations == {"a.pdf": 0.1, "b.pdf": 0.2}


def test_clear():
    clear_parse_durations()
    record_parse_duration("test.pdf", 0.42)
    clear_parse_durations()
    assert get_all_parse_durations() == {}


def test_format_duration():
    assert format_duration(0.423456) == "0.42s"
    assert format_duration(1.0) == "1.00s"
    assert format_duration(0.0) == "0.00s"


def test_format_duration_none():
    assert format_duration(None) == ""
