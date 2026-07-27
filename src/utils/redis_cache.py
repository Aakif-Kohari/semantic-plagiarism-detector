"""
redis_cache.py
--------------
Redis connection and caching utilities for session state and FAISS results.
Supports scaling across multiple server nodes in Docker/Kubernetes environments.
"""

import json
import os
import pickle
from enum import Enum
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
REDIS_TIMEOUT_SECONDS = float(os.getenv("REDIS_TIMEOUT_SECONDS", "2.0"))

# TTL settings (in seconds)
SESSION_TTL = 15 * 60  # 15 minutes for session state
FAISS_INDEX_TTL = 24 * 60 * 60  # 24 hours for FAISS index cache
ANALYSIS_RESULTS_TTL = 2 * 60 * 60  # 2 hours for analysis results
LOGIN_LOCKOUT_TTL = 15 * 60  # 15 minutes for login lockout
UPLOAD_RATE_TTL = 60 * 60  # 1 hour for upload rate limiting
DEFAULT_TTL = 24 * 60 * 60  # 24 hours fallback for keys without explicit TTL


class CacheKeyPrefix(str, Enum):
    SESSION = "spd:v1:session"
    FAISS = "spd:v1:faiss"
    ANALYSIS = "analysis"
    LOGIN_ATTEMPTS = "spd:v1:login_attempts"
    UPLOADS = "spd:v1:uploads"

    # Inline/Legacy keys and prefixes used in deletion/clearing operations
    LEGACY_FAISS_INDEX = "faiss:index:corpus_index"
    LEGACY_ANALYSIS_PATTERN = "analysis:*"
    LEGACY_ANALYSIS_PREFIX = "analysis:"
    LEGACY_UPLOADS_PREFIX = "uploads:"

    def build_key(self, *parts: str) -> str:
        """Construct a standardized cache key with namespace prefix."""
        return ":".join([self.value] + list(parts))


CacheNamespace = CacheKeyPrefix


class RedisCache:
    """Redis cache manager for session state and computational results."""

    _instance: Optional["RedisCache"] = None
    _client: Optional[Any] = None

    def __new__(cls) -> "RedisCache":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._fallback_cache = {}
            cls._instance._hits = 0
            cls._instance._misses = 0
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_fallback_cache") or self._fallback_cache is None:
            self._fallback_cache = {}
        if not hasattr(self, "_hits"):
            self._hits = 0
        if not hasattr(self, "_misses"):
            self._misses = 0
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
                    socket_connect_timeout=REDIS_TIMEOUT_SECONDS,
                )
            else:
                self._client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    db=REDIS_DB,
                    password=REDIS_PASSWORD,
                    decode_responses=False,
                    socket_connect_timeout=REDIS_TIMEOUT_SECONDS,
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

    def ping(self) -> tuple[bool, Optional[float]]:
        """Ping Redis and measure round-trip latency.

        Returns:
            Tuple of (connected: bool, latency_ms: Optional[float]).
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

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics including hit ratio and total items count."""
        total_requests = self._hits + self._misses
        hit_ratio = (self._hits / total_requests) if total_requests > 0 else 0.0

        total_items = 0
        if self._client is not None and self.is_available():
            try:
                total_items = self._client.dbsize()
            except Exception:
                total_items = len(self.fallback_cache)
        else:
            total_items = len(self.fallback_cache)

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": hit_ratio,
            "total_items": total_items,
        }

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store a value in Redis with optional TTL. Falls back to in-memory on failure."""
        if self._client is None:
            return False
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
        if self._client is not None and self.is_available():
            try:
                data = self._client.get(key)
                if data is not None:
                    self._hits += 1
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

        val = self._fallback_get(key)
        if val is not None:
            self._hits += 1
            return val

        self._misses += 1
        return None

    def delete(self, key: str) -> bool:
        """Delete a key from Redis. Falls back to in-memory on failure."""
        if self._client is None:
            return False
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
        if self._client is not None and self.is_available():
            try:
                data = self._client.get(key)
                if data is not None:
                    self._hits += 1
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

        val = self._fallback_get_json(key)
        if val is not None:
            self._hits += 1
            return val

        self._misses += 1
        return None

    def exists(self, key: str) -> bool:
        """Check if a key exists in Redis. Falls back to in-memory on failure."""
        if self._client is None:
            return False
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



    def close(self) -> None:
        """Explicitly close the Redis connection."""
        if self._client is not None:
            try:
                self._client.close()
                self._client = None
            except Exception as e:
                print(f"[RedisCache] Error closing Redis connection: {e}")
                logger.error(f"[RedisCache] Error closing Redis connection: {e}")


# Global cache instance
_cache = RedisCache()


def get_cache(key: Optional[str] = None):
    """Get the global Redis cache instance, or look up a key directly.

    When called with no arguments, returns the :class:`RedisCache` singleton.
    When called with a *key* string, performs a cache lookup and returns the
    stored value (or ``None`` on miss).
    """
    if key is not None:
        return _cache.get(key)
    return _cache


def set_cache(key: str, value: Any, expire: Optional[int] = None) -> bool:
    """Store *value* under *key* in the global Redis cache.

    Args:
        key:    Cache key.
        value:  Value to store (will be serialised by the cache backend).
        expire: Optional TTL in seconds. When ``None`` (default), the
                cache backend applies its own 24-hour default TTL.

    Returns:
        ``True`` on success, ``False`` on failure.
    """
    return _cache.set(key, value, ttl=expire)


def delete_cache(key: str) -> bool:
    """Delete a key from Redis.

    Safe to call even when the key does not exist or Redis is
    unavailable — returns ``False`` in those cases.
    """
    return _cache.delete(key)


def cache_session_state(session_id: str, key: str, value: Any) -> bool:
    """Cache session state data with TTL."""
    cache_key = CacheKeyPrefix.SESSION.build_key(session_id, key)
    return _cache.set(cache_key, value, SESSION_TTL)


def get_session_state(session_id: str, key: str) -> Optional[Any]:
    """Retrieve session state data from cache."""
    cache_key = CacheKeyPrefix.SESSION.build_key(session_id, key)
    return _cache.get(cache_key)


def clear_session(session_id: str) -> bool:
    """Clear all session data for a given session ID."""
    pattern = CacheKeyPrefix.SESSION.build_key(session_id, "*")
    return _cache.clear_pattern(pattern) > 0


def cache_faiss_index(index_key: str, index_data: bytes) -> bool:
    """Cache FAISS index binary data."""
    cache_key = CacheKeyPrefix.FAISS.build_key("index", index_key)
    return _cache.set(cache_key, index_data, FAISS_INDEX_TTL)


def get_faiss_index(index_key: str) -> Optional[bytes]:
    """Retrieve FAISS index binary data from cache."""
    cache_key = CacheKeyPrefix.FAISS.build_key("index", index_key)
    return _cache.get(cache_key)


def cache_analysis_results(analysis_key: str, results: dict) -> bool:
    """Cache analysis results (embeddings, similarity matrices, etc.)."""
    cache_key = CacheKeyPrefix.ANALYSIS.build_key(analysis_key)
    return _cache.set(cache_key, results, ANALYSIS_RESULTS_TTL)


def get_analysis_results(analysis_key: str) -> Optional[dict]:
    """Retrieve analysis results from cache."""
    cache_key = CacheKeyPrefix.ANALYSIS.build_key(analysis_key)
    return _cache.get(cache_key)


def increment_login_attempts(identifier: str) -> int:
    """Increment failed login attempt counter for a username/IP."""
    cache_key = CacheKeyPrefix.LOGIN_ATTEMPTS.build_key(identifier)
    current = _cache.get(cache_key)
    if current is None:
        current = 0
    current += 1
    _cache.set(cache_key, current, LOGIN_LOCKOUT_TTL)
    return current


def get_login_attempts(identifier: str) -> int:
    """Get current failed login attempt count for a username/IP."""
    cache_key = CacheKeyPrefix.LOGIN_ATTEMPTS.build_key(identifier)
    current = _cache.get(cache_key)
    return current if current is not None else 0


def is_login_locked_out(identifier: str) -> bool:
    """Check if a username/IP is locked out due to too many failed attempts."""
    return get_login_attempts(identifier) >= 5


def clear_login_attempts(identifier: str) -> bool:
    """Clear failed login attempt counter after successful login."""
    cache_key = CacheKeyPrefix.LOGIN_ATTEMPTS.build_key(identifier)
    return _cache.delete(cache_key)


def increment_upload_count(username: str) -> int:
    """Increment upload counter for a user per hour."""
    cache_key = CacheKeyPrefix.UPLOADS.build_key(username)
    current = _cache.get(cache_key)
    if current is None:
        current = 0
    current += 1
    _cache.set(cache_key, current, UPLOAD_RATE_TTL)
    return current


def get_upload_count(username: str) -> int:
    """Get current upload count for a user in the current hour window."""
    cache_key = CacheKeyPrefix.UPLOADS.build_key(username)
    current = _cache.get(cache_key)
    return current if current is not None else 0


def is_upload_rate_limited(username: str) -> bool:
    """Check if a user has exceeded the upload rate limit (100 uploads/hour)."""
    return get_upload_count(username) >= 100


import atexit

def _cleanup_redis() -> None:
    """Close the global Redis connection when the process terminates."""
    if _cache:
        _cache.close()

atexit.register(_cleanup_redis)
