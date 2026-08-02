"""ASGI entry point for the Streamlit dashboard.

This wraps the Streamlit UI script (app/streamlit_app.py) so we can attach
Starlette middleware. It's needed for one reason: adding an
X-Frame-Options: DENY header to every HTTP response, to prevent this app
from being embedded in an <iframe> on another site (clickjacking).

Streamlit's own .streamlit/config.toml has no setting for custom HTTP
response headers, so this ASGI-level middleware is the officially
supported way to add one (see Streamlit's "Advanced server configuration
with st.App" documentation).

Run with:
    streamlit run asgi_app.py
"""

import os

import streamlit as st
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "frame-ancestors 'none'; default-src 'self';"
        )
        return response


class ContentLengthLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        max_bytes_str = os.environ.get("MAX_REQUEST_BYTES", "52428800")
        try:
            max_bytes = int(max_bytes_str)
        except ValueError:
            max_bytes = 52428800

        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > max_bytes:
                    return Response("Payload Too Large", status_code=413)
            except ValueError:
                pass

        return await call_next(request)


app = st.App(
    "app/streamlit_app.py",
    middleware=[
        Middleware(SecurityHeadersMiddleware),
        Middleware(ContentLengthLimitMiddleware),
    ],
)

