"""
test_database_backup.py
-----------------------
Unit tests for the database backup and retention management module.

This module validates the creation of SQLite snapshots and the 
automated cleanup of old backups based on retention policies.
"""

import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from src.db.database_backup import (
    create_sqlite_snapshot,
    cleanup_old_backups,
    SQLITE_HEADER,
)


class TestCreateSqliteSnapshot:
    """Tests for the create_sqlite_snapshot function."""

    def test_create_snapshot_valid_db(self, tmp_path):
        """Verify that a valid SQLite database produces a correct snapshot."""
        db_path = tmp_path / "test.db"
        
        # Create a minimal valid SQLite database
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO test (name) VALUES ('sample')")
        conn.commit()
        conn.close()

        snapshot = create_sqlite_snapshot(db_path)
        
        assert snapshot.startswith(SQLITE_HEADER), "Snapshot must start with valid SQLite header"
        assert len(snapshot) > 1000, "Snapshot should have reasonable size"

    def test_create_snapshot_file_not_found(self):
        """Verify that a FileNotFoundError is raised for non-existent paths."""
        with pytest.raises(FileNotFoundError, match="SQLite database does not exist"):
            create_sqlite_snapshot("/nonexistent/path/to/db.db")

    def test_create_snapshot_is_a_directory(self, tmp_path):
        """Verify that an IsADirectoryError is raised if path is a directory."""
        with pytest.raises(IsADirectoryError, match="SQLite database path is not a file"):
            create_sqlite_snapshot(tmp_path)


class TestCleanupOldBackups:
    """Tests for the cleanup_old_backups function."""

    def test_cleanup_nonexistent_directory(self):
        """Verify graceful handling of non-existent backup directories."""
        result = cleanup_old_backups(backup_dir="/nonexistent/backup/dir")
        assert result["files_deleted"] == 0
        assert result["bytes_freed"] == 0

    def test_cleanup_empty_directory(self, tmp_path):
        """Verify that an empty directory results in no deletions."""
        result = cleanup_old_backups(backup_dir=tmp_path)
        assert result["files_deleted"] == 0
        assert result["bytes_freed"] == 0

    def test_cleanup_respects_max_backups(self, tmp_path):
        """Verify that only the newest `max_backups` files are retained."""
        # Create 15 dummy .db files with distinct modification times
        for i in range(15):
            file_path = tmp_path / f"backup_{i}.db"
            file_path.write_bytes(SQLITE_HEADER + b"dummy data")
            # Stagger modification times by 1 second
            old_time = time.time() - (15 - i)
            os.utime(file_path, (old_time, old_time))

        result = cleanup_old_backups(backup_dir=tmp_path, max_backups=10, max_age_days=365)
        
        assert result["files_deleted"] == 5, "Should delete 5 files to respect max_backups=10"
        assert result["bytes_freed"] > 0, "Should report freed bytes"
        
        # Verify the correct files were deleted (oldest ones)
        remaining_files = list(tmp_path.glob("*.db"))
        assert len(remaining_files) == 10
        for f in remaining_files:
            assert int(f.stem.split("_")[1]) >= 5, "Oldest 5 files should have been deleted"

    def test_cleanup_respects_max_age_days(self, tmp_path):
        """Verify that files older than `max_age_days` are deleted regardless of count."""
        # Create 2 files: one old, one new
        old_file = tmp_path / "old_backup.db"
        old_file.write_bytes(SQLITE_HEADER + b"old data")
        old_time = time.time() - (31 * 24 * 60 * 60)  # 31 days ago
        os.utime(old_file, (old_time, old_time))

        new_file = tmp_path / "new_backup.db"
        new_file.write_bytes(SQLITE_HEADER + b"new data")
        # new_file has current time

        result = cleanup_old_backups(backup_dir=tmp_path, max_backups=10, max_age_days=30)
        
        assert result["files_deleted"] == 1, "Should delete the file older than 30 days"
        assert (tmp_path / "new_backup.db").exists(), "New file should be retained"
        assert not (tmp_path / "old_backup.db").exists(), "Old file should be deleted"

    def test_cleanup_handles_os_error_gracefully(self, tmp_path):
        """Verify that OSError during deletion is logged and does not crash the function."""
        file_path = tmp_path / "locked_backup.db"
        file_path.write_bytes(SQLITE_HEADER + b"locked data")
        
        # Mock unlink to raise OSError
        with patch.object(Path, 'unlink', side_effect=OSError("Permission denied")):
            result = cleanup_old_backups(backup_dir=tmp_path, max_backups=1, max_age_days=30)
            
            assert result["files_deleted"] == 0, "Should not count failed deletions"
            assert result["bytes_freed"] == 0, "Should not count freed bytes for failed deletions"
