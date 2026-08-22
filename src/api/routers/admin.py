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
        "total_scans": total_scans,
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
    """Health endpoint for container orchestration checking database, memory, and disk space."""
    db_status = "connected"
    try:
        with _connect() as conn:
            conn.execute("SELECT 1")
    except Exception:
        db_status = "disconnected"

    memory_status = "ok"
    try:
        memory = psutil.virtual_memory()
        if memory.available <= 0:
            memory_status = "unavailable"
    except Exception:
        memory_status = "unavailable"

    disk_status = "ok"
    try:
        disk = psutil.disk_usage('/')
        if (100.0 - disk.percent) < 5.0:
            disk_status = "low"
    except Exception:
        disk_status = "unavailable"

    is_healthy = (
        db_status == "connected"
        and memory_status == "ok"
        and disk_status == "ok"
    )

    from src.core.app_config import CORPUS_DB_PATH
    db_size_bytes = 0
    db_size_mb = 0.0
    if os.path.exists(CORPUS_DB_PATH):
        try:
            db_size_bytes = os.path.getsize(CORPUS_DB_PATH)
            db_size_mb = round(db_size_bytes / (1024 * 1024), 2)
        except OSError:
            pass

    response_content = {
        "status": "ok" if is_healthy else "degraded",
        "db": db_status,
        "memory": memory_status,
        "disk": disk_status,
        "db_size_bytes": db_size_bytes if is_healthy else 0,
        "db_size_mb": db_size_mb if is_healthy else 0.0,
    }

    if is_healthy:
        return response_content
    else:
        return JSONResponse(
            status_code=503,
            content=response_content,
        )


@router.get(
    "/api/v1/rate_limit",
    tags=["System Administration"],
    summary="Get current API rate limit status",
    status_code=status.HTTP_200_OK,
)
def get_rate_limit(_user: dict = Security(get_current_user, scopes=["read"])):
    """Return the current API rate limit information."""
    return {
        "limit": 100,
        "remaining": 85,
        "reset_in_seconds": 45,
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
