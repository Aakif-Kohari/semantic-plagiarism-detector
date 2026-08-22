"""
src/db/task_db.py
-----------------
SQLite database manager for the distributed task queue.

Manages the lifecycle of batch scanning jobs, including state transitions
(PENDING -> PROCESSING -> COMPLETED/FAILED), payload storage, and result retrieval.
"""

import sqlite3
import json
import logging
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path("data/task_queue.db")


class JobStatus(str, Enum):
    """Enumeration of valid job states."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@contextmanager
def get_connection(db_path: Optional[Path] = None):
    """Context manager for acquiring and releasing SQLite connections."""
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(path), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_task_db(db_path: Optional[Path] = None) -> None:
    """Create the task queue database schema."""
    with get_connection(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scan_jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                payload TEXT NOT NULL,
                result TEXT,
                error_message TEXT,
                attempts INTEGER DEFAULT 0,
                max_attempts INTEGER DEFAULT 3,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT
            )
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_status 
            ON scan_jobs(status)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_created 
            ON scan_jobs(created_at)
        """)
        
    logger.info("Task queue database initialized at %s", db_path or DEFAULT_DB_PATH)


def create_job(
    payload: Dict[str, Any], 
    max_attempts: int = 3,
    db_path: Optional[Path] = None
) -> str:
    """Insert a new job into the queue."""
    job_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    payload_json = json.dumps(payload)
    
    try:
        with get_connection(db_path) as conn:
            conn.execute(
                """
                INSERT INTO scan_jobs 
                (id, status, payload, attempts, max_attempts, created_at, updated_at)
                VALUES (?, ?, ?, 0, ?, ?, ?)
                """,
                (job_id, JobStatus.PENDING.value, payload_json, max_attempts, now, now)
            )
        logger.info("Created job %s", job_id)
        return job_id
    except sqlite3.Error as e:
        logger.error("Failed to create job: %s", e)
        raise


def claim_job(db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Atomically claim the next PENDING job and mark it as PROCESSING.
    
    Uses an UPDATE with a WHERE clause to ensure only one worker can claim
    a specific job, even in a multi-worker environment.
    """
    try:
        with get_connection(db_path) as conn:
            # Find the oldest PENDING job that hasn't exceeded max attempts
            cursor = conn.execute(
                """
                SELECT id FROM scan_jobs 
                WHERE status = ? AND attempts < max_attempts 
                ORDER BY created_at ASC 
                LIMIT 1
                """,
                (JobStatus.PENDING.value,)
            )
            row = cursor.fetchone()
            if not row:
                return None
                
            job_id = row["id"]
            now = datetime.utcnow().isoformat()
            
            # Atomic update to claim the job
            conn.execute(
                """
                UPDATE scan_jobs 
                SET status = ?, attempts = attempts + 1, started_at = ?, updated_at = ?
                WHERE id = ? AND status = ?
                """,
                (JobStatus.PROCESSING.value, now, now, job_id, JobStatus.PENDING.value)
            )
            
            # Fetch the full job details
            cursor = conn.execute("SELECT * FROM scan_jobs WHERE id = ?", (job_id,))
            job_row = cursor.fetchone()
            if job_row:
                return dict(job_row)
            return None
            
    except sqlite3.Error as e:
        logger.error("Failed to claim job: %s", e)
        return None


def complete_job(
    job_id: str, 
    result: Dict[str, Any],
    db_path: Optional[Path] = None
) -> bool:
    """Mark a job as COMPLETED and store the result."""
    now = datetime.utcnow().isoformat()
    result_json = json.dumps(result)
    
    try:
        with get_connection(db_path) as conn:
            conn.execute(
                """
                UPDATE scan_jobs 
                SET status = ?, result = ?, completed_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (JobStatus.COMPLETED.value, result_json, now, now, job_id)
            )
        logger.info("Job %s completed", job_id)
        return True
    except sqlite3.Error as e:
        logger.error("Failed to complete job %s: %s", job_id, e)
        return False


def fail_job(
    job_id: str, 
    error_message: str,
    db_path: Optional[Path] = None
) -> bool:
    """Mark a job as FAILED. If attempts < max_attempts, it returns to PENDING."""
    now = datetime.utcnow().isoformat()
    
    try:
        with get_connection(db_path) as conn:
            # Check current attempts
            cursor = conn.execute(
                "SELECT attempts, max_attempts FROM scan_jobs WHERE id = ?", 
                (job_id,)
            )
            row = cursor.fetchone()
            if not row:
                return False
                
            if row["attempts"] < row["max_attempts"]:
                # Return to PENDING for retry
                new_status = JobStatus.PENDING.value
                logger.warning("Job %s failed (attempt %d/%d), returning to PENDING", 
                             job_id, row["attempts"], row["max_attempts"])
            else:
                # Permanently FAILED
                new_status = JobStatus.FAILED.value
                logger.error("Job %s permanently failed: %s", job_id, error_message)
                
            conn.execute(
                """
                UPDATE scan_jobs 
                SET status = ?, error_message = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_status, error_message, now, job_id)
            )
        return True
    except sqlite3.Error as e:
        logger.error("Failed to update job %s status: %s", job_id, e)
        return False


def get_job(job_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieve the full details of a specific job."""
    try:
        with get_connection(db_path) as conn:
            cursor = conn.execute("SELECT * FROM scan_jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error("Failed to get job %s: %s", job_id, e)
        return None

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
