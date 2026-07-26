"""
redis_cache.py
--------------
Redis connection and caching utilities for session state and FAISS results.
Supports scaling across multiple server nodes in Docker/Kubernetes environments.
"""

import json
import os
import pickle
from typing import Any, Optional

try:
    import redis
except ImportError:
    redis = None
import logging

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

RedisError = getattr(redis, "RedisError", Exception)
RedisConnectionError = getattr(redis, "ConnectionError", ConnectionError)
RedisTimeoutError = getattr(redis, "TimeoutError", TimeoutError)


# Redis connection configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_URL = os.getenv("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")

# TTL settings (in seconds)
SESSION_TTL = 15 * 60  # 15 minutes for session state
FAISS_INDEX_TTL = 24 * 60 * 60  # 24 hours for FAISS index cache
ANALYSIS_RESULTS_TTL = 2 * 60 * 60  # 2 hours for analysis results
LOGIN_LOCKOUT_TTL = 15 * 60  # 15 minutes for login lockout
UPLOAD_RATE_TTL = 60 * 60  # 1 hour for upload rate limiting


class RedisCache:
    """Redis cache manager for session state and computational results."""

    _instance: Optional["RedisCache"] = None
    _client: Optional[Any] = None

    def __new__(cls) -> "RedisCache":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._fallback_cache = {}
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_fallback_cache") or self._fallback_cache is None:
            self._fallback_cache = {}
        if self._client is None:
            self._connect()

    @property
    def fallback_cache(self) -> dict:
        """Lazily initialize fallback cache dictionary if not present."""
        if not hasattr(self, "_fallback_cache") or self._fallback_cache is None:
            self._fallback_cache = {}
        return self._fallback_cache

    def _fallback_set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        import time
        expire_at = time.time() + ttl if ttl is not None else None
        self.fallback_cache[key] = (value, expire_at)
        return True

    def _fallback_get(self, key: str) -> Optional[Any]:
        import time
        if key not in self.fallback_cache:
            return None
        value, expire_at = self.fallback_cache[key]
        if expire_at is not None and time.time() > expire_at:
            del self.fallback_cache[key]
            return None
        return value

    def _fallback_delete(self, key: str) -> bool:
        if key in self.fallback_cache:
            del self.fallback_cache[key]
            return True
        return False

    def _fallback_exists(self, key: str) -> bool:
        return self._fallback_get(key) is not None

    def _fallback_set_json(self, key: str, value: dict, ttl: Optional[int] = None) -> bool:
        import json
        serialized = json.dumps(value)
        return self._fallback_set(key, json.loads(serialized), ttl)

    def _fallback_get_json(self, key: str) -> Optional[dict]:
        val = self._fallback_get(key)
        if isinstance(val, dict):
            return val
        return None

    def _fallback_clear_pattern(self, pattern: str) -> int:
        import fnmatch
        keys_to_delete = []
        for key in list(self.fallback_cache.keys()):
            if fnmatch.fnmatch(key, pattern):
                keys_to_delete.append(key)
        count = 0
        for key in keys_to_delete:
            if key in self.fallback_cache:
                del self.fallback_cache[key]
                count += 1
        return count

    def _connect(self) -> None:
        """Establish Redis connection with fallback to in-memory if unavailable."""
        if redis is None:
            self._client = None
            return

        try:
            if REDIS_URL:
                self._client = redis.from_url(
                    REDIS_URL,
                    password=REDIS_PASSWORD,
                    decode_responses=False,
                    socket_connect_timeout=5,
                )
            else:
                self._client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    db=REDIS_DB,
                    password=REDIS_PASSWORD,
                    decode_responses=False,
                    socket_connect_timeout=5,
                )
            # Test connection
            self._client.ping()
            print(f"[RedisCache] Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        except (
            RedisConnectionError,
            RedisTimeoutError,
            ConnectionRefusedError,
        ) as e:
            print(f"[RedisCache] Redis connection failed: {e}. Running without cache.")
            logger.warning(
                f"[RedisCache] Redis connection failed: {e}. Running without cache."
            )
            self._client = None

    def is_available(self) -> bool:
        """Check if Redis is available."""
        if self._client is None:
            return False
        try:
            self._client.ping()
            return True
        except Exception:
            return False

    def ping(self) -> tuple[bool, float | None]:
        """Ping Redis and measure round-trip latency.

        Returns:
            Tuple of (connected: bool, latency_ms: float | None).
            latency_ms is None if the connection is unavailable.
        """
        if self._client is None:
            return False, None
        try:
            import time

            start = time.monotonic()
            self._client.ping()
            elapsed = (time.monotonic() - start) * 1000
            return True, round(elapsed, 1)
        except Exception:
            return False, None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store a value in Redis with optional TTL. Falls back to in-memory on failure."""
        if self.is_available():
            try:
                serialized = pickle.dumps(value)
                if ttl:
                    self._client.setex(key, ttl, serialized)
                else:
                    self._client.set(key, serialized)
                return True
            except (
                RedisError,
                RedisConnectionError,
                RedisTimeoutError,
                ConnectionRefusedError,
                ConnectionResetError,
                pickle.PickleError,
            ) as e:
                print(f"[RedisCache] Error setting key {key}: {e}. Falling back to in-memory.")
                logger.error(f"[RedisCache] Error setting key {key}: {e}. Falling back to in-memory.")

        return self._fallback_set(key, value, ttl)

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from Redis. Falls back to in-memory on failure."""
        if self.is_available():
            try:
                data = self._client.get(key)
                if data is not None:
                    return pickle.loads(data)
            except (
                RedisError,
                RedisConnectionError,
                RedisTimeoutError,
                ConnectionRefusedError,
                ConnectionResetError,
                pickle.PickleError,
            ) as e:
                print(f"[RedisCache] Error getting key {key}: {e}. Falling back to in-memory.")
                logger.error(f"[RedisCache] Error getting key {key}: {e}. Falling back to in-memory.")

        return self._fallback_get(key)

    def delete(self, key: str) -> bool:
        """Delete a key from Redis. Falls back to in-memory on failure."""
        redis_deleted = False
        if self.is_available():
            try:
                redis_deleted = bool(self._client.delete(key))
            except (
                RedisError,
                RedisConnectionError,
                RedisTimeoutError,
                ConnectionRefusedError,
                ConnectionResetError,
            ) as e:
                print(f"[RedisCache] Error deleting key {key}: {e}. Falling back to in-memory.")
                logger.error(f"[RedisCache] Error deleting key {key}: {e}. Falling back to in-memory.")

        fallback_deleted = self._fallback_delete(key)
        return redis_deleted or fallback_deleted

    def set_json(self, key: str, value: dict, ttl: Optional[int] = None) -> bool:
        """Store a JSON-serializable dict in Redis. Falls back to in-memory on failure."""
        if self.is_available():
            try:
                serialized = json.dumps(value)
                if ttl:
                    self._client.setex(key, ttl, serialized)
                else:
                    self._client.set(key, serialized)
                return True
            except (
                RedisError,
                RedisConnectionError,
                RedisTimeoutError,
                ConnectionRefusedError,
                ConnectionResetError,
                json.JSONDecodeError,
                TypeError,
            ) as e:
                print(f"[RedisCache] Error setting JSON key {key}: {e}. Falling back to in-memory.")
                logger.error(f"[RedisCache] Error setting JSON key {key}: {e}. Falling back to in-memory.")

        return self._fallback_set_json(key, value, ttl)

    def get_json(self, key: str) -> Optional[dict]:
        """Retrieve a JSON value from Redis. Falls back to in-memory on failure."""
        if self.is_available():
            try:
                data = self._client.get(key)
                if data is not None:
                    return json.loads(data)
            except (
                RedisError,
                RedisConnectionError,
                RedisTimeoutError,
                ConnectionRefusedError,
                ConnectionResetError,
                json.JSONDecodeError,
            ) as e:
                print(f"[RedisCache] Error getting JSON key {key}: {e}. Falling back to in-memory.")
                logger.error(f"[RedisCache] Error getting JSON key {key}: {e}. Falling back to in-memory.")

        return self._fallback_get_json(key)

    def exists(self, key: str) -> bool:
        """Check if a key exists in Redis. Falls back to in-memory on failure."""
        if self.is_available():
            try:
                if bool(self._client.exists(key)):
                    return True
            except (
                RedisError,
                RedisConnectionError,
                RedisTimeoutError,
                ConnectionRefusedError,
                ConnectionResetError,
            ) as e:
                print(f"[RedisCache] Error checking key {key}: {e}. Falling back to in-memory.")
                logger.error(f"[RedisCache] Error checking key {key}: {e}. Falling back to in-memory.")

        return self._fallback_exists(key)

    def clear_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern. Falls back to in-memory on failure."""
        redis_count = 0
        if self.is_available():
            try:
                keys = self._client.keys(pattern)
                if keys:
                    redis_count = self._client.delete(*keys)
            except (
                RedisError,
                RedisConnectionError,
                RedisTimeoutError,
                ConnectionRefusedError,
                ConnectionResetError,
            ) as e:
                print(f"[RedisCache] Error clearing pattern {pattern}: {e}. Falling back to in-memory.")
                logger.error(f"[RedisCache] Error clearing pattern {pattern}: {e}. Falling back to in-memory.")

        fallback_count = self._fallback_clear_pattern(pattern)
        return redis_count + fallback_count



# Global cache instance
_cache = RedisCache()


def get_cache() -> RedisCache:
    """Get the global Redis cache instance."""
    return _cache


def cache_session_state(session_id: str, key: str, value: Any) -> bool:
    """Cache session state data with TTL."""
    cache_key = f"session:{session_id}:{key}"
    return _cache.set(cache_key, value, SESSION_TTL)


def get_session_state(session_id: str, key: str) -> Optional[Any]:
    """Retrieve session state data from cache."""
    cache_key = f"session:{session_id}:{key}"
    return _cache.get(cache_key)


def clear_session(session_id: str) -> bool:
    """Clear all session data for a given session ID."""
    pattern = f"session:{session_id}:*"
    return _cache.clear_pattern(pattern) > 0


def cache_faiss_index(index_key: str, index_data: bytes) -> bool:
    """Cache FAISS index binary data."""
    cache_key = f"faiss:index:{index_key}"
    return _cache.set(cache_key, index_data, FAISS_INDEX_TTL)


def get_faiss_index(index_key: str) -> Optional[bytes]:
    """Retrieve FAISS index binary data from cache."""
    cache_key = f"faiss:index:{index_key}"
    return _cache.get(cache_key)


def cache_analysis_results(analysis_key: str, results: dict) -> bool:
    """Cache analysis results (embeddings, similarity matrices, etc.)."""
    cache_key = f"analysis:{analysis_key}"
    return _cache.set(cache_key, results, ANALYSIS_RESULTS_TTL)


def get_analysis_results(analysis_key: str) -> Optional[dict]:
    """Retrieve analysis results from cache."""
    cache_key = f"analysis:{analysis_key}"
    return _cache.get(cache_key)


def increment_login_attempts(identifier: str) -> int:
    """Increment failed login attempt counter for a username/IP."""
    cache_key = f"login_attempts:{identifier}"
    current = _cache.get(cache_key)
    if current is None:
        current = 0
    current += 1
    _cache.set(cache_key, current, LOGIN_LOCKOUT_TTL)
    return current


def get_login_attempts(identifier: str) -> int:
    """Get current failed login attempt count for a username/IP."""
    cache_key = f"login_attempts:{identifier}"
    current = _cache.get(cache_key)
    return current if current is not None else 0


def is_login_locked_out(identifier: str) -> bool:
    """Check if a username/IP is locked out due to too many failed attempts."""
    return get_login_attempts(identifier) >= 5


def clear_login_attempts(identifier: str) -> bool:
    """Clear failed login attempt counter after successful login."""
    cache_key = f"login_attempts:{identifier}"
    return _cache.delete(cache_key)


def increment_upload_count(username: str) -> int:
    """Increment upload counter for a user per hour."""
    cache_key = f"uploads:{username}"
    current = _cache.get(cache_key)
    if current is None:
        current = 0
    current += 1
    _cache.set(cache_key, current, UPLOAD_RATE_TTL)
    return current


def get_upload_count(username: str) -> int:
    """Get current upload count for a user in the current hour window."""
    cache_key = f"uploads:{username}"
    current = _cache.get(cache_key)
    return current if current is not None else 0


def is_upload_rate_limited(username: str) -> bool:
    """Check if a user has exceeded the upload rate limit (100 uploads/hour)."""
    return get_upload_count(username) >= 100
