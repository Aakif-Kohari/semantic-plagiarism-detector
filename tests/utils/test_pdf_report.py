"""Tests for src/utils/pdf_report.py PDF plagiarism report generation."""

from io import BytesIO
from pathlib import Path
from PyPDF2 import PdfReader

import pytest

from src.utils.pdf_report import (
    generate_plagiarism_report,
    get_similarity_color,
    wrap_text,
)

# Test utilities for golden fixture comparison
from tests.utils import FIXTURES_DIR, compare_pdf_bytes, assert_pdf_matches


def _read_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def test_generates_valid_pdf_with_required_fields():
    pdf_buffer = generate_plagiarism_report(
        doc_a="student_a.pdf",
        doc_b="student_b.pdf",
        overall_similarity=0.934,
        threshold=0.59,
        top_pairs=[
            ("First matching paragraph.", "Second matching paragraph.", 0.96),
        ],
    )
    pdf_bytes = pdf_buffer.getvalue()

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000

    text = _read_text(pdf_bytes)
    assert "student_a.pdf" in text
    assert "student_b.pdf" in text
    assert "93.4%" in text
    assert "First matching paragraph" in text


def test_pdf_matches_golden_fixture():
    """Verify generated PDF matches the golden fixture (deterministic comparison)."""
    golden_path = FIXTURES_DIR / "generate_plagiarism_report.pdf"
    if not golden_path.exists():
        pytest.skip(f"Golden fixture not found: {golden_path}")

    # Use same parameters as generate_golden_pdf.py to ensure deterministic comparison
    pdf_buffer = generate_plagiarism_report(
        doc_a="student_a.pdf",
        doc_b="student_b.pdf",
        overall_similarity=0.934,
        threshold=0.59,
        top_pairs=[
            (
                "This is the first paragraph from document A that contains some text about the subject being discussed.",
                "This is the first paragraph from document B that contains similar text about the same subject being discussed.",
                0.96,
            ),
            (
                "The second paragraph discusses the methodology used in the research study and includes various statistical analyses.",
                "Methodology section describes the research approach and includes statistical analysis similar to the previous paragraph.",
                0.87,
            ),
            (
                "In the conclusion, the authors summarize their findings and suggest areas for future research.",
                "The authors conclude by summarizing their key findings and identifying potential areas for further investigation.",
                0.79,
            ),
            (
                "The introduction provides background information on the topic and establishes the context for the study.",
                "Introduction section gives background on the topic and sets up the research context.",
                0.72,
            ),
        ],
    )

    assert_pdf_matches(pdf_buffer.getvalue(), golden_path)


def test_pdf_generation_detection_fails_with_modified_content():
    """Verify that modified PDF content fails the golden fixture test."""
    golden_path = FIXTURES_DIR / "generate_plagiarism_report.pdf"
    if not golden_path.exists():
        pytest.skip(f"Golden fixture not found: {golden_path}")

    # Generate PDF with MODIFIED content - should fail comparison
    pdf_buffer = generate_plagiarism_report(
        doc_a="student_a.pdf",
        doc_b="student_b.pdf",
        overall_similarity=0.934,
        threshold=0.59,
        top_pairs=[
            (
                "MODIFIED PARAGRAPH CONTENT - THIS SHOULD FAIL",
                "Another modified paragraph that differs from the golden.",
                0.96,
            ),
        ],
    )

    is_match, error_msg = compare_pdf_bytes(pdf_buffer.getvalue(), golden_path)
    assert not is_match, f"Expected PDF comparison to fail but it passed: {error_msg}"


def test_wrap_text_truncates_long_strings():
    short = "Hello world"
    assert wrap_text(short, max_chars=20) == "Hello world"

    long_str = "A" * 100
    wrapped = wrap_text(long_str, max_chars=20)
    assert len(wrapped) == 20
    assert wrapped.endswith("...")


def test_similarity_color_palette():
    high_color = get_similarity_color(0.95)
    medium_color = get_similarity_color(0.80)
    low_color = get_similarity_color(0.50)

    assert high_color.hexval().lower() == "0xff4b4b"
    assert medium_color.hexval().lower() == "0xffa500"
    assert low_color.hexval().lower() == "0x21c55d"
