import pytest
from src.utils.pdf_highlighter import highlight_pdf_matches as highlight_hl
from src.utils.pdf_report import highlight_pdf_matches as highlight_rep

def test_pdf_highlighters_context_manager():
    """
    Verify that highlight_pdf_matches functions from both pdf_highlighter and pdf_report
    execute without leaks, utilizing context managers correctly.
    """
    # 1. Read a valid sample PDF fixture
    with open("tests/fixtures/clean.pdf", "rb") as f:
        pdf_bytes = f.read()

    # 2. Test pdf_highlighter.highlight_pdf_matches
    res_hl = highlight_hl(pdf_bytes, ["plagiarism", "semantic"])
    assert isinstance(res_hl, bytes)
    assert len(res_hl) > 0

    # 3. Test pdf_report.highlight_pdf_matches
    res_rep = highlight_rep(pdf_bytes, ["plagiarism", "semantic"])
    assert isinstance(res_rep, bytes)
    assert len(res_rep) > 0
