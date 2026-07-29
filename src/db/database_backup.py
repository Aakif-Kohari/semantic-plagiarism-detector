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
import os
import shutil
import sqlite3
import stat
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
DEFAULT_BACKUP_DIRECTORY = Path("backups")


class BackupRestoreSecurityError(ValueError):
    """Raised when a backup fails pre-restore security validation."""


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

    with tempfile.TemporaryDirectory(
        prefix="semantic-plagiarism-backup-"
    ) as temporary_directory:
        snapshot_path = (
            Path(temporary_directory) / source_path.name
        )
        source_uri = f"{source_path.as_uri()}?mode=ro"

        with closing(
            sqlite3.connect(
                source_uri,
                uri=True,
                check_same_thread=False,
            )
        ) as source_connection:
            with closing(
                sqlite3.connect(snapshot_path)
            ) as destination:
                source_connection.backup(destination)

        snapshot = snapshot_path.read_bytes()

        if not snapshot.startswith(SQLITE_HEADER):
            raise sqlite3.DatabaseError("Generated backup is not a valid SQLite database.")

        return snapshot


def create_corpus_database_snapshot() -> bytes:
    """Return a downloadable snapshot of the configured corpus DB."""
    return create_sqlite_snapshot(get_corpus_db_path())


def _resolve_authorized_backup(
    source: str | Path,
    backup_dir: str | Path,
) -> Path:
    """Resolve and validate a backup source before restoration.

    The resolved source must remain inside the resolved backup
    directory. This blocks absolute-path injection, ``..`` traversal,
    and symlinks that escape the authorized directory.
    """
    authorized_directory = (
        Path(backup_dir).expanduser().resolve(strict=True)
    )
    if not authorized_directory.is_dir():
        raise NotADirectoryError(
            "Designated backup path is not a directory: "
            f"{authorized_directory}"
        )

    candidate = Path(source).expanduser()
    if not candidate.is_absolute():
        candidate = authorized_directory / candidate

    try:
        resolved_source = candidate.resolve(strict=True)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Backup file does not exist: {candidate}"
        ) from None

    try:
        resolved_source.relative_to(authorized_directory)
    except ValueError as exc:
        raise BackupRestoreSecurityError(
            "Backup source must be inside the designated backup "
            f"directory: {authorized_directory}"
        ) from exc

    source_stat = os.stat(resolved_source, follow_symlinks=True)

    if not stat.S_ISREG(source_stat.st_mode):
        raise BackupRestoreSecurityError(
            "Backup source must be a regular file."
        )

    if source_stat.st_mode & stat.S_IWOTH:
        raise BackupRestoreSecurityError(
            "Refusing to restore a world-writable backup file."
        )

    return resolved_source


def _validate_sqlite_backup(source: Path) -> None:
    """Verify the SQLite header and integrity before replacement."""
    with source.open("rb") as backup_file:
        header = backup_file.read(len(SQLITE_HEADER))

    if header != SQLITE_HEADER:
        raise sqlite3.DatabaseError(
            "Backup file is not a valid SQLite database."
        )

    source_uri = f"{source.as_uri()}?mode=ro"
    with closing(
        sqlite3.connect(source_uri, uri=True)
    ) as connection:
        result = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()

    if result is None or result[0] != "ok":
        details = result[0] if result else "unknown failure"
        raise sqlite3.DatabaseError(
            f"SQLite backup integrity check failed: {details}"
        )


def restore(
    source: str | Path,
    *,
    backup_dir: str | Path = DEFAULT_BACKUP_DIRECTORY,
    destination: str | Path | None = None,
) -> Path:
    """Securely restore an authorized SQLite backup.

    Security validation happens before any destination file is
    modified. The source must resolve inside ``backup_dir`` and must
    not be world-writable. A valid backup is copied to a temporary
    file in the destination directory and atomically installed with
    ``os.replace``.

    Args:
        source: Backup filename or path. Relative names are resolved
            beneath ``backup_dir``.
        backup_dir: Authorized directory containing restore sources.
        destination: Live database path. Defaults to the configured
            corpus database.

    Returns:
        The resolved destination path.

    Raises:
        BackupRestoreSecurityError: For unauthorized paths, unsafe
            file types, or world-writable source files.
        FileNotFoundError: When the backup directory or source is
            missing.
        sqlite3.DatabaseError: When the backup is not a healthy SQLite
            database.
        OSError: When the atomic file replacement fails.
    """
    source_path = _resolve_authorized_backup(
        source,
        backup_dir,
    )
    _validate_sqlite_backup(source_path)

    destination_path = Path(
        destination
        if destination is not None
        else get_corpus_db_path()
    ).expanduser().resolve()
    destination_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if source_path == destination_path:
        raise BackupRestoreSecurityError(
            "Backup source and restore destination must differ."
        )

    temporary_path: Path | None = None
    try:
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination_path.name}.restore-",
            suffix=".tmp",
            dir=destination_path.parent,
        )
        os.close(file_descriptor)
        temporary_path = Path(temporary_name)

        shutil.copyfile(source_path, temporary_path)
        _validate_sqlite_backup(temporary_path)

        with temporary_path.open("rb") as restored_file:
            os.fsync(restored_file.fileno())

        os.replace(temporary_path, destination_path)
        temporary_path = None
    finally:
        if (
            temporary_path is not None
            and temporary_path.exists()
        ):
            temporary_path.unlink()

    logger.info(
        "Database restored securely from %s to %s.",
        source_path,
        destination_path,
    )
    return destination_path


def restore_database_backup(
    source: str | Path,
    *,
    backup_dir: str | Path = DEFAULT_BACKUP_DIRECTORY,
    destination: str | Path | None = None,
) -> Path:
    """Descriptive alias for :func:`restore`."""
    return restore(
        source,
        backup_dir=backup_dir,
        destination=destination,
    )


def cleanup_old_backups(
    backup_dir: Union[str, Path] = DEFAULT_BACKUP_DIRECTORY,
    max_backups: int = 10,
    max_age_days: int = 30,
) -> Dict[str, int]:
    """Remove stale ``.db`` backups using count and age limits."""
    backup_path = Path(backup_dir)

    if not backup_path.exists() or not backup_path.is_dir():
        logger.warning(
            "Backup directory does not exist: %s",
            backup_path,
        )
        return {
            "files_deleted": 0,
            "bytes_freed": 0,
        }

    db_files = list(backup_path.glob("*.db"))
    if not db_files:
        logger.info(
            "No .db backup files found to clean up."
        )
        return {
            "files_deleted": 0,
            "bytes_freed": 0,
        }

    db_files.sort(
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    current_time = time.time()
    max_age_seconds = max_age_days * 24 * 60 * 60

    files_deleted = 0
    bytes_freed = 0

    for index, file_path in enumerate(db_files):
        file_stat = file_path.stat()
        file_age_seconds = (
            current_time - file_stat.st_mtime
        )

        if (
            index >= max_backups
            or file_age_seconds > max_age_seconds
        ):
            try:
                file_path.unlink()
                files_deleted += 1
                bytes_freed += file_stat.st_size
                logger.info(
                    "Deleted stale backup: %s "
                    "(age: %.1f days)",
                    file_path.name,
                    file_age_seconds / 86400,
                )
            except OSError as exception:
                logger.error(
                    "Failed to delete backup %s: %s",
                    file_path.name,
                    exception,
                )

    logger.info(
        "Backup cleanup complete. Deleted %s files, "
        "freed %s bytes.",
        files_deleted,
        bytes_freed,
    )
    return {
        "files_deleted": files_deleted,
        "bytes_freed": bytes_freed,
    }
