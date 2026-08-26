"""Public SQLite migration API."""

from .auth import (
    AUTH_DOWN_MIGRATIONS,
    AUTH_MIGRATIONS,
    AUTH_SCHEMA_VERSION,
    migrate_auth_database,
)
from .common import (
    check_table_exists,
    column_exists,
    delete_all_if_table_exists,
    ensure_migration_history_table,
    get_latest_applied_migration,
    get_migration_status,
    get_user_version,
    index_exists,
    rollback_migration,
    run_migrations,
    table_exists,
)
from .corpus import (
    CORPUS_DOWN_MIGRATIONS,
    CORPUS_MIGRATIONS,
    CORPUS_SCHEMA_VERSION,
    migrate_corpus_database,
)

__all__ = [
    "AUTH_DOWN_MIGRATIONS",
    "AUTH_MIGRATIONS",
    "AUTH_SCHEMA_VERSION",
    "CORPUS_DOWN_MIGRATIONS",
    "CORPUS_MIGRATIONS",
    "CORPUS_SCHEMA_VERSION",
    "column_exists",
    "delete_all_if_table_exists",
    "ensure_migration_history_table",
    "get_latest_applied_migration",
    "get_migration_status",
    "get_user_version",
    "index_exists",
    "migrate_auth_database",
    "migrate_corpus_database",
    "rollback_migration",
    "run_migrations",
    "table_exists",
    "check_table_exists",
]
