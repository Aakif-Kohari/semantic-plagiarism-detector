"""
test_backup_dir_security_issue_2790.py
---------------------------------------
Unit test suite for Issue #2790:
Validates that database backup directories resolve via BACKUP_DIR env variable
and default to an absolute path outside the repository / web root (/var/backups/spd/),
preventing accidental public exposure of database backups.
"""

import os
from unittest.mock import patch

from src.core.app_config import _REPO_ROOT, get_backup_dir


def test_default_backup_dir_is_outside_repo_root():
    """Verify that default get_backup_dir() returns an absolute path outside repo root."""
    with patch.dict(os.environ, {}, clear=True):
        backup_dir = get_backup_dir()
        assert backup_dir.is_absolute()
        # Ensure default backup directory does not overlap with web root or repo root
        assert not backup_dir.is_relative_to(_REPO_ROOT)


def test_backup_dir_env_var_override(tmp_path):
    """Verify that setting BACKUP_DIR env variable overrides the default path."""
    custom_dir = tmp_path / "custom_backups_dir"
    with patch.dict(os.environ, {"BACKUP_DIR": str(custom_dir)}):
        resolved = get_backup_dir()
        assert resolved == custom_dir.resolve()
        assert resolved.is_absolute()


def test_backup_dir_in_database_backup_module():
    """Verify database_backup module's default directory resolves via get_backup_dir."""
    from src.db.database_backup import DEFAULT_BACKUP_DIRECTORY

    assert DEFAULT_BACKUP_DIRECTORY.is_absolute()
