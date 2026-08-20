from pathlib import Path

APP_PATH = Path("app/streamlit_app.py")


def test_faiss_results_use_interactive_ui():
    """Verify that the interactive render_faiss_results_ui component is used to support chunk diff inspection."""
    source = APP_PATH.read_text(encoding="utf-8")
    assert "render_faiss_results_ui(results," in source


def test_static_faiss_result_loop_is_removed():
    """Verify that raw print loops for FAISS results are removed in favor of the component."""
    source = APP_PATH.read_text(encoding="utf-8")
    assert "for rec, score in results:" not in source
    assert "st.caption(rec.chunk_text)" not in source
