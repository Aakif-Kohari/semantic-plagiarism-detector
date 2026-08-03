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
