from __future__ import annotations

import time
from contextlib import contextmanager

class ProcessingTimer:
    def __init__(self):
        self.durations = []
        self._active_timers = 0

    @contextmanager
    def time_block(self):
        start = time.perf_counter()
        self._active_timers += 1
        try:
            yield self
        finally:
            end = time.perf_counter()
            self._active_timers -= 1
            self.durations.append(end - start)
