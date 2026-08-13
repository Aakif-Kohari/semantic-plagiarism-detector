"""
Batch Processing Optimization for Large Document Sets.

Provides parallel processing, incremental indexing, and progress tracking
for handling 100+ documents efficiently.
"""

import os
import time
import logging
import threading
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed  # noqa: F401
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np
import pandas as pd  # noqa: F401
from datetime import datetime
import psutil

logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class BatchJob:
    """Represents a batch processing job."""
    
    job_id: str
    file_paths: List[str]
    status: str = "pending"  # pending, processing, completed, failed
    progress: float = 0.0
    results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[Dict[str, str]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    total_files: int = 0
    processed_files: int = 0
    
    def __post_init__(self):
        self.total_files = len(self.file_paths)
    
    def get_duration(self) -> Optional[float]:
        """Get job duration in seconds."""
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        return None
    
    def get_progress_percentage(self) -> float:
        """Get progress as percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    
    batch_size: int = 10
    max_workers: int = 4
    use_parallel: bool = True
    chunk_size: int = 500
    chunk_overlap: int = 50
    ocr_language: str = "eng"
    ocr_dpi: int = 250
    threshold: float = 0.59
    use_hybrid_scoring: bool = False
    cross_lingual_mode: bool = False
    save_progress: bool = True
    progress_file: str = ".cache/batch_progress.json"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "batch_size": self.batch_size,
            "max_workers": self.max_workers,
            "use_parallel": self.use_parallel,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "ocr_language": self.ocr_language,
            "ocr_dpi": self.ocr_dpi,
            "threshold": self.threshold,
            "use_hybrid_scoring": self.use_hybrid_scoring,
            "cross_lingual_mode": self.cross_lingual_mode,
            "save_progress": self.save_progress,
        }


# ============================================================================
# BATCH PROCESSOR
# ============================================================================

class BatchProcessor:
    """Main batch processor with parallelization and progress tracking."""
    
    def __init__(self, config: Optional[BatchConfig] = None):
        self.config = config or BatchConfig()
        self._jobs: Dict[str, BatchJob] = {}
        self._active_job: Optional[str] = None
        self._lock = threading.RLock()
        self._progress_callbacks: List[Callable] = []
        self._stop_processing = False
        
        # Performance metrics
        self.metrics = {
            "total_documents": 0,
            "total_time": 0.0,
            "avg_time_per_doc": 0.0,
            "successful": 0,
            "failed": 0,
            "peak_memory_mb": 0
        }
        
        # Create cache directory
        Path(".cache").mkdir(parents=True, exist_ok=True)
    
    def register_progress_callback(self, callback: Callable) -> None:
        """Register a callback for progress updates."""
        self._progress_callbacks.append(callback)
    
    def _notify_progress(self, job_id: str, progress: float, message: str = "") -> None:
        """Notify all registered callbacks of progress update."""
        for callback in self._progress_callbacks:
            try:
                callback(job_id, progress, message)
            except Exception as e:
                logger.error(f"Progress callback failed: {e}")
    
    def _process_single_document(
        self,
        file_path: str,
        file_bytes: bytes,
        config: BatchConfig
    ) -> Dict[str, Any]:
        """
        Process a single document.
        
        Returns:
            Dict with processing results
        """
        start_time = time.time()
        result = {
            "file_path": file_path,
            "status": "success",
            "error": None,
            "processing_time": 0.0,
            "chunks": [],
            "embedding": None,
            "word_count": 0
        }
        
        try:
            # Import here to avoid circular imports
            from src.core.document_parser import extract_text
            from src.core.text_chunking import chunk_documents
            from src.core.embedding_model import embed_chunks
            from src.core.document_parser import prepare_text_for_embedding
            
            # Extract text
            extracted_text = extract_text(
                file_bytes,
                filename=file_path,
                language=config.ocr_language,
                dpi=config.ocr_dpi
            )
            
            if not extracted_text:
                result["status"] = "failed"
                result["error"] = "No text extracted"
                return result
            
            # Prepare text
            prepared = prepare_text_for_embedding(extracted_text)
            
            # Chunk documents
            chunks = chunk_documents(
                [prepared],
                chunk_size=config.chunk_size,
                chunk_overlap=config.chunk_overlap
            )
            
            if not chunks:
                result["status"] = "failed"
                result["error"] = "No chunks generated"
                return result
            
            # Generate embeddings
            embeddings = embed_chunks(chunks)
            
            result["chunks"] = chunks
            result["embedding"] = embeddings.tolist() if isinstance(embeddings, np.ndarray) else embeddings
            result["word_count"] = len(extracted_text.split())
            result["chunk_count"] = len(chunks)
            
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            logger.error(f"Failed to process {file_path}: {e}")
        
        result["processing_time"] = time.time() - start_time
        return result
    
    def _process_batch(
        self,
        batch_files: List[Tuple[str, bytes]],
        batch_index: int
    ) -> List[Dict[str, Any]]:
        """
        Process a batch of documents in parallel.
        
        Args:
            batch_files: List of (file_path, file_bytes) tuples
            batch_index: Index of this batch
            
        Returns:
            List of processing results
        """
        results = []
        
        # Determine if we should use parallel processing
        if self.config.use_parallel and len(batch_files) > 1:
            # Use ThreadPoolExecutor for I/O bound operations
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                futures = []
                for file_path, file_bytes in batch_files:
                    future = executor.submit(
                        self._process_single_document,
                        file_path,
                        file_bytes,
                        self.config
                    )
                    futures.append((file_path, future))
                
                for file_path, future in futures:
                    try:
                        result = future.result(timeout=300)  # 5 min timeout
                        results.append(result)
                    except Exception as e:
                        results.append({
                            "file_path": file_path,
                            "status": "failed",
                            "error": str(e),
                            "processing_time": 0.0
                        })
        else:
            # Sequential processing
            for file_path, file_bytes in batch_files:
                result = self._process_single_document(
                    file_path,
                    file_bytes,
                    self.config
                )
                results.append(result)
        
        return results
    
    def process_documents(
        self,
        file_bytes_dict: Dict[str, bytes],
        job_id: Optional[str] = None
    ) -> BatchJob:
        """
        Process a batch of documents.
        
        Args:
            file_bytes_dict: Dict mapping file paths to bytes
            job_id: Optional job ID
            
        Returns:
            BatchJob with results
        """
        if not file_bytes_dict:
            raise ValueError("No documents to process")
        
        # Create job
        if job_id is None:
            job_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        files = list(file_bytes_dict.keys())
        job = BatchJob(
            job_id=job_id,
            file_paths=files,
            total_files=len(files)
        )
        
        with self._lock:
            self._jobs[job_id] = job
            self._active_job = job_id
        
        # Split into batches
        batch_size = self.config.batch_size
        file_items = list(file_bytes_dict.items())
        batches = [
            file_items[i:i + batch_size]
            for i in range(0, len(file_items), batch_size)
        ]
        
        logger.info(f"Processing {len(file_items)} files in {len(batches)} batches")
        
        start_time = time.time()
        job.started_at = start_time
        
        # Process each batch
        for batch_index, batch in enumerate(batches):
            if self._stop_processing:
                logger.warning(f"Processing stopped for job {job_id}")
                break
            
            # Update status
            job.status = "processing"
            job.progress = (batch_index / len(batches)) * 100
            
            self._notify_progress(
                job_id,
                job.progress,
                f"Processing batch {batch_index + 1}/{len(batches)}"
            )
            
            # Process batch
            batch_results = self._process_batch(batch, batch_index)
            
            # Update job with results
            with self._lock:
                for result in batch_results:
                    if result["status"] == "success":
                        job.results.append(result)
                        job.processed_files += 1
                    else:
                        job.errors.append({
                            "file": result["file_path"],
                            "error": result.get("error", "Unknown error")
                        })
            
            # Update metrics
            self.metrics["successful"] = len(job.results)
            self.metrics["failed"] = len(job.errors)
            
            # Check memory usage
            try:
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / (1024 * 1024)
                if memory_mb > self.metrics["peak_memory_mb"]:
                    self.metrics["peak_memory_mb"] = memory_mb
            except Exception:
                pass
        
        # Complete job
        job.completed_at = time.time()
        job.status = "completed"
        job.progress = 100.0
        
        # Update metrics
        self.metrics["total_documents"] += job.total_files
        self.metrics["total_time"] += job.get_duration() or 0
        if job.processed_files > 0:
            self.metrics["avg_time_per_doc"] = (
                self.metrics["total_time"] / self.metrics["total_documents"]
            )
        
        self._notify_progress(job_id, 100.0, "Processing complete")
        
        # Save progress
        if self.config.save_progress:
            self._save_progress(job)
        
        return job
    
    def _save_progress(self, job: BatchJob) -> None:
        """Save job progress to file."""
        try:
            import json
            data = {
                "job_id": job.job_id,
                "status": job.status,
                "processed_files": job.processed_files,
                "total_files": job.total_files,
                "errors": job.errors,
                "results_count": len(job.results),
                "created_at": job.created_at,
                "started_at": job.started_at,
                "completed_at": job.completed_at
            }
            with open(self.config.progress_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")
    
    def get_job(self, job_id: str) -> Optional[BatchJob]:
        """Get a job by ID."""
        with self._lock:
            return self._jobs.get(job_id)
    
    def get_active_job(self) -> Optional[BatchJob]:
        """Get the currently active job."""
        with self._lock:
            if self._active_job:
                return self._jobs.get(self._active_job)
            return None
    
    def stop_processing(self) -> None:
        """Stop ongoing processing."""
        self._stop_processing = True
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get processing metrics."""
        return {
            **self.metrics,
            "active_job": self._active_job,
            "total_jobs": len(self._jobs),
            "config": self.config.to_dict()
        }
    
    def get_recommended_batch_size(self) -> int:
        """Get recommended batch size based on system resources."""
        try:
            cpu_count = multiprocessing.cpu_count()
            memory = psutil.virtual_memory()
            available_mb = memory.available / (1024 * 1024)
            
            # Estimate based on available resources
            if available_mb > 4096 and cpu_count > 4:
                return 20
            elif available_mb > 2048 and cpu_count > 2:
                return 10
            else:
                return 5
        except Exception:
            return 10


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_processor: Optional[BatchProcessor] = None
_processor_lock = threading.Lock()


def get_batch_processor() -> BatchProcessor:
    """Get global batch processor instance."""
    global _processor
    with _processor_lock:
        if _processor is None:
            _processor = BatchProcessor()
        return _processor