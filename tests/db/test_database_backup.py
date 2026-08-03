"""
test_database_backup.py
-----------------------
Unit tests for the database backup, restoration, and retention management module.

This module validates:
- SQLite snapshot creation (including corpus DB snapshots).
- Password-protected ZIP backups.
- Secure database restore workflow.
- Database optimization via VACUUM and PRAGMA optimize.
- Automated cleanup of old backups based on retention policies.
- Database file size inspection (issue #1047).
"""

import logging
import os
import sqlite3
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from src.db.database_backup import (
    SQLITE_HEADER,
    BackupRestoreSecurityError,
    cleanup_old_backups,
    create_password_protected_backup,
    create_sqlite_snapshot,
    get_database_size_bytes,
    optimize_database,
    restore,
    run_incremental_vacuum,
)


class TestCreateSqliteSnapshot:
    """Tests for the create_sqlite_snapshot function."""

    def test_create_snapshot_valid_db(self, tmp_path):
        """Verify that a valid SQLite database produces a correct snapshot."""
        db_path = tmp_path / "test.db"

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO test (name) VALUES ('sample')")
        conn.commit()
        conn.close()

        snapshot = create_sqlite_snapshot(db_path)

        assert snapshot.startswith(
            SQLITE_HEADER
        ), "Snapshot must start with valid SQLite header"
        assert len(snapshot) > 1000, "Snapshot should have reasonable size"

    def test_create_snapshot_file_not_found(self):
        """Verify that a FileNotFoundError is raised for non-existent paths."""
        with pytest.raises(FileNotFoundError, match="SQLite database does not exist"):
            create_sqlite_snapshot("/nonexistent/path/to/db.db")

    def test_create_snapshot_is_a_directory(self, tmp_path):
        """Verify that an IsADirectoryError is raised if path is a directory."""
        with pytest.raises(
            IsADirectoryError, match="SQLite database path is not a file"
        ):
            create_sqlite_snapshot(tmp_path)


class TestCorpusSnapshotAndBackup:
    """Tests for corpus snapshots and password-protected backups."""

    @pytest.fixture
    def temp_db_path(self, tmp_path):
        """Create a temporary SQLite database with some test data."""
        db_file = tmp_path / "test_corpus.db"

        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
        cursor.execute(
            "INSERT INTO test_table (name) VALUES ('test1'), ('test2'), ('test3')"
        )

        # Insert and delete data to create fragmentation for VACUUM to clean
        for i in range(100):
            cursor.execute(
                "INSERT INTO test_table (name) VALUES (?)", (f"temp_data_{i}",)
            )

        cursor.execute("DELETE FROM test_table WHERE name LIKE 'temp_data_%'")
        conn.commit()
        conn.close()

        return str(db_file)

    def test_create_corpus_database_snapshot(self, temp_db_path):
        """Test that a valid binary snapshot is created given a specific DB file."""
        snapshot = create_sqlite_snapshot(temp_db_path)

        assert isinstance(snapshot, bytes)
        assert len(snapshot) > 0
        assert snapshot[:16] == SQLITE_HEADER

    def test_create_corpus_database_snapshot_missing_file(self, tmp_path):
        """Test snapshot creation raises FileNotFoundError when database file does not exist."""
        missing_db = tmp_path / "nonexistent.db"
        with pytest.raises(FileNotFoundError, match="SQLite database does not exist"):
            create_sqlite_snapshot(missing_db)

    def test_create_password_protected_backup(self, temp_db_path):
        """Test creation of a password-protected ZIP backup."""
        snapshot = create_sqlite_snapshot(temp_db_path)
        password = "secure_password_123"

        zip_data = create_password_protected_backup(snapshot, password, "corpus.db")

        assert isinstance(zip_data, bytes)
        assert len(zip_data) > 0
        assert zip_data[:4] == b"PK\x03\x04"


class TestOptimizeDatabase:
    """Tests for the optimize_database function."""

    @pytest.fixture
    def temp_db_path(self, tmp_path):
        """Create a temporary SQLite database with fragmented data."""
        db_file = tmp_path / "test_opt.db"
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
        cursor.execute(
            "INSERT INTO test_table (name) VALUES ('test1'), ('test2'), ('test3')"
        )

        for i in range(100):
            cursor.execute(
                "INSERT INTO test_table (name) VALUES (?)", (f"temp_data_{i}",)
            )

        cursor.execute("DELETE FROM test_table WHERE name LIKE 'temp_data_%'")
        conn.commit()
        conn.close()

        return str(db_file)

    def test_optimize_database_success(self, temp_db_path):
        """Test that optimize_database successfully runs VACUUM and ANALYZE."""
        result = optimize_database(temp_db_path)

        assert result is True
        assert os.path.exists(temp_db_path)

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM test_table LIMIT 1")
        assert cursor.fetchone()[0] == "test1"
        conn.close()

    def test_optimize_database_missing_file(self, tmp_path):
        """Test optimization when the database file does not exist."""
        missing_db = tmp_path / "nonexistent.db"
        result = optimize_database(missing_db)

        assert result is False

    def test_optimize_database_logs_size_reduction(self, temp_db_path, caplog):
        """Test that optimize_database logs the size reduction statistics."""
        caplog.set_level(logging.INFO)

        result = optimize_database(temp_db_path)

        assert result is True
        assert "Starting database optimization" in caplog.text
        assert "Executing PRAGMA optimize" in caplog.text
        assert "Executing VACUUM" in caplog.text
        assert "Executing ANALYZE" in caplog.text
        assert "Database optimization completed successfully" in caplog.text
        assert "Space reclaimed:" in caplog.text

    def test_run_incremental_vacuum(self, temp_db_path):
        """Verify incremental vacuum executes successfully."""
        conn = sqlite3.connect(temp_db_path)
        try:
            assert run_incremental_vacuum(conn) is True
        finally:
            conn.close()


class TestRestoreDatabase:
    """Tests for secure database restoration."""

    def test_restore_database_success(self, tmp_path):
        """Test restoring a valid SQLite database backup into a target destination."""
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        source_db = backup_dir / "valid_backup.db"
        conn = sqlite3.connect(str(source_db))
        conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO test_table (name) VALUES ('item1')")
        conn.commit()
        conn.close()

        dest_db = tmp_path / "restored_corpus.db"

        restored_path = restore(
            source="valid_backup.db",
            backup_dir=backup_dir,
            destination=dest_db,
        )

        assert restored_path == dest_db.resolve()
        assert dest_db.exists()

        conn = sqlite3.connect(str(dest_db))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM test_table")
        assert cursor.fetchone()[0] == "item1"
        conn.close()

    def test_restore_database_security_error_outside_dir(self, tmp_path):
        """Verify restore raises BackupRestoreSecurityError when source lies outside backup_dir."""
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        outside_file = tmp_path / "outside.db"
        outside_file.write_bytes(SQLITE_HEADER + b"data")

        with pytest.raises(
            BackupRestoreSecurityError,
            match="must be inside the designated backup directory",
        ):
            restore(
                source="../outside.db",
                backup_dir=backup_dir,
                destination=tmp_path / "target.db",
            )


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
        for i in range(15):
            file_path = tmp_path / f"backup_{i}.db"
            file_path.write_bytes(SQLITE_HEADER + b"dummy data")
            old_time = time.time() - (15 - i)
            os.utime(file_path, (old_time, old_time))

        result = cleanup_old_backups(
            backup_dir=tmp_path, max_backups=10, max_age_days=365
        )

        assert (
            result["files_deleted"] == 5
        ), "Should delete 5 files to respect max_backups=10"
        assert result["bytes_freed"] > 0, "Should report freed bytes"

        remaining_files = list(tmp_path.glob("*.db"))
        assert len(remaining_files) == 10
        for f in remaining_files:
            assert (
                int(f.stem.split("_")[1]) >= 5
            ), "Oldest 5 files should have been deleted"

    def test_cleanup_respects_max_age_days(self, tmp_path):
        """Verify that files older than `max_age_days` are deleted regardless of count."""
        old_file = tmp_path / "old_backup.db"
        old_file.write_bytes(SQLITE_HEADER + b"old data")
        old_time = time.time() - (31 * 24 * 60 * 60)  # 31 days ago
        os.utime(old_file, (old_time, old_time))

        new_file = tmp_path / "new_backup.db"
        new_file.write_bytes(SQLITE_HEADER + b"new data")

        result = cleanup_old_backups(
            backup_dir=tmp_path, max_backups=10, max_age_days=30
        )

        assert result["files_deleted"] == 1, "Should delete the file older than 30 days"
        assert (tmp_path / "new_backup.db").exists(), "New file should be retained"
        assert not (tmp_path / "old_backup.db").exists(), "Old file should be deleted"

    def test_cleanup_handles_os_error_gracefully(self, tmp_path):
        """Verify that OSError during deletion is logged and does not crash the function."""
        file_path = tmp_path / "locked_backup.db"
        file_path.write_bytes(SQLITE_HEADER + b"locked data")

        with patch.object(Path, "unlink", side_effect=OSError("Permission denied")):
            result = cleanup_old_backups(
                backup_dir=tmp_path, max_backups=1, max_age_days=30
            )

            assert result["files_deleted"] == 0, "Should not count failed deletions"
            assert (
                result["bytes_freed"] == 0
            ), "Should not count freed bytes for failed deletions"


class TestGetDatabaseSizeBytes:
    """Tests for the get_database_size_bytes helper (issue #1047)."""

    def test_returns_zero_for_nonexistent_file(self, tmp_path):
        """A missing database file must report size 0, not raise."""
        missing_db = tmp_path / "does_not_exist.db"

        size = get_database_size_bytes(missing_db)

        assert size == 0

    def test_returns_zero_for_nonexistent_file_string_path(self, tmp_path):
        """The function must accept str paths as well as Path objects."""
        missing_db = str(tmp_path / "does_not_exist.db")

        size = get_database_size_bytes(missing_db)

        assert size == 0

    def test_returns_size_for_temp_db(self, tmp_path):
        """Verify size calculation for a temp DB created with known content.

        Acceptance criterion from issue #1047:
            "Add unit test verifying size calculation for temp DB."
        """
        db_path = tmp_path / "test_size.db"

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, payload TEXT)")
        conn.executemany(
            "INSERT INTO sample (payload) VALUES (?)",
            [(f"row-{i}",) for i in range(50)],
        )
        conn.commit()
        conn.close()

        size = get_database_size_bytes(db_path)

        # The file must exist and report a positive size.
        assert size > 0
        # The reported size must match the actual on-disk size.
        assert size == db_path.stat().st_size

    def test_size_grows_after_insert(self, tmp_path):
        """Inserting more data must increase the reported size."""
        db_path = tmp_path / "test_grow.db"

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE docs (id INTEGER PRIMARY KEY, content TEXT)")
        conn.execute("INSERT INTO docs (content) VALUES ('seed')")
        conn.commit()
        conn.close()

        size_before = get_database_size_bytes(db_path)

        conn = sqlite3.connect(str(db_path))
        conn.executemany(
            "INSERT INTO docs (content) VALUES (?)",
            [(f"padding-{'x' * 200}-{i}",) for i in range(100)],
        )
        conn.commit()
        conn.close()

        size_after = get_database_size_bytes(db_path)

        assert size_after > size_before

    def test_accepts_path_and_str_equivalently(self, tmp_path):
        """Both Path and str inputs must resolve to the same size."""
        db_path = tmp_path / "test_type.db"
        db_path.write_bytes(SQLITE_HEADER + b"payload")

        size_from_path = get_database_size_bytes(db_path)
        size_from_str = get_database_size_bytes(str(db_path))

        assert size_from_path == size_from_str == db_path.stat().st_size

    def test_expands_user_home(self, monkeypatch, tmp_path):
        """A leading ``~`` must be expanded against the home directory."""
        db_path = tmp_path / "home_db.db"
        db_path.write_bytes(b"not-a-real-sqlite-db-but-size-still-works")
        # Path.expanduser() reads $HOME (not Path.home()), so patch the env var.
        monkeypatch.setenv("HOME", str(tmp_path))

        size = get_database_size_bytes("~/home_db.db")

        assert size == db_path.stat().st_size
