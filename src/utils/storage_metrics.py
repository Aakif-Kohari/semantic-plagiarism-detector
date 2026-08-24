"""src/utils/storage_metrics.py - Disk usage calculation for SQLite databases and FAISS index."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _deduplicate_paths(paths: list[Path]) -> list[Path]:
    """Remove duplicate paths by comparing their resolved absolute form."""
    unique_paths: list[Path] = []
    seen: set[Path] = set()
    for p in paths:
        try:
            resolved = p.resolve()
            if resolved not in seen:
                seen.add(resolved)
                unique_paths.append(p)
        except Exception as e:
            logger.debug("Could not resolve path: %s", e)
    return unique_paths


def get_sqlite_db_paths() -> list[Path]:
    """Retrieve unique paths of SQLite database files in standard locations.

    Collects the three configured application databases (corpus, auth and
    incidents) plus any additional ``*.db`` files sitting in the repository
    root or in ``data/``.

    Each configured path is resolved independently and a failure to resolve
    one is logged at debug level and skipped, so a partially installed
    environment still reports usage for the databases it can see.

    Returns:
        List[Path]: Existing-or-not database paths, de-duplicated by their
        resolved absolute form. Paths are returned in discovery order.
    """
    paths: list[Path] = []

    # 1. Corpus DB path
    try:
        from src.db.corpus_db import get_corpus_db_path

        paths.append(get_corpus_db_path())
    except Exception as e:
        logger.debug("Could not resolve path: %s", e)

    # 2. Auth DB path
    try:
        from src.db.auth import get_auth_db_path

        paths.append(get_auth_db_path())
    except Exception as e:
        logger.debug("Could not resolve path: %s", e)

    # 3. Incidents DB path
    try:
        from src.db.incidents import DEFAULT_DB_PATH as incidents_db_path

        paths.append(Path(incidents_db_path))
    except Exception as e:
        logger.debug("Could not resolve path: %s", e)

    # 4. Search root and data directories for additional .db files
    base_dir = Path(__file__).resolve().parents[2]
    data_dir = base_dir / "data"
    for folder in [base_dir, data_dir]:
        if folder.exists():
            for file_path in folder.glob("*.db"):
                paths.append(file_path)

    # Deduplicate resolved absolute paths
    return _deduplicate_paths(paths)


def get_faiss_index_paths() -> list[Path]:
    """Retrieve unique paths of FAISS index files in standard locations.

    Always includes the two default ``corpus.index`` locations (repository
    root and ``data/``) so a caller can report "0 bytes" for an index that has
    not been built yet, then adds any other ``*.index`` files found alongside
    them.

    Returns:
        List[Path]: Existing-or-not index paths, de-duplicated by their
        resolved absolute form. Paths are returned in discovery order.
    """
    paths: list[Path] = []

    base_dir = Path(__file__).resolve().parents[2]
    data_dir = base_dir / "data"

    # Default corpus.index
    paths.append(base_dir / "corpus.index")
    paths.append(data_dir / "corpus.index")

    for folder in [base_dir, data_dir]:
        if folder.exists():
            for file_path in folder.glob("*.index"):
                paths.append(file_path)

    return _deduplicate_paths(paths)


def calculate_storage_usage(
    db_paths: Optional[list[Path]] = None,
    index_paths: Optional[list[Path]] = None,
) -> dict[str, Any]:
    """Calculate total SQLite + FAISS disk usage in bytes and formatted megabytes.

    Returns:
        Dict[str, Any]: Dictionary containing:
            - 'sqlite_bytes': int (bytes used by SQLite files)
            - 'faiss_bytes': int (bytes used by FAISS index files)
            - 'total_bytes': int (combined bytes)
            - 'sqlite_mb': float (megabytes, rounded to 2 decimal places)
            - 'faiss_mb': float (megabytes, rounded to 2 decimal places)
            - 'total_mb': float (megabytes, rounded to 2 decimal places)
            - 'formatted_total': str (formatted total string e.g. "1.25 MB")
            - 'formatted_sqlite': str (formatted SQLite size)
            - 'formatted_faiss': str (formatted FAISS index size)
            - 'sqlite_file_count': int (number of SQLite files found)
            - 'faiss_file_count': int (number of FAISS index files found)
    """
    if db_paths is None:
        db_paths = get_sqlite_db_paths()
    if index_paths is None:
        index_paths = get_faiss_index_paths()

    sqlite_bytes = 0
    sqlite_file_count = 0
    for db_path in db_paths:
        try:
            if db_path.exists() and db_path.is_file():
                sqlite_bytes += db_path.stat().st_size
                sqlite_file_count += 1
        except OSError as e:
            logger.debug("Could not resolve path: %s", e)

    faiss_bytes = 0
    faiss_file_count = 0
    for idx_path in index_paths:
        try:
            if idx_path.exists() and idx_path.is_file():
                faiss_bytes += idx_path.stat().st_size
                faiss_file_count += 1
        except OSError as e:
            logger.debug("Could not resolve path: %s", e)

    total_bytes = sqlite_bytes + faiss_bytes

    sqlite_mb = round(sqlite_bytes / (1024 * 1024), 2)
    faiss_mb = round(faiss_bytes / (1024 * 1024), 2)
    total_mb = round(total_bytes / (1024 * 1024), 2)

    return {
        "sqlite_bytes": sqlite_bytes,
        "faiss_bytes": faiss_bytes,
        "total_bytes": total_bytes,
        "sqlite_mb": sqlite_mb,
        "faiss_mb": faiss_mb,
        "total_mb": total_mb,
        "formatted_total": f"{total_mb:.2f} MB",
        "formatted_sqlite": f"{sqlite_mb:.2f} MB",
        "formatted_faiss": f"{faiss_mb:.2f} MB",
        "sqlite_file_count": sqlite_file_count,
        "faiss_file_count": faiss_file_count,
    }


def calculate_database_fragmentation(db_path: str) -> dict[str, float | int | str]:
    """
    Queries SQLite storage engine page allocations to evaluate structural 
    fragmentation levels and identify if an analytical VACUUM routine is required.
    
    Returns:
        Dict detailing page counts, freelist counts, and calculated fragmentation ratio.
    """
    connection = None
    try:
        # Establish a read-only or direct cursor sequence into the target SQLite file
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()
        
        # 1. Retrieve the count of empty, deleted, or unallocated database pages
        cursor.execute("PRAGMA freelist_count;")
        freelist_count: int = cursor.fetchone()[0]
        
        # 2. Retrieve the cumulative count of total structural database pages
        cursor.execute("PRAGMA page_count;")
        page_count: int = cursor.fetchone()[0]
        
        # Handle zero-allocation edge cases gracefully to avoid ZeroDivisionError logs
        if page_count == 0:
            return {
                "freelist_count": 0,
                "page_count": 0,
                "fragmentation_percentage": 0.0,
                "status": "EMPTY_DATABASE"
            }
            
        # Calculate fragmentation percentage based on space-recovery eligibility
        fragmentation_percentage: float = (freelist_count / page_count) * 100.0
        
        # Determine actionable optimization benchmarks
        # Standard administrative threshold sets optimization need at > 20% bloat
        needs_vacuum: bool = fragmentation_percentage > 20.0
        
        return {
            "freelist_count": freelist_count,
            "page_count": page_count,
            "fragmentation_percentage": round(fragmentation_percentage, 2),
            "status": "VACUUM_RECOMMENDED" if needs_vacuum else "OPTIMAL"
        }
        
    except sqlite3.Error as error:
        # Capture engine connectivity abnormalities safely
        return {
            "error": "SQLITE_QUERY_FAILURE",
            "details": str(error),
            "fragmentation_percentage": -1.0
        }
        
    finally:
        if connection:
            connection.close()
