import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from src.asgi_app import SecurityHeadersMiddleware


def homepage(request):
    return PlainTextResponse("OK")


@pytest.mark.unit
def test_security_headers_middleware():
    app = Starlette(
        routes=[Route("/", homepage)],
        middleware=[Middleware(SecurityHeadersMiddleware)],
    )
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["X-Frame-Options"] == "DENY"
    assert (
        response.headers["Content-Security-Policy"]
        == "frame-ancestors 'none'; default-src 'self';"
    )
