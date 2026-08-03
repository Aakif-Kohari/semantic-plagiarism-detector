# JSONContentTypeMiddleware unit coverage for Issue #1394.
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient as StarletteTestClient

from src.asgi_app import JSONContentTypeMiddleware


async def _json_echo(request):
    return JSONResponse({"accepted": True})


def _json_middleware_client():
    test_app = Starlette(
        routes=[
            Route(
                "/api/v1/settings",
                _json_echo,
                methods=["POST", "PUT", "GET"],
            ),
            Route(
                "/api/v1/scan",
                _json_echo,
                methods=["POST"],
            ),
            Route(
                "/internal/action",
                _json_echo,
                methods=["POST"],
            ),
        ],
        middleware=[Middleware(JSONContentTypeMiddleware)],
    )
    return StarletteTestClient(test_app)


def test_json_middleware_accepts_application_json():
    response = _json_middleware_client().post(
        "/api/v1/settings",
        headers={"Content-Type": "application/json"},
        content=b'{"enabled":true}',
    )

    assert response.status_code == 200
    assert response.json() == {"accepted": True}


def test_json_middleware_accepts_json_with_charset():
    response = _json_middleware_client().put(
        "/api/v1/settings",
        headers={
            "Content-Type": "Application/JSON; Charset=UTF-8",
        },
        content=b'{"enabled":true}',
    )

    assert response.status_code == 200


def test_json_middleware_accepts_structured_json_suffix():
    response = _json_middleware_client().post(
        "/api/v1/settings",
        headers={
            "Content-Type": "application/problem+json",
        },
        content=b'{"title":"problem"}',
    )

    assert response.status_code == 200


def test_json_middleware_rejects_non_json_post_payload():
    response = _json_middleware_client().post(
        "/api/v1/settings",
        headers={"Content-Type": "text/plain"},
        content=b"not json",
    )

    assert response.status_code == 415
    assert response.json() == {
        "detail": (
            "Unsupported Media Type: Request must be application/json"
        )
    }


def test_json_middleware_rejects_missing_content_type_with_body():
    response = _json_middleware_client().put(
        "/api/v1/settings",
        content=b'{"enabled":true}',
    )

    assert response.status_code == 415


def test_json_middleware_allows_bodyless_post():
    response = _json_middleware_client().post(
        "/api/v1/settings",
        content=b"",
    )

    assert response.status_code == 200


def test_json_middleware_does_not_restrict_get_requests():
    response = _json_middleware_client().get(
        "/api/v1/settings",
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == 200


def test_json_middleware_excludes_multipart_scan_endpoint():
    response = _json_middleware_client().post(
        "/api/v1/scan",
        headers={
            "Content-Type": (
                "multipart/form-data; boundary=example"
            )
        },
        content=b"--example--",
    )

    assert response.status_code == 200


def test_json_middleware_ignores_non_api_post_routes():
    response = _json_middleware_client().post(
        "/internal/action",
        headers={"Content-Type": "text/plain"},
        content=b"streamlit-internal-payload",
    )

    assert response.status_code == 200


# ── TokenBucketRateLimiter Tests (#1362) ──────────────────────────────────────

import time
from src.asgi_app import TokenBucketRateLimiter


def _rate_limiter_client(rate_limit_per_minute=60, burst_capacity=10, api_prefix="/api/"):
    test_app = Starlette(
        routes=[
            Route(
                "/api/v1/resource",
                _json_echo,
                methods=["GET", "POST"],
            ),
            Route(
                "/dashboard/home",
                _json_echo,
                methods=["GET"],
            ),
        ],
        middleware=[
            Middleware(
                TokenBucketRateLimiter,
                rate_limit_per_minute=rate_limit_per_minute,
                burst_capacity=burst_capacity,
                api_prefix=api_prefix,
            )
        ],
    )
    return StarletteTestClient(test_app)


def test_token_bucket_allows_within_burst_capacity():
    client = _rate_limiter_client(burst_capacity=10)
    for _ in range(10):
        response = client.get("/api/v1/resource")
        assert response.status_code == 200


def test_token_bucket_rejects_exceeding_burst_capacity_with_429():
    client = _rate_limiter_client(rate_limit_per_minute=60, burst_capacity=5)

    # First 5 requests within burst capacity succeed
    for _ in range(5):
        res = client.get("/api/v1/resource")
        assert res.status_code == 200

    # 6th request exceeds burst capacity -> 429 Too Many Requests
    blocked_response = client.get("/api/v1/resource")
    assert blocked_response.status_code == 429
    assert blocked_response.text == "Too Many Requests"
    assert "Retry-After" in blocked_response.headers
    assert blocked_response.headers["Retry-After"].isdigit()
    assert int(blocked_response.headers["Retry-After"]) >= 1


def test_token_bucket_refills_tokens_over_time():
    client = _rate_limiter_client(rate_limit_per_minute=600, burst_capacity=2)

    # Exhaust capacity
    assert client.get("/api/v1/resource").status_code == 200
    assert client.get("/api/v1/resource").status_code == 200
    assert client.get("/api/v1/resource").status_code == 429

    # Wait 0.2 seconds -> 2 tokens refilled (600/min = 10/sec)
    time.sleep(0.2)
    assert client.get("/api/v1/resource").status_code == 200


def test_token_bucket_ignores_non_api_routes():
    client = _rate_limiter_client(burst_capacity=2, api_prefix="/api/")

    # Exhaust API route capacity
    client.get("/api/v1/resource")
    client.get("/api/v1/resource")
    assert client.get("/api/v1/resource").status_code == 429

    # Non-API route is not rate-limited
    assert client.get("/dashboard/home").status_code == 200


def test_token_bucket_per_ip_isolation():
    client = _rate_limiter_client(burst_capacity=1)

    # IP 1 uses its 1 token
    res1 = client.get("/api/v1/resource", headers={"X-Forwarded-For": "192.168.1.10"})
    assert res1.status_code == 200

    res1_blocked = client.get("/api/v1/resource", headers={"X-Forwarded-For": "192.168.1.10"})
    assert res1_blocked.status_code == 429

    # IP 2 still has its token
    res2 = client.get("/api/v1/resource", headers={"X-Forwarded-For": "192.168.1.20"})
    assert res2.status_code == 200


# ── Standardized Health Status Endpoint (#1273) ─────────────────────────────

from datetime import datetime

from fastapi.testclient import TestClient

from src.api.app import app

_status_client = TestClient(app)


def test_api_v1_status_returns_online_payload():
    """Verify GET /api/v1/status returns the standardized status payload."""
    response = _status_client.get("/api/v1/status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["version"] == "1.0.0"


def test_api_v1_status_timestamp_is_iso_utc():
    """Verify the timestamp is a parseable ISO 8601 string in UTC."""
    response = _status_client.get("/api/v1/status")
    data = response.json()

    parsed = datetime.fromisoformat(data["timestamp"])
    assert parsed.tzinfo is not None
    assert parsed.utcoffset().total_seconds() == 0


def test_api_v1_status_is_public_without_token():
    """Verify /api/v1/status is reachable without a bearer token."""
    response = _status_client.get(
        "/api/v1/status",
        headers={},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_scope_enforcement_rate_limit_endpoint():
    """Verify scope enforcement on /api/v1/rate_limit (requires 'read')."""
    from fastapi.testclient import TestClient
    from src.api.app import app

    client = TestClient(app)

    # 1. No credentials -> 401
    res = client.get("/api/v1/rate_limit")
    assert res.status_code == 401

    # 2. Token with 'read' scope -> 200
    res = client.get(
        "/api/v1/rate_limit",
        headers={"Authorization": "Bearer test-read-token"}
    )
    assert res.status_code == 200

    # 3. Token with no scopes -> 403
    res = client.get(
        "/api/v1/rate_limit",
        headers={"Authorization": "Bearer test-no-scope-token"}
    )
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]


def test_scope_enforcement_clear_endpoint():
    """Verify scope enforcement on /api/v1/clear (requires 'admin')."""
    from fastapi.testclient import TestClient
    from src.api.app import app

    client = TestClient(app)

    # 1. Token with 'admin' scope -> success (either 200 or 500 depending on actual database operations but not 401/403)
    res = client.post(
        "/api/v1/clear?username=admin",
        headers={"Authorization": "Bearer test-admin-token"}
    )
    assert res.status_code in (200, 500)

    # 2. Token with 'write' but no 'admin' -> 403
    res = client.post(
        "/api/v1/clear?username=admin",
        headers={"Authorization": "Bearer test-write-token"}
    )
    assert res.status_code == 403

import asyncio
import json
from unittest.mock import Mock

from src.api.app import global_exception_handler


def test_global_exception_handler_returns_standard_payload(monkeypatch):
    """Verify Issue #1500: unhandled exceptions return the standardized JSON payload."""
    monkeypatch.setenv("APP_ENVIRONMENT", "development")
    mock_request = Mock()

    response = asyncio.run(global_exception_handler(mock_request, ValueError("boom")))
    body = json.loads(response.body)

    assert response.status_code == 500
    assert body["error"] is True
    assert body["code"] == 500
    assert body["message"] == "boom"
    assert "timestamp" in body


def test_global_exception_handler_masks_details_in_production(monkeypatch):
    """Verify Issue #1500: internal exception details are masked in production."""
    monkeypatch.setenv("APP_ENVIRONMENT", "production")
    mock_request = Mock()

    response = asyncio.run(
        global_exception_handler(mock_request, ValueError("sensitive internal detail"))
    )
    body = json.loads(response.body)

    assert body["message"] == "An internal server error occurred."
    assert "sensitive internal detail" not in body["message"]