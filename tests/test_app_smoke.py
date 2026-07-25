import io
from unittest.mock import patch

from reportlab.pdfgen import canvas
from streamlit.testing.v1 import AppTest

from tests.conftest import MockDataFactory


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


@patch("src.core.webhook.send_plagiarism_alert")
@patch(
    "src.core.embedding_model.embed_chunks", side_effect=MockDataFactory.embed_chunks
)
def test_app_smoke(mock_embed, mock_webhook):
    import os

    from src.db.corpus_db import clear_all_data

    clear_all_data()
    idx_path = os.path.abspath("corpus.index")
    if os.path.exists(idx_path):
        try:
            os.remove(idx_path)
        except Exception:
            pass

    # Instantiate AppTest
    at = AppTest.from_file("app/streamlit_app.py")

    # Simulate authentication in session state
    at.session_state["authenticated"] = True
    at.session_state["username"] = "admin"
    at.session_state["role"] = "admin"
    at.session_state["page"] = "dashboard"

    # Initial run to display uploader
    at.run()

    # Assert uploader is found
    assert len(at.file_uploader) > 0

    # Generate 2 PDFs with text > 20 words to trigger plagiarism warnings
    sample_text = (
        "Artificial intelligence is intelligence demonstrated by machines, as opposed to natural "
        "intelligence displayed by humans and other animals. This field of computer science is "
        "highly focused on study, research and development of agents that perceive their environment "
        "and take actions that maximize their chance of successfully achieving their goals."
    )
    pdf1 = generate_pdf(sample_text)
    pdf2 = generate_pdf(sample_text)

    # Upload via the native AppTest FileUploader.upload method
    at.file_uploader[0].upload("doc1.pdf", pdf1, "application/pdf")
    at.file_uploader[0].upload("doc2.pdf", pdf2, "application/pdf")

    # Execute full pipeline
    at.run(timeout=30)

    # Ensure no exceptions occurred during pipeline execution
    assert not at.exception

    # Check if metrics are rendered correctly (should be 5 summary metrics)
    assert len(at.metric) >= 5

    # Find the "Run FAISS Search" button and click it to ensure FAISS search works
    faiss_btn = None
    for btn in at.button:
        if "Run FAISS" in btn.label:
            faiss_btn = btn
            break

    assert faiss_btn is not None
    faiss_btn.click().run()
    assert not at.exception

    # Verify warnings are present and severity badge is correct (🔴 High since similarity = 100%)
    badge_found = False
    for md in at.markdown:
        if "High" in md.value:
            badge_found = True
            break
    assert badge_found, "High plagiarism warning badge was not rendered"

    # Verify webhook alert was triggered
    mock_webhook.assert_called_once()
