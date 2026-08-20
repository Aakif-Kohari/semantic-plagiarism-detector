"""
tests/app/test_redis_healthcheck_ui.py
--------------------------------------
Unit tests verifying Redis cache health indicator presence in UI sidebar.
"""

from pathlib import Path

CORPUS_VIEW_PATH = Path("app/views/corpus_view.py")
STREAMLIT_APP_PATH = Path("app/streamlit_app.py")


def test_sidebar_has_cache_status_indicator():
    source = CORPUS_VIEW_PATH.read_text(encoding="utf-8")
    assert "🟢 Cache: Redis" in source
    assert "🟡 Cache: In-Memory" in source
    assert "ping()" in source


def test_streamlit_app_system_health_has_cache_status():
    source = STREAMLIT_APP_PATH.read_text(encoding="utf-8")
    assert "• **Cache Backend:** 🟢 Redis" in source
    assert "• **Cache Backend:** 🟡 In-Memory" in source
