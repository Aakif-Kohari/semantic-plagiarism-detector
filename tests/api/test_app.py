from fastapi.testclient import TestClient
from src.api.app import app

client = TestClient(app)


def test_http_404_not_found():
    """Verify that a nonexistent route returns a standardized JSON 404 response payload."""
    response = client.get("/api/v1/nonexistent-endpoint-xyz")
    assert response.status_code == 404
    assert response.json() == {
        "error": True,
        "code": 404,
        "message": "API endpoint or resource not found",
    }
