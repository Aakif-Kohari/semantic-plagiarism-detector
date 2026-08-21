"""Tests for document parser MAX_BATCH_SIZE configurable via PARSER_MAX_BATCH_SIZE (Issue #2708)."""

import importlib

import pytest


def test_max_batch_size_default(monkeypatch):
    """Test MAX_BATCH_SIZE defaults to 50 when PARSER_MAX_BATCH_SIZE is not set."""
    monkeypatch.delenv("PARSER_MAX_BATCH_SIZE", raising=False)
    import src.core.document_parser as dp

    importlib.reload(dp)
    assert dp.MAX_BATCH_SIZE == 50

    # 50 files should not raise
    dp.check_batch_rate_limit(50)

    # 51 files should raise ValueError
    with pytest.raises(ValueError, match="50"):
        dp.check_batch_rate_limit(51)


def test_max_batch_size_env_override(monkeypatch):
    """Test MAX_BATCH_SIZE is configurable via PARSER_MAX_BATCH_SIZE env var."""
    monkeypatch.setenv("PARSER_MAX_BATCH_SIZE", "150")
    import src.core.document_parser as dp

    importlib.reload(dp)
    assert dp.MAX_BATCH_SIZE == 150

    # 150 files should pass
    dp.check_batch_rate_limit(150)

    # 151 files should raise ValueError
    with pytest.raises(ValueError, match="150"):
        dp.check_batch_rate_limit(151)


def test_max_batch_size_invalid_env_fallback(monkeypatch):
    """Test MAX_BATCH_SIZE gracefully falls back to 50 on invalid or non-positive env values."""
    for invalid_val in ["invalid_str", "-10", "0", "   "]:
        monkeypatch.setenv("PARSER_MAX_BATCH_SIZE", invalid_val)
        import src.core.document_parser as dp

        importlib.reload(dp)
        assert dp.MAX_BATCH_SIZE == 50
