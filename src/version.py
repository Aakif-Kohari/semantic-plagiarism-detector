"""
src/version.py
----------------
Single source of truth for the application's version string.

Previously this string was duplicated as a hardcoded literal in several
places (the FastAPI `version=` kwarg in src/api/app.py, the /health,
/api/v1/status, and /api/v1/version endpoint fallbacks in
src/api/routers/admin.py, and src/utils/version_check.py's own
APP_VERSION constant), so bumping the version meant remembering to edit
every one of those spots -- and they could silently drift out of sync
with each other and with the actual released version.

Bump this constant in lock-step with CHANGELOG.md when cutting a new
release. Everything else in the codebase that needs the running app's
version should import APP_VERSION from here rather than hardcoding its
own copy.
"""

from __future__ import annotations

APP_VERSION: str = "1.0.0"
