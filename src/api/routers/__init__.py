"""src/api/routers - FastAPI domain router package."""

from src.api.routers.admin import router as admin_router
from src.api.routers.analysis import router as analysis_router
from src.api.routers.auth import router as auth_router
from src.api.routers.corpus import router as corpus_router

__all__ = [
    "auth_router",
    "analysis_router",
    "corpus_router",
    "admin_router",
]
