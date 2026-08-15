"""Rate Limiter for API Gateway."""

from __future__ import annotations

import time
from collections import defaultdict

from src.utils.redis_cache import get_cache


class RateLimiter:
    """Rate limiter supporting Redis or in-memory fallback."""

    def __init__(self, default_limit: int = 100, window_seconds: int = 60) -> None:
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        # In-memory sliding window timestamps: key -> list of float timestamps
        self._memory_buckets: dict[str, list[float]] = defaultdict(list)

    def allow(
        self,
        key: str,
        limit: int | None = None,
        window_seconds: int | None = None,
    ) -> bool:
        """Check if request for key is allowed under rate limit.

        Args:
            key: Unique key identifier (e.g. API key hash, IP address, user_id)
            limit: Maximum requests allowed in window (defaults to self.default_limit)
            window_seconds: Time window in seconds (defaults to self.window_seconds)

        Returns:
            True if request is allowed, False if limit exceeded.
        """
        max_requests = limit if limit is not None else self.default_limit
        window = window_seconds if window_seconds is not None else self.window_seconds

        # Try Redis first if available
        cache = get_cache()
        if cache.is_available():
            try:
                redis_key = f"rate_limit:{key}"
                current_count = cache.incr(redis_key)
                if current_count == 1:
                    cache.expire(redis_key, window)
                return current_count <= max_requests
            except Exception:
                pass  # Fallback to in-memory implementation on Redis failure

        # In-memory sliding window fallback
        now = time.time()
        cutoff = now - window
        timestamps = self._memory_buckets[key]

        # Evict old timestamps outside current window
        valid_timestamps = [t for t in timestamps if t > cutoff]
        self._memory_buckets[key] = valid_timestamps

        if len(valid_timestamps) >= max_requests:
            return False

        valid_timestamps.append(now)
        return True

    def reset(self, key: str | None = None) -> None:
        """Reset rate limiter state for a key or all keys."""
        if key is None:
            self._memory_buckets.clear()
        else:
            self._memory_buckets.pop(key, None)
