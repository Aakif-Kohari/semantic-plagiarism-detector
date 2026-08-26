import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Mock exception matching your cache provider client infrastructure
class RedisConnectionError(Exception):
    """Simulated Redis connection failure exception."""
    pass

# --- Redis Failure Resilience Test Suite ---

@patch("src.api.routers.corpus.get_cache")
@patch("src.api.routers.corpus.get_sqlite_db")
def test_clear_all_documents_succeeds_when_redis_is_down(mock_get_sqlite_db, mock_get_cache):
    """
    Scenario: Verify clear_all_documents catches Redis failures and successfully purges SQLite.
    Acceptance Criteria:
    - get_cache().clear_pattern raises RedisConnectionError.
    - /api/v1/clear returns HTTP 200 OK.
    - SQLite data purging function is still successfully invoked.
    """
    # 1. Setup Mock Cache provider to simulate a connection dropout event
    mock_cache_instance = MagicMock()
    mock_cache_instance.clear_pattern.side_effect = RedisConnectionError("Redis server unreachable.")
    mock_get_cache.return_value = mock_cache_instance

    # 2. Setup Mock SQLite DB execution contexts
    mock_db_session = MagicMock()
    mock_get_sqlite_db.return_value = mock_db_session

    # 3. Initialize your application client router environment
    # Importing inline to ensure clean mock patching context limits
    from src.main import app  
    client = TestClient(app)

    # 4. Trigger the target cleanup routing endpoint
    response = client.post("/api/v1/clear")

    # 5. Assert fallback recovery and execution integrity metrics
    assert response.status_code == 200, f"Expected HTTP 200 but received {response.status_code}"
    
    # Assert cache clear attempt was initiated before dropping out
    mock_cache_instance.clear_pattern.assert_called_once()
    
    # Critical Boundary: Assert SQLite purge query execution was still dispatched completely
    mock_db_session.execute.assert_called()
    mock_db_session.commit.assert_called_once()
