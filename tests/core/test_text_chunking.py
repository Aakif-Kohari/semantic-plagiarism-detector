"""
tests/core/test_text_chunking.py
---------------------------------
Unit tests for customizable chunk size and overlap parameters.
"""

from src.core.text_chunking import chunk_documents, chunk_text


def test_chunk_text_custom_parameters():
    sample_text = "Word " * 200  # 1000 characters approximately

    # Default parameters
    default_chunks = chunk_text(sample_text, chunk_size=500, chunk_overlap=50)

    # Smaller chunk size should produce more chunks
    small_chunks = chunk_text(sample_text, chunk_size=200, chunk_overlap=20)

    assert len(small_chunks) > len(default_chunks)


def test_chunk_documents_passes_parameters():
    docs = {"doc1.txt": "Line content text repeating " * 50}
    chunked = chunk_documents(docs, chunk_size=300, chunk_overlap=30)

    assert "doc1.txt" in chunked
    assert len(chunked["doc1.txt"]) > 0


def test_min_words_filters_short_chunks():
    # "42" and "Page 1" are ultra-short; only the long sentence should survive
    text = "42\n\nPage 1\n\nThis is a sufficiently long sentence with many words in it."
    chunks = chunk_text(text, chunk_size=500, chunk_overlap=0, min_words=5)
    assert all(len(c.split()) >= 5 for c in chunks)
    assert any("sufficiently" in c for c in chunks)


def test_min_words_default_is_five():
    # Verify default min_words=5 without explicit argument
    text = "one two\n\nthree four five six seven eight"
    chunks = chunk_text(text)
    assert all(len(c.split()) >= 5 for c in chunks)
