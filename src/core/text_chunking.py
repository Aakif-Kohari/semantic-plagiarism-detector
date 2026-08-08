"""
src/core/text_chunking.py
-------------------------
Utilities for splitting raw extracted document text into processable chunks.
"""

from typing import Dict, List


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    min_words: int = 5,
) -> List[str]:
    """
    Splits text into chunks of a target character length with overlapping boundaries.
    """
    if not text or not text.strip():
        return []

    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0

    for word in words:
        word_len = len(word) + 1  # include space
        if current_length + word_len > chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))

            # Retain overlap words from the end of the previous chunk
            overlap_words = []
            overlap_len = 0
            for w in reversed(current_chunk):
                if overlap_len + len(w) + 1 <= chunk_overlap:
                    overlap_words.insert(0, w)
                    overlap_len += len(w) + 1
                else:
                    break
            current_chunk = overlap_words + [word]
            current_length = sum(len(w) + 1 for w in current_chunk)
        else:
            current_chunk.append(word)
            current_length += word_len

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return [c for c in chunks if len(c.split()) >= min_words]


# Alias for backward compatibility with src/core/__init__.py
chunk_document = chunk_text


def chunk_documents(
    documents: Dict[str, str],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    min_words: int = 5,
) -> Dict[str, List[str]]:
    """
    Splits a dictionary of document raw texts into chunks respecting customizable
    chunk size and overlap parameters.
    """
    chunked_docs = {}
    for doc_name, text in documents.items():
        chunked_docs[doc_name] = chunk_text(
            text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_words=min_words,
        )
    return chunked_docs
