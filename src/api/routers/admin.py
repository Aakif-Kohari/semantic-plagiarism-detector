"""src/api/routers/admin.py - System metrics, health check, and status router."""

import logging
import os
import time
from datetime import datetime, timezone

import psutil
from fastapi import APIRouter, Request, Security, status
from fastapi.responses import JSONResponse, PlainTextResponse

from src.api.middleware import get_current_user
from src.api.schemas import (
    HealthCheckResponse,
    HealthzResponse,
    StatusResponse,
)
from src.core.app_config import HEALTHZ_DB_PATHS
from src.db.corpus_db import _connect
from src.version import APP_VERSION

logger = logging.getLogger(__name__)

router = APIRouter()

START_TIME = time.time()
_HEALTHZ_DB_PATHS = tuple(str(p) for p in HEALTHZ_DB_PATHS)


@router.get(
    "/health",
    tags=["Health"],
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
)
def health_check():
    """Healthcheck endpoint for readiness and liveness probes."""
    return {
        "status": "healthy",
        "service": "Semantic Plagiarism Detector API",
        "version": APP_VERSION,
    }


@router.get(
    "/api/v1/status",
    tags=["Health"],
    summary="Get service status, API version, and server UTC time",
    response_model=StatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_service_status(request: Request):
    """Public status endpoint returning service info, API version, and server UTC time."""
    logger.debug("Service status requested")
    return {
        "status": "online",
        "version": getattr(request.app, "version", APP_VERSION),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/api/v1/usage",
    tags=["Health"],
    summary="Get current API request usage statistics and scan counts",
    status_code=status.HTTP_200_OK,
)
def get_api_usage(request: Request):
    """Public usage endpoint returning total scan count and system uptime."""
    from src.api.routers.analysis import total_scans

    uptime = time.time() - START_TIME
    return {
        "total_scans": int(total_scans),
        "uptime_seconds": float(uptime),
    }


@router.get("/metrics", tags=["Monitoring"], response_class=PlainTextResponse)
def metrics_prometheus():
    """Prometheus-format metrics export for production monitoring."""
    from src.core.metrics import generate_latest as _gen

    return PlainTextResponse(_gen().decode("utf-8"))


@router.get("/metrics/json", tags=["Monitoring"])
def metrics_json():
    """JSON-format metrics export for non-Prometheus monitoring setups."""
    from src.core.metrics import generate_metrics_json

    return JSONResponse(generate_metrics_json())


@router.get(
    "/healthz",
    tags=["Health"],
    response_model=HealthzResponse,
)
@router.get(
    "/api/v1/healthz",
    tags=["Health"],
    response_model=HealthzResponse,
)
def healthz():
    """Health endpoint for container orchestration."""
    try:
        with _connect() as conn:
            conn.execute("SELECT 1")

        memory = psutil.virtual_memory()

        if memory.available <= 0:
            raise RuntimeError("Low memory")

        from src.core.app_config import CORPUS_DB_PATH

        db_size_bytes = 0
        db_size_mb = 0.0
        if os.path.exists(CORPUS_DB_PATH):
            try:
                db_size_bytes = os.path.getsize(CORPUS_DB_PATH)
                db_size_mb = round(db_size_bytes / (1024 * 1024), 2)
            except OSError:
                pass

        return {
            "status": "ok",
            "db": "connected",
            "memory": "ok",
            "db_size_bytes": db_size_bytes,
            "db_size_mb": db_size_mb,
        }

    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "db": "disconnected",
                "memory": "unavailable",
                "db_size_bytes": 0,
                "db_size_mb": 0.0,
            },
        )


@router.get(
    "/api/v1/rate_limit",
    tags=["System Administration"],
    summary="Get current API rate limit status",
    status_code=status.HTTP_200_OK,
)
def get_rate_limit(request: Request, _user: dict = Security(get_current_user, scopes=["read"])):
    """Return the current API rate limit information."""
    import time
    from src.utils.redis_cache import get_cache
    from src.security.rate_limiter import get_token_bucket_limiter

    # Default metrics
    limit = 100
    remaining = 100
    reset_in_seconds = 0

    # 1. Check TokenBucketRateLimiter (Bearer Token Rate Limiter)
    auth_header = request.headers.get("authorization", "")
    token = None
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()

    if token:
        lim = get_token_bucket_limiter()
        capacity = lim.capacity
        refill_rate = lim.refill_rate
        
        with lim._lock:
            bucket = lim._buckets.get(token)
            if bucket is None:
                remaining = int(capacity)
                reset_in_seconds = 0
            else:
                now = time.time()
                elapsed = max(0.0, now - bucket["last_refill"])
                current_tokens = min(capacity, bucket["tokens"] + (elapsed * refill_rate))
                remaining = int(current_tokens)
                limit = int(capacity)
                if current_tokens < capacity:
                    reset_in_seconds = int((capacity - current_tokens) / refill_rate)
                else:
                    reset_in_seconds = 0
                return {
                    "limit": limit,
                    "remaining": remaining,
                    "reset_in_seconds": reset_in_seconds,
                }

    # 2. Fallback to active Redis rate limiter / client IP
    client_ip = "127.0.0.1"
    if request.client:
        client_ip = request.client.host
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    cache = get_cache()
    if cache.is_available():
        block_key = f"rate_limit:blocked:{client_ip}"
        if cache._client.exists(block_key):
            ttl = cache._client.ttl(block_key)
            return {
                "limit": limit,
                "remaining": 0,
                "reset_in_seconds": max(1, int(ttl))
            }
        
        redis_key = f"rate_limit:{client_ip}"
        val = cache._client.get(redis_key)
        ttl = cache._client.ttl(redis_key)
        if val is not None:
            current_count = int(val)
            remaining = max(0, limit - current_count)
            reset_in_seconds = max(0, int(ttl))
            return {
                "limit": limit,
                "remaining": remaining,
                "reset_in_seconds": reset_in_seconds,
            }

    return {
        "limit": limit,
        "remaining": remaining,
        "reset_in_seconds": reset_in_seconds,
    }


@router.get(
    "/api/v1/version",
    tags=["System Administration"],
    summary="Get API version",
    status_code=status.HTTP_200_OK,
)
def get_version(request: Request):
    """Return the lightweight API version."""
    return {
        "version": getattr(request.app, "version", APP_VERSION),
        "status": "active",
    }
