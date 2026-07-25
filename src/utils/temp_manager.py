"""
src/utils/temp_manager.py
--------------------------
Utility module to manage temporary files safely.
"""

import os
import tempfile
from contextlib import contextmanager


@contextmanager
def create_managed_temp_file(suffix: str = "", delete: bool = True):
    """Context manager for creating and automatically cleaning up temporary files."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        yield path
    finally:
        if delete and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass