"""src/api/app.py - FastAPI REST API for LMS integration."""

import logging
import os
import sqlite3
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Request, status
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.dependencies import (
    custom_rate_limit_exceeded_handler,
    limiter,
)
from src.api.middleware import verify_bearer_token
from src.api.routers import (
    admin_router,
    analysis_router,
    auth_router,
    corpus_router,
)
from src.utils.tracing import get_tracer
from src.core.app_config import get_api_support_contact

# Re-exports for backward compatibility with existing tests and scripts

logger = logging.getLogger(__name__)

# ── API Initialization ────────────────────────────────────────────────────────

app = FastAPI(
    title="Semantic Plagiarism Detector API",
    description="REST API for programmatically checking documents for semantic plagiarism.",
    version="1.0.0",
    contact=get_api_support_contact(),
    openapi_tags=[
        {"name": "Authentication", "description": "Authenticate user"},
        {"name": "Plagiarism Detection", "description": "Scanning operations"},
        {"name": "System Administration", "description": "Admin operations"},
        {"name": "Health", "description": "Health checks"},
    ],
    dependencies=[Depends(verify_bearer_token)],
)

# Enable CORS for external LMS frontends
origins = os.getenv("CORS_ALLOWED_ORIGINS", "*")
if origins.strip() == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [
        origin.strip() for origin in origins.split(",") if origin.strip()
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

# SlowAPI Rate Limiting setup
app.state.limiter = limiter


@app.middleware("http")
async def otel_tracing_middleware(request: Request, call_next):
    """Middleware to create an OpenTelemetry root span for every HTTP request."""
    # 1. Check if user_id was pre-set on request.state
    user_id = getattr(request.state, "user_id", None)

    # 2. If missing, attempt to extract token from Authorization header
    if not user_id:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
            if token:
                try:
                    from src.security.jwt_utils import verify_access_token

                    payload = verify_access_token(token)
                    user_id = str(
                        payload.get("sub")
                        or payload.get("user_id")
                        or payload.get("username")
                        or ""
                    )
                except Exception:
                    pass

    if not user_id:
        user_id = "anonymous"

    request.state.user_id = user_id

    try:
        from src.utils.tracing import get_tracer

        tracer = get_tracer()
    except Exception:
        tracer = None

    if not tracer:
        return await call_next(request)

    request_id = request.headers.get("X-Request-ID", "unknown")
    span_name = f"HTTP {request.method} {request.url.path}"
    with tracer.start_as_current_span(span_name) as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", str(request.url))
        span.set_attribute("http.route", request.url.path)
        span.set_attribute("http.request_id", request_id)
        span.set_attribute("user.id", user_id)

        try:
            response = await call_next(request)
            span.set_attribute("http.status_code", response.status_code)
            # Update user.id if set or modified by route handler/dependencies
            final_user_id = getattr(request.state, "user_id", user_id)
            if final_user_id:
                span.set_attribute("user.id", str(final_user_id))
            return response
        except Exception as exc:
            span.record_exception(exc)
            span.set_attribute("http.status_code", 500)
            raise


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors from malformed API requests.
    
    Logs the detailed validation errors via logger.warning to help backend
    engineers debug malformed requests from the frontend or third-party LMS
    platforms, then returns a standardized JSON error response to the client.
    
    Args:
        request: The incoming FastAPI Request object.
        exc: The RequestValidationError containing Pydantic validation details.
        
    Returns:
        JSONResponse with 422 status code and structured error details.
    """
    # Issue #2564: Log the detailed validation errors for backend debugging
    # This helps identify malformed payloads from LMS integrations or frontend bugs
    logger.warning(
        "Request validation failed for %s %s: %s",
        request.method,
        request.url.path,
        exc.errors()
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "message": "Validation failed.",
            "details": [
                {
                    "field": ".".join(map(str, err["loc"])),
                    "message": err["msg"],
                    "type": err["type"],
                }
                for err in exc.errors()
            ],
        },
    )

@app.exception_handler(404)
async def not_found_handler(request, exc: StarletteHTTPException):
    """Custom exception handler for HTTP 404 errors."""
    return JSONResponse(
        status_code=404,
        content={
            "error": True,
            "code": 404,
            "message": "API endpoint or resource not found",
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError exceptions by returning a standardized 400 Bad Request JSON response."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": True,
            "code": status.HTTP_400_BAD_REQUEST,
            "message": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.exception_handler(sqlite3.OperationalError)
async def sqlite_operational_error_handler(request: Request, exc: sqlite3.OperationalError):
    """Handle sqlite3.OperationalError, particularly database is locked, returning 503 Service Unavailable."""
    err_msg = str(exc)
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE if "locked" in err_msg.lower() or "busy" in err_msg.lower() else status.HTTP_500_INTERNAL_SERVER_ERROR
    message = "Service busy, please retry" if status_code == status.HTTP_503_SERVICE_UNAVAILABLE else f"Database error: {err_msg}"

    is_production = os.getenv("APP_ENVIRONMENT", "production").lower() == "production"
    logger.error(f"SQLite operational error: {exc}", exc_info=not is_production)

    return JSONResponse(
        status_code=status_code,
        content={
            "error": True,
            "code": status_code,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler that returns a standardized JSON error payload for any unhandled exception."""
    status_code = getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
    is_production = os.getenv("APP_ENVIRONMENT", "production").lower() == "production"

    logging.getLogger(__name__).error(
        f"Unhandled exception: {exc}", exc_info=not is_production
    )

    message = "An internal server error occurred." if is_production else str(exc)

    return JSONResponse(
        status_code=status_code,
        content={
            "error": True,
            "code": status_code,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Custom exception handler for HTTP errors to return standardized JSON payloads."""
    status_code = exc.status_code
    if status_code == 404:
        message = "API endpoint or resource not found"
    else:
        message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)

    log_level = logging.WARNING if 400 <= status_code < 500 else logging.ERROR
    logger.log(
        log_level,
        "HTTP %d error on %s %s: %s",
        status_code,
        request.method,
        request.url.path,
        message,
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "error": True,
            "code": status_code,
            "message": message,
        },
    )


app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── Register Sub-Routers ──────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(analysis_router)
app.include_router(corpus_router)
app.include_router(admin_router)
"""src/api/app.py - FastAPI REST API for LMS integration."""

import logging
import os
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.dependencies import (
    custom_rate_limit_exceeded_handler,
    limiter,
)
from src.api.middleware import verify_bearer_token
from src.api.routers import (
    admin_router,
    analysis_router,
    auth_router,
    corpus_router,
)
from src.utils.tracing import get_tracer
from src.core.app_config import get_api_support_contact

# Re-exports for backward compatibility with existing tests and scripts

logger = logging.getLogger(__name__)

# ── API Initialization ────────────────────────────────────────────────────────

app = FastAPI(
    title="Semantic Plagiarism Detector API",
    description="REST API for programmatically checking documents for semantic plagiarism.",
    version="1.0.0",
    contact=get_api_support_contact(),
    openapi_tags=[
        {"name": "Authentication", "description": "Authenticate user"},
        {"name": "Plagiarism Detection", "description": "Scanning operations"},
        {"name": "System Administration", "description": "Admin operations"},
        {"name": "Health", "description": "Health checks"},
    ],
    dependencies=[Depends(verify_bearer_token)],
)

# Enable CORS for external LMS frontends
origins = os.getenv("CORS_ALLOWED_ORIGINS", "*")
if origins.strip() == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [
        origin.strip() for origin in origins.split(",") if origin.strip()
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

# SlowAPI Rate Limiting setup
app.state.limiter = limiter


@app.middleware("http")
async def otel_tracing_middleware(request: Request, call_next):
    """Middleware to create an OpenTelemetry root span for every HTTP request."""
    tracer = get_tracer()
    request_id = request.headers.get("X-Request-ID", "unknown")
    user_id = getattr(request.state, "user_id", "anonymous")

    span_name = f"HTTP {request.method} {request.url.path}"
    with tracer.start_as_current_span(span_name) as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", str(request.url))
        span.set_attribute("http.route", request.url.path)
        span.set_attribute("http.request_id", request_id)
        span.set_attribute("user.id", user_id)

        try:
            response = await call_next(request)
            span.set_attribute("http.status_code", response.status_code)
            return response
        except Exception as exc:
            span.record_exception(exc)
            span.set_attribute("http.status_code", 500)
            raise


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return a standardized JSON response for request validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "message": "Validation failed.",
            "details": [
                {
                    "field": ".".join(map(str, err["loc"])),
                    "message": err["msg"],
                    "type": err["type"],
                }
                for err in exc.errors()
            ],
        },
    )


@app.exception_handler(404)
async def not_found_handler(request, exc: StarletteHTTPException):
    """Custom exception handler for HTTP 404 errors."""
    return JSONResponse(
        status_code=404,
        content={
            "error": True,
            "code": 404,
            "message": "API endpoint or resource not found",
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler that returns a standardized JSON error payload for any unhandled exception."""
    status_code = getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
    is_production = os.getenv("APP_ENVIRONMENT", "production").lower() == "production"

    logging.getLogger(__name__).error(
        f"Unhandled exception: {exc}", exc_info=True
    )

    message = "An internal server error occurred." if is_production else str(exc)

    return JSONResponse(
        status_code=status_code,
        content={
            "error": True,
            "code": status_code,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Custom exception handler for HTTP errors to return standardized JSON payloads."""
    status_code = exc.status_code
    if status_code == 404:
        message = "API endpoint or resource not found"
    else:
        message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)

    log_level = logging.WARNING if 400 <= status_code < 500 else logging.ERROR
    logger.log(
        log_level,
        "HTTP %d error on %s %s: %s",
        status_code,
        request.method,
        request.url.path,
        message,
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "error": True,
            "code": status_code,
            "message": message,
        },
    )


app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── Register Sub-Routers ──────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(analysis_router)
app.include_router(corpus_router)
app.include_router(admin_router)
