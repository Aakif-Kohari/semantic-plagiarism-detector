"""
test_redis_cache.py
-------------------
Unit tests for Redis cache functionality.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from src.utils.redis_cache import (
    RedisCache,
    get_cache,
    cache_session_state,
    get_session_state,
    clear_session,
    cache_faiss_index,
    get_faiss_index,
    cache_analysis_results,
    get_analysis_results,
    _cache,
    RedisError,
)
import redis


class TestRedisCache:
    """Test Redis cache manager functionality."""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client."""
        client = Mock()
        client.ping.return_value = True
        return client
    
    @pytest.fixture
    def cache_with_mock(self, mock_redis_client):
        """Create a RedisCache instance with mocked client."""
        from src.utils.redis_cache import _cache
        cache = RedisCache.__new__(RedisCache)
        cache._client = mock_redis_client
        _cache._client = mock_redis_client
        yield cache
        _cache._client = None
    
    def test_cache_set_get(self, cache_with_mock, mock_redis_client):
        """Test basic set and get operations."""
        import pickle
        cache_with_mock.set("test_key", "test_value", ttl=60)
        mock_redis_client.setex.assert_called_once()
        
        mock_redis_client.get.return_value = pickle.dumps("test_value")
        result = cache_with_mock.get("test_key")
        assert result == "test_value"
    
    def test_cache_set_get_json(self, cache_with_mock, mock_redis_client):
        """Test JSON set and get operations."""
        test_dict = {"key": "value", "number": 42}
        cache_with_mock.set_json("test_json", test_dict, ttl=60)
        mock_redis_client.setex.assert_called_once()
        
        mock_redis_client.get.return_value = '{"key": "value", "number": 42}'
        result = cache_with_mock.get_json("test_json")
        assert result == test_dict
    
    def test_cache_delete(self, cache_with_mock, mock_redis_client):
        """Test delete operation."""
        cache_with_mock.delete("test_key")
        mock_redis_client.delete.assert_called_once_with("test_key")
    
    def test_cache_exists(self, cache_with_mock, mock_redis_client):
        """Test exists operation."""
        mock_redis_client.exists.return_value = 1
        result = cache_with_mock.exists("test_key")
        assert result is True
        
        mock_redis_client.exists.return_value = 0
        result = cache_with_mock.exists("test_key")
        assert result is False
    
    def test_cache_unavailable(self):
        """Test behavior when Redis is unavailable."""
        cache = RedisCache.__new__(RedisCache)
        cache._client = None
        
        assert cache.set("test_key", "test_value") is False
        assert cache.get("test_key") is None
        assert cache.delete("test_key") is False
        assert cache.exists("test_key") is False
    
    def test_session_state_caching(self, cache_with_mock, mock_redis_client):
        """Test session state caching functions."""
        session_id = "test_session"
        key = "authenticated"
        value = True
        
        cache_session_state(session_id, key, value)
        expected_key = f"session:{session_id}:{key}"
        mock_redis_client.setex.assert_called_once()
        
        mock_redis_client.get.return_value = b"\x80"
        get_session_state(session_id, key)
        mock_redis_client.get.assert_called_once_with(expected_key)
    
    def test_clear_session(self, cache_with_mock, mock_redis_client):
        """Test clearing session data."""
        session_id = "test_session"
        mock_redis_client.keys.return_value = [
            b"session:test_session:key1",
            b"session:test_session:key2"
        ]
        mock_redis_client.delete.return_value = 2
        
        result = clear_session(session_id)
        assert result is True
        mock_redis_client.keys.assert_called_once_with(f"session:{session_id}:*")
    
    def test_faiss_index_caching(self, cache_with_mock, mock_redis_client):
        """Test FAISS index caching."""
        import pickle
        index_key = "corpus_index"
        index_data = b"fake_index_data"
        
        cache_faiss_index(index_key, index_data)
        mock_redis_client.setex.assert_called_once()
        
        mock_redis_client.get.return_value = pickle.dumps(index_data)
        result = get_faiss_index(index_key)
        assert result == index_data
    
    def test_analysis_results_caching(self, cache_with_mock, mock_redis_client):
        """Test analysis results caching."""
        analysis_key = "test_analysis"
        results = {"embeddings": np.array([[1, 2, 3]]), "similarity": 0.85}
        
        cache_analysis_results(analysis_key, results)
        expected_key = f"analysis:{analysis_key}"
        mock_redis_client.setex.assert_called_once()
        
        mock_redis_client.get.return_value = b"\x80"
        get_analysis_results(analysis_key)
        mock_redis_client.get.assert_called_once_with(expected_key)
    
    def test_get_cache_singleton(self):
        """Test that get_cache returns the same instance."""
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2
    
    def test_redis_failover_during_get(self):
        """Test graceful fallback when Redis fails during a get operation."""
        cache = RedisCache.__new__(RedisCache)
        mock_client = Mock()
        
        # Simulate Redis disconnection during get
        mock_client.get.side_effect = RedisError("Connection refused")
        cache._client = mock_client
        
        # Should return None gracefully without crashing
        result = cache.get("test_key")
        assert result is None
    
    def test_redis_failover_during_set(self):
        """Test graceful fallback when Redis fails during a set operation."""
        cache = RedisCache.__new__(RedisCache)
        mock_client = Mock()
        
        # Simulate Redis disconnection during set
        mock_client.setex.side_effect = RedisError("Connection timeout")
        cache._client = mock_client
        
        # Should return False gracefully
        result = cache.set("test_key", "test_value", ttl=60)
        assert result is False
    
    def test_redis_failover_during_delete(self):
        """Test graceful fallback when Redis fails during a delete operation."""
        cache = RedisCache.__new__(RedisCache)
        mock_client = Mock()
        
        # Simulate Redis disconnection during delete
        mock_client.delete.side_effect = RedisError("Connection lost")
        cache._client = mock_client
        
        # Should return False gracefully
        result = cache.delete("test_key")
        assert result is False
    
    def test_redis_failover_during_exists(self):
        """Test graceful fallback when Redis fails during an exists check."""
        cache = RedisCache.__new__(RedisCache)
        mock_client = Mock()
        
        # Simulate Redis disconnection during exists check
        mock_client.exists.side_effect = RedisError("Server unavailable")
        cache._client = mock_client
        
        # Should return False gracefully
        result = cache.exists("test_key")
        assert result is False
    
    def test_redis_failover_during_get_json(self):
        """Test graceful fallback when Redis fails during JSON get."""
        cache = RedisCache.__new__(RedisCache)
        mock_client = Mock()
        
        # Simulate Redis disconnection during JSON get
        mock_client.get.side_effect = RedisError("Connection refused")
        cache._client = mock_client
        
        # Should return None gracefully
        result = cache.get_json("test_json")
        assert result is None
    
    def test_redis_failover_during_set_json(self):
        """Test graceful fallback when Redis fails during JSON set."""
        cache = RedisCache.__new__(RedisCache)
        mock_client = Mock()
        
        # Simulate Redis disconnection during JSON set
        mock_client.setex.side_effect = RedisError("Connection timeout")
        cache._client = mock_client
        
        # Should return False gracefully
        result = cache.set_json("test_json", {"key": "value"}, ttl=60)
        assert result is False
    
    def test_redis_failover_during_clear_pattern(self):
        """Test graceful fallback when Redis fails during pattern clear."""
        cache = RedisCache.__new__(RedisCache)
        mock_client = Mock()
        
        # Simulate Redis disconnection during pattern clear
        mock_client.keys.side_effect = RedisError("Connection lost")
        cache._client = mock_client
        
        # Should return 0 gracefully
        result = cache.clear_pattern("session:*")
        assert result == 0
    
    def test_redis_failover_during_is_available(self):
        """Test is_available returns False when Redis is unavailable."""
        cache = RedisCache.__new__(RedisCache)
        cache._client = Mock()
        cache._client.ping.side_effect = RedisError("Connection refused")
        
        # Should return False without crashing
        result = cache.is_available()
        assert result is False
    
    def test_cache_fallback_when_redis_unavailable(self):
        """Test that cache gracefully falls back when Redis is completely unavailable."""
        cache = RedisCache.__new__(RedisCache)
        cache._client = None
        
        # All operations should return None/False gracefully
        assert cache.is_available() is False
        assert cache.get("test_key") is None
        assert cache.set("test_key", "test_value") is False
        assert cache.delete("test_key") is False
        assert cache.exists("test_key") is False
        assert cache.get_json("test_key") is None
        assert cache.set_json("test_key", {"value": 1}) is False
        assert cache.clear_pattern("session:*") == 0
    
    def test_session_state_fallback_when_redis_unavailable(self):
        """Test that session state functions gracefully when Redis is unavailable."""
        from src.utils.redis_cache import _cache as global_cache
        
        # Temporarily disable Redis
        original_client = global_cache._client
        global_cache._client = None
        
        try:
            # These should not crash, just return False/None
            assert cache_session_state("test_session", "key", "value") is False
            assert get_session_state("test_session", "key") is None
            assert clear_session("test_session") is False
        finally:
            # Restore original client
            global_cache._client = original_client
    
    def test_faiss_index_fallback_when_redis_unavailable(self):
        """Test that FAISS index functions gracefully when Redis is unavailable."""
        from src.utils.redis_cache import _cache as global_cache
        
        # Temporarily disable Redis
        original_client = global_cache._client
        global_cache._client = None
        
        try:
            # These should not crash, just return None/False
            assert cache_faiss_index("test_key", b"test_data") is False
            assert get_faiss_index("test_key") is None
        finally:
            # Restore original client
            global_cache._client = original_client
    
    def test_analysis_results_fallback_when_redis_unavailable(self):
        """Test that analysis results functions gracefully when Redis is unavailable."""
        from src.utils.redis_cache import _cache as global_cache
        
        # Temporarily disable Redis
        original_client = global_cache._client
        global_cache._client = None
        
        try:
            # These should not crash, just return None/False
            assert cache_analysis_results("test_key", {"results": []}) is False
            assert get_analysis_results("test_key") is None
        finally:
            # Restore original client
            global_cache._client = original_client
    
    def test_pickle_error_handling_in_get(self):
        """Test graceful handling of pickle deserialization errors."""
        cache = RedisCache.__new__(RedisCache)
        mock_client = Mock()
        
        # Simulate valid connection but invalid pickle data
        mock_client.get.return_value = b"invalid_pickle_data"
        cache._client = mock_client
        
        # Should return None gracefully instead of crashing
        result = cache.get("test_key")
        assert result is None
    
    def test_json_decode_error_handling_in_get_json(self):
        """Test graceful handling of JSON deserialization errors."""
        cache = RedisCache.__new__(RedisCache)
        mock_client = Mock()
        
        # Simulate valid connection but invalid JSON data
        mock_client.get.return_value = "invalid json {"
        cache._client = mock_client
        
        # Should return None gracefully instead of crashing
        result = cache.get_json("test_json")
        assert result is None
    
    def test_redis_timeout_during_get(self):
        """Test graceful handling of Redis timeout during get."""
        from src.utils.redis_cache import RedisError
        
        cache = RedisCache.__new__(RedisCache)
        mock_client = Mock()
        
        # Simulate Redis timeout
        mock_client.get.side_effect = redis.TimeoutError("Request timed out") if hasattr(redis, 'TimeoutError') else RedisError("Timeout")
        cache._client = mock_client
        
        # Should return None gracefully
        result = cache.get("test_key")
        assert result is None
