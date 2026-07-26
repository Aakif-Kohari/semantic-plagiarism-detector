"""
redis_cache.py
--------------
Redis connection and caching utilities for session state and FAISS results.
Supports scaling across multiple server nodes in Docker/Kubernetes environments.
"""

import hashlib
import json
import os
import pickle
import re
from typing import Any, Optional
from urllib.parse import quote

try:
    import redis
except ImportError:
    redis = None
from dotenv import load_dotenv

load_dotenv()

RedisError = getattr(redis, "RedisError", Exception)


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


def sanitize_key_component(key_input: str) -> str:
    """
    Sanitizes string inputs used in Redis key generation to prevent
    key injection, key splitting, and command pollution.
    
    Strips whitespace and uses URL encoding or SHA256 hashing for inputs
    containing spaces, wildcards, or control characters.
    """
    if not isinstance(key_input, str):
        key_input = str(key_input)

    stripped = key_input.strip()

    # If the input contains whitespace or illegal characters, hash or encode it safely
    if re.search(r"[\s*?\[\]{}\\\n\r]", stripped) or len(stripped) > 128:
        return hashlib.sha256(stripped.encode("utf-8")).hexdigest()

    return quote(stripped, safe="-_.")


class RedisCache:
    """Redis cache manager for session state and computational results."""

    _instance: Optional["RedisCache"] = None
    _client: Optional[Any] = None

    def __new__(cls) -> "RedisCache":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._connect()

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
        except (AttributeError, redis.ConnectionError, redis.TimeoutError) as e:
            print(f"[RedisCache] Redis connection failed: {e}. Running without cache.")
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

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store a value in Redis with optional TTL."""
        if not self.is_available():
            return False

        try:
            serialized = pickle.dumps(value)
            if ttl:
                self._client.setex(key, ttl, serialized)
            else:
                self._client.set(key, serialized)
            return True
        except (RedisError, pickle.PickleError) as e:
            print(f"[RedisCache] Error setting key {key}: {e}")
            return False

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from Redis."""
        if not self.is_available():
            return None

        try:
            data = self._client.get(key)
            if data is None:
                return None
            return pickle.loads(data)
        except (RedisError, pickle.PickleError) as e:
            print(f"[RedisCache] Error getting key {key}: {e}")
            return None

    def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        if not self.is_available():
            return False

        try:
            self._client.delete(key)
            return True
        except RedisError as e:
            print(f"[RedisCache] Error deleting key {key}: {e}")
            return False

    def set_json(self, key: str, value: dict, ttl: Optional[int] = None) -> bool:
        """Store a JSON-serializable dict in Redis."""
        if not self.is_available():
            return False

        try:
            serialized = json.dumps(value)
            if ttl:
                self._client.setex(key, ttl, serialized)
            else:
                self._client.set(key, serialized)
            return True
        except (RedisError, json.JSONDecodeError) as e:
            print(f"[RedisCache] Error setting JSON key {key}: {e}")
            return False

    def get_json(self, key: str) -> Optional[dict]:
        """Retrieve a JSON value from Redis."""
        if not self.is_available():
            return None

        try:
            data = self._client.get(key)
            if data is None:
                return None
            return json.loads(data)
        except (RedisError, json.JSONDecodeError) as e:
            print(f"[RedisCache] Error getting JSON key {key}: {e}")
            return None

    def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        if not self.is_available():
            return False

        try:
            return bool(self._client.exists(key))
        except RedisError as e:
            print(f"[RedisCache] Error checking key {key}: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        if not self.is_available():
            return 0

        try:
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except RedisError as e:
            print(f"[RedisCache] Error clearing pattern {pattern}: {e}")
            return 0


# Global cache instance
_cache = RedisCache()


def get_cache() -> RedisCache:
    """Get the global Redis cache instance."""
    return _cache


def cache_session_state(session_id: str, key: str, value: Any) -> bool:
    """Cache session state data with TTL."""
    clean_sid = sanitize_key_component(session_id)
    clean_key = sanitize_key_component(key)
    cache_key = f"session:{clean_sid}:{clean_key}"
    return _cache.set(cache_key, value, SESSION_TTL)


def get_session_state(session_id: str, key: str) -> Optional[Any]:
    """Retrieve session state data from cache."""
    clean_sid = sanitize_key_component(session_id)
    clean_key = sanitize_key_component(key)
    cache_key = f"session:{clean_sid}:{clean_key}"
    return _cache.get(cache_key)


def clear_session(session_id: str) -> bool:
    """Clear all session data for a given session ID."""
    clean_sid = sanitize_key_component(session_id)
    pattern = f"session:{clean_sid}:*"
    return _cache.clear_pattern(pattern) > 0


def cache_faiss_index(index_key: str, index_data: bytes) -> bool:
    """Cache FAISS index binary data."""
    clean_key = sanitize_key_component(index_key)
    cache_key = f"faiss:index:{clean_key}"
    return _cache.set(cache_key, index_data, FAISS_INDEX_TTL)


def get_faiss_index(index_key: str) -> Optional[bytes]:
    """Retrieve FAISS index binary data from cache."""
    clean_key = sanitize_key_component(index_key)
    cache_key = f"faiss:index:{clean_key}"
    return _cache.get(cache_key)


def cache_analysis_results(analysis_key: str, results: dict) -> bool:
    """Cache analysis results (embeddings, similarity matrices, etc.)."""
    clean_key = sanitize_key_component(analysis_key)
    cache_key = f"analysis:{clean_key}"
    return _cache.set(cache_key, results, ANALYSIS_RESULTS_TTL)


def get_analysis_results(analysis_key: str) -> Optional[dict]:
    """Retrieve analysis results from cache."""
    clean_key = sanitize_key_component(analysis_key)
    cache_key = f"analysis:{clean_key}"
    return _cache.get(cache_key)
