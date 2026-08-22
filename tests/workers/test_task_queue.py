"""
tests/workers/test_task_queue.py
--------------------------------
Integration tests for the distributed task queue system.
"""

import pytest
import time
import json
from pathlib import Path

from src.db.task_db import (
    initialize_task_db,
    create_job,
    claim_job,
    complete_job,
    fail_job,
    get_job,
    JobStatus,
)
from src.workers.task_queue import TaskQueue


@pytest.fixture
def temp_db(tmp_path):
    """Provide a temporary database for testing."""
    db_path = tmp_path / "test_tasks.db"
    initialize_task_db(db_path)
    return db_path


class TestTaskDB:
    """Test suite for low-level DB operations."""

    def test_create_and_get_job(self, temp_db):
        """Verify a job can be created and retrieved."""
        payload = {"doc_ids": ["doc1", "doc2"]}
        job_id = create_job(payload, db_path=temp_db)

        assert job_id is not None

        job = get_job(job_id, db_path=temp_db)
        assert job is not None
        assert job["status"] == JobStatus.PENDING.value
        assert json.loads(job["payload"]) == payload

    def test_claim_job_transitions_to_processing(self, temp_db):
        """Verify claiming a job changes its status to PROCESSING."""
        create_job({"test": "data"}, db_path=temp_db)

        job = claim_job(db_path=temp_db)
        assert job is not None
        assert job["status"] == JobStatus.PROCESSING.value
        assert job["attempts"] == 1

    def test_claim_job_returns_none_when_empty(self, temp_db):
        """Verify claim_job returns None when queue is empty."""
        job = claim_job(db_path=temp_db)
        assert job is None

    def test_complete_job_stores_result(self, temp_db):
        """Verify completing a job stores the result and updates status."""
        create_job({"test": "data"}, db_path=temp_db)
        job = claim_job(db_path=temp_db)

        result = {"score": 0.95}
        success = complete_job(job["id"], result, db_path=temp_db)

        assert success is True

        updated_job = get_job(job["id"], db_path=temp_db)
        assert updated_job["status"] == JobStatus.COMPLETED.value
        assert json.loads(updated_job["result"]) == result

    def test_fail_job_retries_if_under_limit(self, temp_db):
        """Verify a failed job returns to PENDING if attempts < max_attempts."""
        create_job({"test": "data"}, max_attempts=3, db_path=temp_db)
        job = claim_job(db_path=temp_db)

        fail_job(job["id"], "Simulated error", db_path=temp_db)

        updated_job = get_job(job["id"], db_path=temp_db)
        assert updated_job["status"] == JobStatus.PENDING.value
        assert updated_job["error_message"] == "Simulated error"

    def test_fail_job_permanently_fails_at_limit(self, temp_db):
        """Verify a job is marked FAILED after reaching max_attempts."""
        # Create job with max_attempts=1
        create_job({"test": "data"}, max_attempts=1, db_path=temp_db)
        job = claim_job(db_path=temp_db)

        fail_job(job["id"], "Fatal error", db_path=temp_db)

        updated_job = get_job(job["id"], db_path=temp_db)
        assert updated_job["status"] == JobStatus.FAILED.value


class TestTaskQueueClient:
    """Test suite for the high-level TaskQueue client."""

    def test_submit_and_poll(self, temp_db):
        """Verify the client can submit and poll a job."""
        queue = TaskQueue(db_path=str(temp_db))

        job_id = queue.submit_batch_scan(document_ids=["doc1"], user_id="user1")

        status = queue.get_job_status(job_id)
        assert status is not None
        assert status["status"] == JobStatus.PENDING.value
        assert status["payload"]["document_ids"] == ["doc1"]
