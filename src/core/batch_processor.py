"""
Batch Processing Engine for Semantic Plagiarism Detection.

Provides asynchronous batch processing capabilities for large-scale
plagiarism detection across multiple document collections.
"""

import os
import json
import time
import uuid
import logging
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Callable
from enum import Enum
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class BatchStatus(Enum):
    """Status of a batch processing job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class BatchPriority(Enum):
    """Priority levels for batch jobs."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class BatchJob:
    """Represents a single batch processing job."""
    job_id: str
    name: str
    document_paths: List[str]
    status: BatchStatus = BatchStatus.PENDING
    priority: BatchPriority = BatchPriority.NORMAL
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: float = 0.0
    total_documents: int = 0
    processed_documents: int = 0
    flagged_pairs: int = 0
    high_severity_count: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary."""
        data = asdict(self)
        data['status'] = self.status.value
        data['priority'] = self.priority.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchJob':
        """Create job from dictionary."""
        data['status'] = BatchStatus(data.get('status', 'pending'))
        data['priority'] = BatchPriority(data.get('priority', 'normal'))
        return cls(**data)

    def update_progress(self, processed: int, flagged: int = 0, high: int = 0):
        """Update job progress."""
        self.processed_documents = processed
        self.flagged_pairs += flagged
        self.high_severity_count += high
        if self.total_documents > 0:
            self.progress = (processed / self.total_documents) * 100.0


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    max_workers: int = 4
    chunk_size: int = 100
    similarity_threshold: float = 0.59
    faiss_top_k: int = 5
    enable_webhook: bool = True
    webhook_threshold: float = 0.90
    output_directory: str = "batch_results"
    enable_caching: bool = True
    cache_ttl: int = 3600
    max_retries: int = 3
    timeout_seconds: int = 300

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchConfig':
        """Create config from dictionary."""
        return cls(**data)


class BatchProcessor:
    """
    Main batch processing engine for plagiarism detection.

    Handles large-scale document processing with parallel execution,
    progress tracking, and result aggregation.
    """

    def __init__(self, config: Optional[BatchConfig] = None):
        """
        Initialize batch processor.

        Args:
            config: Batch processing configuration
        """
        self.config = config or BatchConfig()
        self.jobs: Dict[str, BatchJob] = {}
        self._executor: Optional[ThreadPoolExecutor] = None
        self._callbacks: List[Callable] = []
        self._results_cache: Dict[str, Any] = {}
        logger.info(f"BatchProcessor initialized with {self.config.max_workers} workers")

    def register_callback(self, callback: Callable[[str, BatchJob], None]):
        """Register a callback for job status updates."""
        self._callbacks.append(callback)

    def _notify_callbacks(self, event: str, job: BatchJob):
        """Notify all registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(event, job)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def create_job(
        self,
        name: str,
        document_paths: List[str],
        priority: BatchPriority = BatchPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> BatchJob:
        """
        Create a new batch processing job.

        Args:
            name: Human-readable job name
            document_paths: List of paths to documents to process
            priority: Job priority level
            metadata: Optional metadata dictionary

        Returns:
            Created BatchJob instance
        """
        job_id = str(uuid.uuid4())[:12]
        job = BatchJob(
            job_id=job_id,
            name=name,
            document_paths=document_paths,
            priority=priority,
            total_documents=len(document_paths),
            metadata=metadata or {}
        )
        self.jobs[job_id] = job
        logger.info(f"Created batch job {job_id}: {name} ({len(document_paths)} docs)")
        self._notify_callbacks("created", job)
        return job

    def get_job(self, job_id: str) -> Optional[BatchJob]:
        """Retrieve a batch job by ID."""
        return self.jobs.get(job_id)

    def list_jobs(
        self,
        status: Optional[BatchStatus] = None,
        priority: Optional[BatchPriority] = None
    ) -> List[BatchJob]:
        """List jobs with optional filtering."""
        jobs = list(self.jobs.values())
        if status:
            jobs = [j for j in jobs if j.status == status]
        if priority:
            jobs = [j for j in jobs if j.priority == priority]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or processing job."""
        job = self.jobs.get(job_id)
        if not job:
            return False
        if job.status in (BatchStatus.COMPLETED, BatchStatus.CANCELLED):
            return False
        job.status = BatchStatus.CANCELLED
        job.completed_at = datetime.now().isoformat()
        self._notify_callbacks("cancelled", job)
        logger.info(f"Cancelled batch job {job_id}")
        return True

    def pause_job(self, job_id: str) -> bool:
        """Pause a processing job."""
        job = self.jobs.get(job_id)
        if not job or job.status != BatchStatus.PROCESSING:
            return False
        job.status = BatchStatus.PAUSED
        self._notify_callbacks("paused", job)
        return True

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        job = self.jobs.get(job_id)
        if not job or job.status != BatchStatus.PAUSED:
            return False
        job.status = BatchStatus.PROCESSING
        self._notify_callbacks("resumed", job)
        return True

    def process_job(self, job_id: str, processing_fn: Optional[Callable] = None) -> bool:
        """
        Process a batch job.

        Args:
            job_id: Job ID to process
            processing_fn: Custom processing function(doc_path) -> results

        Returns:
            True if processing started successfully
        """
        job = self.jobs.get(job_id)
        if not job or job.status not in (BatchStatus.PENDING, BatchStatus.PAUSED):
            return False

        job.status = BatchStatus.PROCESSING
        job.started_at = datetime.now().isoformat()
        self._notify_callbacks("started", job)

        try:
            self._process_documents(job, processing_fn)
            job.status = BatchStatus.COMPLETED
            job.progress = 100.0
            job.completed_at = datetime.now().isoformat()
            self._notify_callbacks("completed", job)
            logger.info(f"Completed batch job {job_id}")
            return True
        except Exception as e:
            job.status = BatchStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now().isoformat()
            self._notify_callbacks("failed", job)
            logger.error(f"Failed batch job {job_id}: {e}")
            return False

    def _process_documents(self, job: BatchJob, processing_fn: Optional[Callable] = None):
        """Process documents in a job with parallel execution."""
        if processing_fn is None:
            processing_fn = self._default_processing

        results = {}
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            future_to_path = {
                executor.submit(processing_fn, path): path
                for path in job.document_paths
            }
            for i, future in enumerate(as_completed(future_to_path)):
                path = future_to_path[future]
                try:
                    result = future.result(timeout=self.config.timeout_seconds)
                    results[path] = result
                    job.update_progress(i + 1)
                    self._notify_callbacks("progress", job)
                except Exception as e:
                    results[path] = {"error": str(e)}
                    logger.error(f"Error processing {path}: {e}")

        job.results = results

    def _default_processing(self, doc_path: str) -> Dict[str, Any]:
        """Default document processing function."""
        return {
            "path": doc_path,
            "status": "processed",
            "timestamp": datetime.now().isoformat(),
            "size": os.path.getsize(doc_path) if os.path.exists(doc_path) else 0
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall batch processing statistics."""
        jobs = list(self.jobs.values())
        return {
            "total_jobs": len(jobs),
            "pending": len([j for j in jobs if j.status == BatchStatus.PENDING]),
            "processing": len([j for j in jobs if j.status == BatchStatus.PROCESSING]),
            "completed": len([j for j in jobs if j.status == BatchStatus.COMPLETED]),
            "failed": len([j for j in jobs if j.status == BatchStatus.FAILED]),
            "total_documents": sum(j.total_documents for j in jobs),
            "total_flagged": sum(j.flagged_pairs for j in jobs),
            "avg_progress": sum(j.progress for j in jobs) / len(jobs) if jobs else 0,
        }

    def export_results(self, job_id: str, output_path: str) -> bool:
        """Export job results to JSON file."""
        job = self.jobs.get(job_id)
        if not job:
            return False
        output = {
            "job": job.to_dict(),
            "exported_at": datetime.now().isoformat(),
            "config": self.config.to_dict()
        }
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2, default=str)
        logger.info(f"Exported results to {output_path}")
        return True

    def clear_completed(self) -> int:
        """Remove completed and failed jobs. Returns count removed."""
        to_remove = [
            jid for jid, job in self.jobs.items()
            if job.status in (BatchStatus.COMPLETED, BatchStatus.FAILED, BatchStatus.CANCELLED)
        ]
        for jid in to_remove:
            del self.jobs[jid]
        logger.info(f"Cleared {len(to_remove)} jobs")
        return len(to_remove)
