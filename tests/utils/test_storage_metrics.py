"""Unit tests for src/utils/storage_metrics.py."""

import logging
from pathlib import Path
from unittest.mock import patch

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


def test_path_resolution_logs_debug_warning(caplog) -> None:
    """Verify that exceptions during path resolution log debug warnings."""
    with caplog.at_level(logging.DEBUG):
        with patch(
            "src.db.corpus_db.get_corpus_db_path",
            side_effect=Exception("Database path resolution error"),
        ):
            get_sqlite_db_paths()
            assert (
                "Could not resolve path: Database path resolution error" in caplog.text
            )


class TestCalculateStorageUsageFileCounts:
    """Test suite for file count tracking in calculate_storage_usage() (Issue #2253)."""

    def test_returns_zero_counts_for_empty_paths(self, tmp_path):
        """Verify file counts are 0 when no files exist at provided paths."""
        from src.utils.storage_metrics import calculate_storage_usage
        
        # Pass empty lists to simulate no files found
        result = calculate_storage_usage(db_paths=[], index_paths=[])
        
        assert result["sqlite_file_count"] == 0
        assert result["faiss_file_count"] == 0
        assert result["formatted_total"] == "0.00 MB"

    def test_counts_sqlite_files_correctly(self, tmp_path):
        """Verify sqlite_file_count increments for each valid .db file."""
        from src.utils.storage_metrics import calculate_storage_usage
        
        # Create 3 dummy SQLite files
        db_paths = []
        for i in range(3):
            db_file = tmp_path / f"test_{i}.db"
            db_file.write_bytes(b"x" * 1024)  # 1KB each
            db_paths.append(db_file)
            
        result = calculate_storage_usage(db_paths=db_paths, index_paths=[])
        
        assert result["sqlite_file_count"] == 3
        assert result["faiss_file_count"] == 0
        assert result["sqlite_bytes"] == 3072

    def test_counts_faiss_files_correctly(self, tmp_path):
        """Verify faiss_file_count increments for each valid .index file."""
        from src.utils.storage_metrics import calculate_storage_usage
        
        # Create 2 dummy FAISS index files
        index_paths = []
        for i in range(2):
            idx_file = tmp_path / f"corpus_{i}.index"
            idx_file.write_bytes(b"y" * 2048)  # 2KB each
            index_paths.append(idx_file)
            
        result = calculate_storage_usage(db_paths=[], index_paths=index_paths)
        
        assert result["sqlite_file_count"] == 0
        assert result["faiss_file_count"] == 2
        assert result["faiss_bytes"] == 4096

    def test_ignores_nonexistent_paths_in_count(self, tmp_path):
        """Verify nonexistent paths don't increment the file count."""
        from src.utils.storage_metrics import calculate_storage_usage
        
        existing_db = tmp_path / "real.db"
        existing_db.write_bytes(b"data")
        
        nonexistent_db = tmp_path / "missing.db"
        
        result = calculate_storage_usage(
            db_paths=[existing_db, nonexistent_db],
            index_paths=[]
        )
        
        # Should only count the existing file
        assert result["sqlite_file_count"] == 1

    def test_ignores_directories_in_count(self, tmp_path):
        """Verify directories ending in .db don't increment the file count."""
        from src.utils.storage_metrics import calculate_storage_usage
        
        # Create a directory with .db extension
        db_dir = tmp_path / "fake.db"
        db_dir.mkdir()
        
        result = calculate_storage_usage(db_paths=[db_dir], index_paths=[])
        
        assert result["sqlite_file_count"] == 0

