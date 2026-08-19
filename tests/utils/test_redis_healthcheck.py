"""
tests/utils/test_redis_healthcheck.py
-------------------------------------
Unit tests for RedisCache.ping() health check method.
"""

from unittest.mock import MagicMock
from src.utils.redis_cache import RedisCache


def test_redis_cache_ping_when_client_is_none():
    cache = RedisCache.__new__(RedisCache)
    cache._client = None
    connected, latency = cache.ping()
    assert connected is False
    assert latency is None


def test_redis_cache_ping_success():
    cache = RedisCache.__new__(RedisCache)
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    cache._client = mock_client

    connected, latency = cache.ping()
    assert connected is True
    assert latency is not None
    assert latency >= 0.0
    mock_client.ping.assert_called_once()


def test_redis_cache_ping_failure_on_exception():
    cache = RedisCache.__new__(RedisCache)
    mock_client = MagicMock()
    mock_client.ping.side_effect = ConnectionError("Connection refused")
    cache._client = mock_client

    connected, latency = cache.ping()
    assert connected is False
    assert latency is None
    mock_client.ping.assert_called_once()
