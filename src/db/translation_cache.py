"""
src/db/translation_cache.py
---------------------------
SQLite-backed cache for cross-lingual back-translations and translation API
requests to preserve API quota.

Prevents redundant and expensive translation API/model calls by persisting
source_text, target_language, and translated_text mappings.

Maps SHA-256 hash of (foreign_text, source_lang, target_lang) -> cached_text.

Recent Additions (Issue #1956):
- Created translation_cache table schema with source_hash primary key.
- Implemented get_cached_translation() and save_translation() helpers
  for the cross-lingual back-translation pipeline.
"""

import hashlib
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from src.core.app_config import _REPO_ROOT, CORPUS_DB_PATH, FALLBACK_CORPUS_DB_PATH

logger = logging.getLogger(__name__)

# ── Legacy DB Path (backward compatibility) ──────────────────────────────────

# Seed the translation cache DB path from the centralized app_config.
# ``DB_PATH`` is intentionally kept as a module-level string so that tests
# importing ``src.db.translation_cache.DB_PATH`` continue to work.
DB_PATH = str(CORPUS_DB_PATH)

# In-memory counters for lookup hits and misses
cache_hits = 0
cache_misses = 0

# ── Issue #1956 Cache DB Path ────────────────────────────────────────────────

_CACHE_DB_PATH = _REPO_ROOT / "data" / "translation_cache.db"
_lock = threading.Lock()


# ── Issue #1956 Connection Manager ───────────────────────────────────────────


@contextmanager
def _connect():
    """Borrow a reusable SQLite connection for the translation cache."""
    _CACHE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_CACHE_DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_translation_cache() -> None:
    """Create the translation cache table if it does not exist (Issue #1956)."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS translation_cache (
                source_hash TEXT PRIMARY KEY,
                source_text TEXT NOT NULL,
                source_lang TEXT NOT NULL,
                target_lang TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_translation_langs
            ON translation_cache(source_lang, target_lang)
        """)
    logger.info("Translation cache initialized at %s", _CACHE_DB_PATH)


def _hash_text_simple(text: str) -> str:
    """Generate a SHA-256 hash of the text for Issue #1956 cache key lookup."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_cached_translation(
    source_text: str,
    source_lang: str,
    target_lang: str,
) -> str | None:
    """Retrieve a cached translation if it exists (Issue #1956).

    Args:
        source_text: The original text.
        source_lang: Source language code.
        target_lang: Target language code.

    Returns:
        The translated text string, or None if not cached.
    """
    if not source_text:
        return None

    source_hash = _hash_text_simple(source_text)

    try:
        with _connect() as conn:
            cursor = conn.execute(
                """
                SELECT translated_text FROM translation_cache
                WHERE source_hash = ? AND source_lang = ? AND target_lang = ?
                """,
                (source_hash, source_lang, target_lang),
            )
            row = cursor.fetchone()
            return row[0] if row else None
    except sqlite3.Error as exc:
        logger.error("Failed to query translation cache: %s", exc)
        return None


def save_translation(
    source_text: str,
    source_lang: str,
    target_lang: str,
    translated_text: str,
) -> bool:
    """Save a new translation to the cache (Issue #1956).

    Args:
        source_text: The original text.
        source_lang: Source language code.
        target_lang: Target language code.
        translated_text: The resulting translation.

    Returns:
        True if saved successfully, False otherwise.
    """
    if not source_text or not translated_text:
        return False

    source_hash = _hash_text_simple(source_text)
    created_at = datetime.utcnow().isoformat()

    try:
        with _connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO translation_cache
                (source_hash, source_text, source_lang, target_lang, translated_text, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    source_hash,
                    source_text,
                    source_lang,
                    target_lang,
                    translated_text,
                    created_at,
                ),
            )
        return True
    except sqlite3.Error as exc:
        logger.error("Failed to save translation to cache: %s", exc)
        return False


def clear_translation_cache() -> int:
    """Delete all entries from the translation cache (Issue #1956).

    Returns:
        The number of rows deleted.
    """
    try:
        with _connect() as conn:
            cursor = conn.execute("DELETE FROM translation_cache")
            return cursor.rowcount
    except sqlite3.Error as exc:
        logger.error("Failed to clear translation cache: %s", exc)
        return 0


# ── Legacy Cache Functions (Backward Compatibility) ──────────────────────────


def _init_db() -> None:
    """
    Initializes the legacy translation cache table and indexes if they do not exist.

    The table includes a `created_at` timestamp column to support TTL-based
    expiration and purging of stale cache entries.
    """
    path = DB_PATH
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        conn = sqlite3.connect(path)
    except (sqlite3.OperationalError, OSError, PermissionError):
        # Centralized temp-dir fallback (matches corpus_db.py and incidents.py)
        path = str(FALLBACK_CORPUS_DB_PATH)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        conn = sqlite3.connect(path)

    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS legacy_translation_cache (
                    text_hash TEXT PRIMARY KEY,
                    foreign_text TEXT NOT NULL,
                    translated_text TEXT NOT NULL,
                    source_lang TEXT,
                    target_lang TEXT DEFAULT 'en',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_legacy_translation_cache_created_at
                ON legacy_translation_cache(created_at)
                """)
            conn.commit()
    finally:
        conn.close()


def _hash_text(text: str, source_lang: str = "auto", target_lang: str = "en") -> str:
    """
    Generates a unique SHA-256 hash for a given text and language pair.

    Args:
        text: The foreign text to be translated.
        source_lang: The source language code.
        target_lang: The target language code.

    Returns:
        str: A hexadecimal SHA-256 hash string.
    """
    key = f"{source_lang}:{target_lang}:{text.strip()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def get_legacy_cached_translation(
    text: str, source_lang: str = "auto", target_lang: str = "en"
) -> Optional[str]:
    """
    Retrieves a cached translation from the legacy cache if available.

    Args:
        text: The foreign text to look up.
        source_lang: The source language code.
        target_lang: The target language code.

    Returns:
        Optional[str]: The cached translated text, or None if not found.
    """
    _init_db()
    if not text or not text.strip():
        return None

    text_hash = _hash_text(text, source_lang, target_lang)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT translated_text FROM legacy_translation_cache WHERE text_hash = ?",
            (text_hash,),
        )
        row = cursor.fetchone()
        global cache_hits, cache_misses
        if row:
            cache_hits += 1
            return row[0]
        else:
            cache_misses += 1
            return None


def cache_translation(
    foreign_text: str,
    translated_text: str,
    source_lang: str = "auto",
    target_lang: str = "en",
) -> None:
    """
    Stores a new translation in the legacy SQLite cache.

    Args:
        foreign_text: The original foreign text.
        translated_text: The translated text.
        source_lang: The source language code.
        target_lang: The target language code.
    """
    _init_db()
    if not foreign_text or not translated_text:
        return

    text_hash = _hash_text(foreign_text, source_lang, target_lang)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO legacy_translation_cache
            (text_hash, foreign_text, translated_text, source_lang, target_lang)
            VALUES (?, ?, ?, ?, ?)
            """,
            (text_hash, foreign_text, translated_text, source_lang, target_lang),
        )
        conn.commit()


def purge_expired_translation_cache(days_old: int = 60) -> int:
    """
    Purge legacy translation cache entries older than the specified number of days.

    This prevents unbounded database growth by removing stale translation
    pairs that are unlikely to be requested again.

    Args:
        days_old: The age in days after which a cache entry is considered expired.
                  Defaults to 60 days.

    Returns:
        int: The number of rows successfully deleted from the cache.
    """
    _init_db()
    if days_old < 0:
        raise ValueError("days_old must be a non-negative integer.")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM legacy_translation_cache
                WHERE created_at < datetime('now', '-' || ? || ' days')
                """,
                (days_old,),
            )
            deleted_count = cursor.rowcount
            conn.commit()
            logger.info(
                "Purged %d expired legacy translation cache entries older than %d days.",
                deleted_count,
                days_old,
            )
            return deleted_count
    except sqlite3.Error as e:
        logger.error("Failed to purge expired translation cache: %s", e)
        return 0


def purge_translation_cache_older_than(days: int = 30) -> int:
    """
    Purge legacy translation cache entries older than the specified number of days.

    Args:
        days: The age in days after which a cache entry is considered expired.
              Defaults to 30 days.

    Returns:
        int: The number of rows successfully deleted from the cache.
    """
    _init_db()
    if days < 0:
        raise ValueError("days must be a non-negative integer.")

    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=days)
    # SQLite CURRENT_TIMESTAMP defaults to UTC string format YYYY-MM-DD HH:MM:SS
    cutoff_str = cutoff_dt.strftime("%Y-%m-%d %H:%M:%S")

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM legacy_translation_cache WHERE created_at < ?",
                (cutoff_str,),
            )
            deleted_count = cursor.rowcount
            conn.commit()
            logger.info(
                "Purged %d legacy translation cache entries older than %d days.",
                deleted_count,
                days,
            )
            return deleted_count
    except sqlite3.Error as e:
        logger.error("Failed to purge translation cache: %s", e)
        return 0


def get_translation_cache_stats() -> dict[str, int]:
    """
    Get statistics about the current legacy translation cache.

    Returns:
        dict[str, int]: A dictionary containing total entries count.
    """
    _init_db()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM translation_cache")
            row = cursor.fetchone()
            total_count = row[0] if row else 0

            return {
                "total_entries": int(total_count),
            }
    except sqlite3.Error as e:
        logger.error(f"Failed to get translation cache stats: {e}")
        return {"total_entries": 0}


# Fix: Original code referenced undefined `_cache_hits` / `_cache_misses`.
# Map to the existing module-level `cache_hits` / `cache_misses` counters.
_cache_hits = cache_hits
_cache_misses = cache_misses


def get_translation_cache_hit_ratio() -> float:
    """
    Computes the translation cache hit ratio.
    """
    total = cache_hits + cache_misses
    if total == 0:
        return 0.0
    return cache_hits / total


def reset_translation_cache_counters() -> None:
    """Reset the cache hits and misses counters to zero."""
    global cache_hits, cache_misses
    cache_hits = 0
    cache_misses = 0


def get_cache_performance_summary() -> dict[str, Any]:
    """Retrieves cache lookup telemetry, including total requests, hits, misses, and hit ratio percentage.

    Returns:
        dict[str, Any]: A dictionary summary of cache performance statistics.
    """
    total = cache_hits + cache_misses
    ratio = (float(cache_hits) / total * 100.0) if total > 0 else 0.0
    return {
        "total_requests": total,
        "hits": cache_hits,
        "misses": cache_misses,
        "hit_ratio_percentage": ratio,
    }
