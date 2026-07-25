"""
test_redis_edge_cases.py
------------------------
Edge-case tests verifying graceful fallback when Redis becomes unavailable.
"""

from unittest.mock import Mock, patch

import pytest
import redis

from src.utils.redis_cache import RedisCache


@pytest.fixture
def mock_redis_refused():
    """Mock Redis client to raise ConnectionRefusedError on all operations."""
    client = Mock()
    # Simulate ConnectionRefusedError on typical operations
    client.ping.side_effect = ConnectionRefusedError("Connection refused")
    client.get.side_effect = ConnectionRefusedError("Connection refused")
    client.set.side_effect = ConnectionRefusedError("Connection refused")
    client.setex.side_effect = ConnectionRefusedError("Connection refused")
    client.delete.side_effect = ConnectionRefusedError("Connection refused")
    client.exists.side_effect = ConnectionRefusedError("Connection refused")
    client.keys.side_effect = ConnectionRefusedError("Connection refused")
    return client


def test_redis_unavailable_during_initialization():
    """Test scenario: Redis unavailable during initialization."""
    with patch("src.utils.redis_cache.redis") as mock_redis_module:
        # When Redis attempts to connect, raise ConnectionRefusedError
        mock_redis_module.from_url.side_effect = ConnectionRefusedError(
            "Connection refused"
        )
        mock_redis_module.Redis.side_effect = ConnectionRefusedError(
            "Connection refused"
        )
        # Ensure we still have access to the exceptions for catching
        mock_redis_module.ConnectionError = redis.ConnectionError
        mock_redis_module.TimeoutError = redis.TimeoutError

        cache = RedisCache.__new__(RedisCache)
        cache._client = None

        # This shouldn't raise an exception
        cache._connect()

        # Verify it falls back
        assert cache._client is None
        assert cache.is_available() is False


def test_redis_disconnects_during_cache_access(mock_redis_refused):
    """Test scenario: Redis disconnects during cache access (ping fails)."""
    cache = RedisCache.__new__(RedisCache)
    cache._client = mock_redis_refused

    # is_available uses ping()
    assert cache.is_available() is False

    # ping() directly
    status, latency = cache.ping()
    assert status is False
    assert latency is None


def test_cache_read_failure(mock_redis_refused):
    """Test scenario: Cache read failure."""
    cache = RedisCache.__new__(RedisCache)
    cache._client = mock_redis_refused

    # Override is_available to simulate that the connection WAS available
    # but the read operation fails
    with patch.object(cache, "is_available", return_value=True):
        # Should catch the error and return None
        result = cache.get("some_key")
        assert result is None

        # json read
        json_result = cache.get_json("some_json_key")
        assert json_result is None

        # exists check
        exists_result = cache.exists("some_key")
        assert exists_result is False


def test_cache_write_failure(mock_redis_refused):
    """Test scenario: Cache write failure."""
    cache = RedisCache.__new__(RedisCache)
    cache._client = mock_redis_refused

    # Override is_available to simulate that the connection WAS available
    # but the write operation fails
    with patch.object(cache, "is_available", return_value=True):
        # Should catch the error and return False
        set_result = cache.set("some_key", "value")
        assert set_result is False

        set_json_result = cache.set_json("some_json_key", {"a": 1})
        assert set_json_result is False

        delete_result = cache.delete("some_key")
        assert delete_result is False

        clear_result = cache.clear_pattern("some_pattern:*")
        assert clear_result == 0
