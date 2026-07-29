"""
database_backup.py
------------------
Consistent SQLite database download helpers and retention management.

This module provides utilities for creating transactionally consistent 
snapshots of SQLite databases and managing the lifecycle of backup files 
to prevent disk space exhaustion.

Recent Additions (Issue #465):
- Added `cleanup_old_backups` function to enforce retention policies 
  (max backups count and max age in days).
"""

from __future__ import annotations

import logging
import sqlite3
import tempfile
import time
from contextlib import closing
from pathlib import Path
from typing import Dict, Union

from src.db.corpus_db import get_corpus_db_path

# ── Logger Configuration ───────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SQLITE_HEADER = b"SQLite format 3\x00"


def create_sqlite_snapshot(database_path: str | Path) -> bytes:
    """
    Return a transactionally consistent SQLite snapshot.

    SQLite's online backup API is used instead of reading a live database
    file directly. This includes committed pages correctly even when the
    source database uses WAL journaling.
    
    Args:
        database_path: Path to the source SQLite database.
        
    Returns:
        bytes: The raw bytes of the SQLite snapshot.
        
    Raises:
        FileNotFoundError: If the source database does not exist.
        IsADirectoryError: If the source path is a directory.
        sqlite3.DatabaseError: If the generated backup is invalid.
    """
    source_path = Path(database_path).expanduser().resolve()

    if not source_path.exists():
        raise FileNotFoundError(f"SQLite database does not exist: {source_path}")
    if not source_path.is_file():
        raise IsADirectoryError(f"SQLite database path is not a file: {source_path}")

    with tempfile.TemporaryDirectory(prefix="semantic-plagiarism-backup-") as temporary_directory:
        snapshot_path = Path(temporary_directory) / source_path.name
        source_uri = f"{source_path.as_uri()}?mode=ro"

        with closing(sqlite3.connect(source_uri, uri=True, check_same_thread=False)) as source_connection:
            with closing(sqlite3.connect(snapshot_path)) as destination:
                source_connection.backup(destination)

        snapshot = snapshot_path.read_bytes()

        if not snapshot.startswith(SQLITE_HEADER):
            raise sqlite3.DatabaseError("Generated backup is not a valid SQLite database.")

        return snapshot


def create_corpus_database_snapshot() -> bytes:
    """Return a downloadable snapshot of the configured corpus DB."""
    return create_sqlite_snapshot(get_corpus_db_path())


def cleanup_old_backups(
    backup_dir: Union[str, Path] = "backups",
    max_backups: int = 10,
    max_age_days: int = 30
) -> Dict[str, int]:
    """
    Removes stale .db backup files based on a retention policy.
    
    This function prevents disk space exhaustion by enforcing two rules:
    1. Keep at most `max_backups` files.
    2. Delete any file older than `max_age_days`.
    
    Args:
        backup_dir: Directory containing the backup files. Defaults to "backups".
        max_backups: Maximum number of backup files to retain. Defaults to 10.
        max_age_days: Maximum age in days for a backup file to be retained. Defaults to 30.
        
    Returns:
        dict: A summary of the cleanup operation containing:
            - "files_deleted": Number of files successfully removed.
            - "bytes_freed": Total disk space freed in bytes.
    """
    backup_path = Path(backup_dir)
    
    if not backup_path.exists() or not backup_path.is_dir():
        logger.warning(f"Backup directory does not exist: {backup_path}")
        return {"files_deleted": 0, "bytes_freed": 0}
        
    # Find all .db files in the directory
    db_files = list(backup_path.glob("*.db"))
    if not db_files:
        logger.info("No .db backup files found to clean up.")
        return {"files_deleted": 0, "bytes_freed": 0}
        
    # Sort by modification time, newest first
    db_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    current_time = time.time()
    max_age_seconds = max_age_days * 24 * 60 * 60
    
    files_deleted = 0
    bytes_freed = 0
    
    for i, file_path in enumerate(db_files):
        file_age_seconds = current_time - file_path.stat().st_mtime
        file_size = file_path.stat().st_size
        
        # Check if it exceeds max_backups OR max_age_days
        if i >= max_backups or file_age_seconds > max_age_seconds:
            try:
                file_path.unlink()
                files_deleted += 1
                bytes_freed += file_size
                logger.info(f"Deleted stale backup: {file_path.name} (Age: {file_age_seconds/86400:.1f} days)")
            except OSError as e:
                logger.error(f"Failed to delete backup {file_path.name}: {e}")
                
    logger.info(f"Backup cleanup complete. Deleted {files_deleted} files, freed {bytes_freed} bytes.")
    return {"files_deleted": files_deleted, "bytes_freed": bytes_freed}
