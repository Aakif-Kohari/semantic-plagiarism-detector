"""
src/db/task_db.py
-----------------
SQLite-backed job state manager for the distributed task queue (Issue #3146).

Manages job lifecycle states (PENDING → PROCESSING → COMPLETED / FAILED)
and their JSON payloads. Thread-safe via SQLite WAL mode + a per-thread
connection local. The schema is created automatically on first use so the
queue works out-of-the-box without a separate migration step.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────

VALID_STATUSES = ("PENDING", "PROCESSING", "COMPLETED", "FAILED", "DEAD_LETTER")

DEFAULT_DB_PATH = Path(os.environ.get(
    "TASK_QUEUE_DB_PATH",
    str(Path(__file__).resolve().parents[2] / "data" / "task_queue.db"),
))

_connection_pool = threading.local()
_pool_lock = threading.Lock()
_all_connections: set[sqlite3.Connection] = set()

# ── Schema ──────────────────────────────────────────────────────

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS task_jobs (
    id              TEXT PRIMARY KEY,
    status          TEXT NOT NULL DEFAULT 'PENDING',
    payload         TEXT NOT NULL,             -- JSON blob
    result          TEXT,                     -- JSON blob (set on COMPLETED)
    error           TEXT,                     -- error message (set on FAILED)
    retry_count     INTEGER NOT NULL DEFAULT 0,
    max_retries     INTEGER NOT NULL DEFAULT 3,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    started_at      TEXT,
    completed_at    TEXT,
    worker_id       TEXT
);

CREATE INDEX IF NOT EXISTS idx_task_jobs_status
    ON task_jobs (status, created_at);
"""

# ── Connection management ──────────────────────────────────────

def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_connection(db_path: Path) -> sqlite3.Connection:
    """Return a thread-local connection, creating one if needed."""
    conn = getattr(_connection_pool, "conn", None)
    if conn is not None:
        return conn

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        str(db_path),
        check_same_thread=False,
        timeout=30.0,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_SCHEMA_SQL)
    conn.commit()

    with _pool_lock:
        _all_connections.add(conn)
    _connection_pool.conn = conn
    return conn


def _cleanup_all_connections() -> None:
    with _pool_lock:
        for conn in _all_connections:
            try:
                conn.close()
            except Exception:
                pass
        _all_connections.clear()


import atexit
atexit.register(_cleanup_all_connections)


@contextmanager
def get_conn(db_path: Path = DEFAULT_DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """Yield the thread-local connection (no auto-commit)."""
    conn = _get_connection(db_path)
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise


# ── Public API ─────────────────────────────────────────────────

def create_job(
    payload: Dict[str, Any],
    *,
    max_retries: int = 3,
    db_path: Path = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    """Insert a new PENDING job and return its row as a dict."""
    job_id = str(uuid.uuid4())
    now = _utcnow_iso()
    payload_json = json.dumps(payload, ensure_ascii=False)

    with get_conn(db_path) as conn:
        conn.execute(
            """INSERT INTO task_jobs
               (id, status, payload, max_retries, created_at, updated_at)
               VALUES (?, 'PENDING', ?, ?, ?, ?)""",
            (job_id, payload_json, max_retries, now, now),
        )
        conn.commit()

    return get_job(job_id, db_path=db_path)  # type: ignore[return-value]


def get_job(
    job_id: str,
    *,
    db_path: Path = DEFAULT_DB_PATH,
) -> Optional[Dict[str, Any]]:
    """Return one job row as a dict, or None."""
    with get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM task_jobs WHERE id = ?", (job_id,)
        ).fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


def list_jobs(
    *,
    status: Optional[str] = None,
    limit: int = 100,
    db_path: Path = DEFAULT_DB_PATH,
) -> List[Dict[str, Any]]:
    """List jobs, optionally filtered by status, newest first."""
    with get_conn(db_path) as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM task_jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM task_jobs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [_row_to_dict(r) for r in rows]


def claim_next_job(
    worker_id: str,
    *,
    db_path: Path = DEFAULT_DB_PATH,
) -> Optional[Dict[str, Any]]:
    """Atomically claim the oldest PENDING job for a worker.

    Uses ``UPDATE ... RETURNING`` (SQLite 3.35+, which ships with Python 3.10+)
    so the claim + status flip happen in a single statement — no race window.
    """
    now = _utcnow_iso()
    with get_conn(db_path) as conn:
        # Try RETURNING first (fast path, SQLite ≥ 3.35).
        try:
            row = conn.execute(
                """UPDATE task_jobs
                   SET status = 'PROCESSING',
                       updated_at = ?,
                       started_at = ?,
                       worker_id = ?
                   WHERE id = (
                       SELECT id FROM task_jobs
                       WHERE status = 'PENDING'
                   ORDER BY created_at ASC
                   LIMIT 1
                   )
                   RETURNING *""",
                (now, now, worker_id),
            ).fetchone()
            if row is not None:
                conn.commit()
                return _row_to_dict(row)
            conn.commit()
            return None
        except sqlite3.OperationalError:
            # Fallback for older SQLite: two-step claim with row lock.
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """SELECT id FROM task_jobs
                   WHERE status = 'PENDING'
                   ORDER BY created_at ASC LIMIT 1"""
            ).fetchone()
            if row is None:
                conn.commit()
                return None
            conn.execute(
                """UPDATE task_jobs
                   SET status = 'PROCESSING',
                       updated_at = ?,
                       started_at = ?,
                       worker_id = ?
                   WHERE id = ?""",
                (now, now, worker_id, row["id"]),
            )
            conn.commit()
            return get_job(row["id"], db_path=db_path)


def mark_completed(
    job_id: str,
    result: Dict[str, Any],
    *,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    now = _utcnow_iso()
    with get_conn(db_path) as conn:
        conn.execute(
            """UPDATE task_jobs
               SET status = 'COMPLETED',
                   result = ?,
                   updated_at = ?,
                   completed_at = ?
             WHERE id = ?""",
            (json.dumps(result, ensure_ascii=False), now, now, job_id),
        )
        conn.commit()


def mark_failed(
    job_id: str,
    error: str,
    *,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Mark a job as FAILED. If retries remain, re-queue it as PENDING."""
    now = _utcnow_iso()
    with get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT retry_count, max_retries FROM task_jobs WHERE id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            return

        new_retry_count = row["retry_count"] + 1
        if new_retry_count < row["max_retries"]:
            # Re-queue for another attempt.
            conn.execute(
                """UPDATE task_jobs
                   SET status = 'PENDING',
                       retry_count = ?,
                       error = ?,
                       updated_at = ?,
                       worker_id = NULL
                 WHERE id = ?""",
                (new_retry_count, error, now, job_id),
            )
        else:
            # Exhausted retries → move to DEAD_LETTER.
            conn.execute(
                """UPDATE task_jobs
                   SET status = 'DEAD_LETTER',
                       retry_count = ?,
                       error = ?,
                       updated_at = ?,
                       completed_at = ?
                 WHERE id = ?""",
                (new_retry_count, error, now, now, job_id),
            )
        conn.commit()


def mark_dead_letter(
    job_id: str,
    error: str,
    *,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Immediately move a job to DEAD_LETTER, bypassing retries."""
    now = _utcnow_iso()
    with get_conn(db_path) as conn:
        conn.execute(
            """UPDATE task_jobs
               SET status = 'DEAD_LETTER',
                   error = ?,
                   updated_at = ?,
                   completed_at = ?
             WHERE id = ?""",
            (error, now, now, job_id),
        )
        conn.commit()


def get_dead_letter_jobs(
    *,
    limit: int = 50,
    db_path: Path = DEFAULT_DB_PATH,
) -> List[Dict[str, Any]]:
    return list_jobs(status="DEAD_LETTER", limit=limit, db_path=db_path)


def reset_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    """Drop and recreate the task_jobs table (for tests)."""
    with get_conn(db_path) as conn:
        conn.execute("DROP TABLE IF EXISTS task_jobs")
        conn.executescript(_SCHEMA_SQL)
        conn.commit()


# ── Helpers ────────────────────────────────────────────────────

def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    # Parse JSON fields.
    for key in ("payload", "result"):
        v = d.get(key)
        if v and isinstance(v, str):
            try:
                d[key] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                pass
    return d
