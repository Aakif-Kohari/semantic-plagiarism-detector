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
