import io
import os
from unittest.mock import patch

import pytest
from reportlab.pdfgen import canvas
from streamlit.testing.v1 import AppTest

from tests.conftest import MockDataFactory

# Paths to stale artifacts that can pollute test runs
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_STALE_INDEX = os.path.join(_REPO_ROOT, "corpus.index")
_STALE_DB = os.path.join(_REPO_ROOT, "corpus.db")


def _cleanup_stale_artifacts():
    """Remove leftover FAISS index and SQLite DB from prior runs."""
    for path in (_STALE_INDEX, _STALE_DB):
        try:
            if os.path.exists(path):
                os.remove(path)
        except PermissionError:
            pass  # File locked by another process (e.g. SQLite); safe to skip


def generate_pdf(text: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    # Write text in lines to make it clean
    words = text.split()
    lines = []
    for i in range(0, len(words), 8):
        lines.append(" ".join(words[i : i + 8]))

    y = 750
    for line in lines:
        c.drawString(50, y, line)
        y -= 20

    c.showPage()
    c.save()
    return buf.getvalue()


@pytest.fixture(autouse=True)
def clean_smoke_test_env():
    import os

    from src.db.corpus_db import clear_all_data

    clear_all_data()
    index_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "corpus.index")
    )
    if os.path.exists(index_path):
        try:
            os.remove(index_path)
        except Exception:
            pass
    yield
    clear_all_data()
    if os.path.exists(index_path):
        try:
            os.remove(index_path)
        except Exception:
            pass


@patch("src.core.webhook.send_plagiarism_alert")
@patch(
    "src.core.embedding_model.get_embedding_model_info",
    return_value=("all-MiniLM-L6-v2", 384),
)
@patch(
    "src.core.embedding_model.embed_chunks", side_effect=MockDataFactory.embed_chunks
)
def test_app_smoke(mock_embed, mock_model_info, mock_webhook):
    # Clean up stale artifacts from prior test runs
    _cleanup_stale_artifacts()

    try:
        # Instantiate AppTest
        at = AppTest.from_file("app/streamlit_app.py")

        # Simulate authentication in session state
        at.session_state["authenticated"] = True
        at.session_state["username"] = "admin"
        at.session_state["role"] = "admin"
        at.session_state["page"] = "dashboard"

        # Initial run to display uploader
        at.run(timeout=30)

        # Assert uploader is found
        assert len(at.file_uploader) > 0

        # Generate 2 PDFs with DISTINCT text so they get different SHA256 hashes.
        # The deduplication logic in streamlit_app.py skips files with duplicate hashes,
        # so identical PDFs would result in only 1 document processed → no pairs → no badge.
        # The mock embedder always returns the same vector regardless of content,
        # so cosine similarity will still be 1.0 → High severity badge rendered.
        sample_text_a = (
            "Artificial intelligence is intelligence demonstrated by machines, as opposed to natural "
            "intelligence displayed by humans and other animals. This field of computer science is "
            "highly focused on study, research and development of agents that perceive their environment "
            "and take actions that maximize their chance of successfully achieving their goals."
        )
        sample_text_b = (
            "Machine learning is a subset of artificial intelligence that provides systems the ability "
            "to automatically learn and improve from experience without being explicitly programmed. "
            "It focuses on developing computer programs that can access data and use it to learn for "
            "themselves, enabling computers to find hidden insights without being explicitly programmed."
        )
        pdf1 = generate_pdf(sample_text_a)
        pdf2 = generate_pdf(sample_text_b)

        # Upload via the native AppTest FileUploader.upload method
        at.file_uploader[0].upload("doc1.pdf", pdf1, "application/pdf")
        at.file_uploader[0].upload("doc2.pdf", pdf2, "application/pdf")

        # Execute full pipeline
        at.run(timeout=30)

        # Ensure no exceptions occurred during pipeline execution
        assert not at.exception

        # Check if metrics are rendered correctly (should be 5 summary metrics)
        assert len(at.metric) >= 5

        # ── Badge check on initial pipeline run ───────────────────────────────
        # The warnings tab renders immediately after the pipeline run while
        # uploaded files are still in the widget state. After clicking FAISS,
        # AppTest resets the file uploader, causing the app to call st.stop()
        # before rendering the warnings tab — so we check the badge HERE.
        high_severity_keywords = (
            "High",
            "🔴",
            "high",
            "CRITICAL",
            "Critical",
            "danger",
            "Danger",
        )
        badge_found = any(
            any(kw in md.value for kw in high_severity_keywords) for md in at.markdown
        )
        assert badge_found, "High plagiarism warning badge was not rendered"

        # Verify webhook alert was triggered (called during initial pipeline run)
        mock_webhook.assert_called_once()

        # ── FAISS smoke test ───────────────────────────────────────────────────
        # Find the "Run FAISS Search" button and click it — just verify no crash.
        faiss_btn = None
        for btn in at.button:
            if "Run FAISS" in btn.label:
                faiss_btn = btn
                break

        assert faiss_btn is not None
        faiss_btn.click().run()
        # App may hit st.stop() early on re-run (empty uploader), but must not
        # raise an unhandled exception.
        assert not at.exception

    finally:
        # Always clean up artifacts after the test, regardless of pass/fail
        _cleanup_stale_artifacts()
