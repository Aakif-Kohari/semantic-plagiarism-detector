"""Unit tests for src/utils/storage_metrics.py."""

from pathlib import Path
from src.utils.storage_metrics import (
    calculate_storage_usage,
    get_faiss_index_paths,
    get_sqlite_db_paths,
)


def test_missing_db_files(tmp_path: Path) -> None:
    """Pass non-existent paths, assert sqlite_bytes == 0."""
    db_file = tmp_path / "nonexistent.db"
    usage = calculate_storage_usage(db_paths=[db_file], index_paths=[])
    assert usage["sqlite_bytes"] == 0


def test_missing_index_files(tmp_path: Path) -> None:
    """Pass non-existent paths, assert faiss_bytes == 0."""
    index_file = tmp_path / "nonexistent.index"
    usage = calculate_storage_usage(db_paths=[], index_paths=[index_file])
    assert usage["faiss_bytes"] == 0


def test_real_file(tmp_path: Path) -> None:
    """Create a temp file and verify its size is reported correctly."""
    db_file = tmp_path / "test_corpus.db"
    db_file.write_bytes(b"0" * 1024)
    usage = calculate_storage_usage(db_paths=[db_file], index_paths=[])
    assert usage["sqlite_bytes"] == 1024


def test_get_sqlite_db_paths() -> None:
    """Test get_sqlite_db_paths returns a list of Path objects."""
    paths = get_sqlite_db_paths()
    assert isinstance(paths, list)
    for p in paths:
        assert isinstance(p, Path)


def test_get_faiss_index_paths() -> None:
    """Test get_faiss_index_paths returns a list of Path objects."""
    paths = get_faiss_index_paths()
    assert isinstance(paths, list)
    for p in paths:
        assert isinstance(p, Path)
