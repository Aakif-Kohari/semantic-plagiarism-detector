"""Tests for src/utils/pdf_report.py PDF plagiarism report generation."""

from io import BytesIO
from PyPDF2 import PdfReader

import pytest

from src.utils.pdf_report import (
    generate_plagiarism_report,
    get_similarity_color,
    wrap_text,
)

# Test utilities for golden fixture comparison
from tests.utils import FIXTURES_DIR, compare_pdf_bytes, assert_pdf_matches

# Text stats utilities
from src.utils.text_stats import (
    count_words,
    count_sentences,
    count_unique_words,
    get_unique_word_ratio,
    compute_text_stats,
    format_stats_for_pdf,
)


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


# ── Tests for text_stats.py ───────────────────────────────────────────────────


def test_count_words():
    """Test word counting function."""
    assert count_words("") == 0
    assert count_words("hello") == 1
    assert count_words("hello world") == 2
    assert count_words("Hello, world! How are you?") == 5


def test_count_sentences():
    """Test sentence counting function."""
    assert count_sentences("") == 0
    assert count_sentences("Hello.") == 1
    assert count_sentences("Hello. World.") == 2
    assert count_sentences("Hello! How are you? I'm fine.") == 3


def test_count_unique_words():
    """Test unique word counting function."""
    assert count_unique_words("") == 0
    assert count_unique_words("hello") == 1
    assert count_unique_words("hello world") == 2
    assert count_unique_words("Hello hello world") == 2  # Case insensitive


def test_get_unique_word_ratio():
    """Test unique word ratio calculation."""
    assert get_unique_word_ratio("") == 0.0
    assert get_unique_word_ratio("hello") == 1.0
    assert get_unique_word_ratio("hello world") == 1.0
    assert get_unique_word_ratio("hello hello world") == pytest.approx(2/3, rel=0.01)


def test_compute_text_stats():
    """Test comprehensive text statistics computation."""
    text = "Hello world. Hello there. The world is beautiful."
    stats = compute_text_stats(text)
    
    assert stats['word_count'] > 0
    assert stats['sentence_count'] > 0
    assert stats['unique_word_count'] > 0
    assert 0.0 <= stats['unique_word_ratio'] <= 1.0


def test_format_stats_for_pdf():
    """Test statistics formatting for PDF table."""
    stats = {
        'word_count': 150,
        'sentence_count': 12,
        'unique_word_count': 100,
        'unique_word_ratio': 0.67,
    }
    
    rows = format_stats_for_pdf(stats)
    
    assert len(rows) == 4
    assert rows[0] == ['Word Count', '150']
    assert rows[1] == ['Sentence Count', '12']
    assert rows[2] == ['Unique Words', '100']
    assert rows[3] == ['Unique Word Ratio', '67.00%']


def test_generate_plagiarism_report_with_text_stats():
    """Test PDF generation with text statistics included."""
    sample_text_a = "This is the first document with some text. It has multiple sentences and words. The content is designed to test the text statistics feature in the PDF report generation."
    sample_text_b = "This is the second document with different content. It has some similar words but mostly unique text. The purpose is to compare with the first document for plagiarism detection purposes."
    
    pdf_buffer = generate_plagiarism_report(
        doc_a="student_a.pdf",
        doc_b="student_b.pdf",
        overall_similarity=0.934,
        threshold=0.59,
        top_pairs=[
            ("First matching paragraph from document A.", 
             "First matching paragraph from document B.", 0.96),
        ],
        doc_a_text=sample_text_a,
        doc_b_text=sample_text_b,
    )
    
    pdf_bytes = pdf_buffer.getvalue()
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000
    
    # Verify statistics are in the PDF
    text = _read_text(pdf_bytes)
    assert "Document Statistics" in text
    assert "Word Count" in text
    assert "Sentence Count" in text
    assert "Unique Word Ratio" in text


def test_generate_plagiarism_report_without_text_stats():
    """Test PDF generation without text statistics (backward compatibility)."""
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
    
    # Statistics section should not be present when text not provided
    text = _read_text(pdf_bytes)
    assert "Document Statistics" not in text
