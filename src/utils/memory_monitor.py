"""Memory monitoring utility for detecting leaks."""

import psutil
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def get_memory_usage() -> Dict[str, Any]:
    """Get current memory usage of the process."""
    try:
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        
        return {
            "rss_mb": mem_info.rss / (1024 * 1024),
            "vms_mb": mem_info.vms / (1024 * 1024),
            "percent": process.memory_percent(),
            "cpu_percent": process.cpu_percent(interval=0.1)
        }
    except Exception as e:
        logger.error(f"Failed to get memory usage: {e}")
        return {
            "rss_mb": 0,
            "vms_mb": 0,
            "percent": 0,
            "cpu_percent": 0
        }


def log_memory_usage(tag: str = "") -> None:
    """Log current memory usage with a tag."""
    usage = get_memory_usage()
    logger.info(f"[Memory] {tag} - RSS: {usage['rss_mb']:.1f}MB, "
                f"VMS: {usage['vms_mb']:.1f}MB, "
                f"Process: {usage['percent']:.1f}%")
    return usage