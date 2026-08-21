"""
src/core/text_chunking.py
-------------------------
Utilities for splitting documents into overlapping text chunks optimized
for semantic embedding models.

Two strategies are available:

* ``chunk_text``         – fixed character-count chunking with word-boundary
  awareness and optional sentence-aware padding (Issue #1480).
* ``chunk_by_sentences``  – sentence-boundary-aware chunking that groups whole
  sentences into blocks up to *max_chunk_size* characters, ensuring no sentence
  is split mid-word or mid-clause.

Recent Additions (Issue #1480):
- Added sentence-aware padding to chunk_text() and chunk_documents().
- Chunks now extend to the nearest sentence boundary to prevent cutting
  off semantic context mid-sentence, improving embedding quality.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List

try:
    import nltk  # type: ignore
except ImportError:
    nltk = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# Default chunking parameters
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50
MIN_CHUNK_SIZE = 50

# Track whether we've already attempted to download the NLTK punkt corpus
_nltk_punkt_checked = False

# Regex pattern to split text into sentences while preserving punctuation
_SENTENCE_SPLIT_PATTERN = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')

# Regex pattern to identify sentence boundaries.
# Matches '.', '!', or '?' followed by a space and an uppercase letter,
# or followed by the end of the string.
_SENTENCE_BOUNDARY_PATTERN = re.compile(r"([.!?])\s+(?=[A-Z])|([.!?])$")


# ── Sentence splitting helper ─────────────────────────────────────────────────


def _split_into_sentences(text: str) -> List[str]:
    """Return a list of sentences from *text*.

    Tries NLTK ``sent_tokenize`` first.  Falls back to a regex-based splitter
    if NLTK data is unavailable so the function works in restricted environments
    (e.g. CI containers without the punkt corpus downloaded).
    """
    if nltk is not None:
        try:
            from nltk.tokenize import sent_tokenize  # type: ignore

            sentences = sent_tokenize(text)
            if sentences:
                return sentences
        except LookupError:
            # punkt_tab / punkt corpus not downloaded – trigger download once
            try:
                nltk.download("punkt_tab", quiet=True)
                from nltk.tokenize import sent_tokenize  # type: ignore
                return sent_tokenize(text)
            except Exception:
                pass

    # Regex fallback: split on sentence-ending punctuation followed by
    # whitespace and an uppercase letter (covers English prose well).
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"\'\(])", text.strip())
    return [p.strip() for p in parts if p.strip()]


# ── ChunkString ───────────────────────────────────────────────────────────────


class ChunkString(str):
    """str subclass that carries optional chunk metadata.

    Warning: Metadata is lost if the string is modified via standard str operations.
    """

    def __new__(cls, value, metadata=None):
        obj = super().__new__(cls, value)
        obj.metadata = metadata or {}
        return obj


# ── Character-level fallback (CJK / emoji / long-word texts) ─────────────────


def _find_length_capped_end(
    text: str, start: int, limit: int, count_bytes: bool
) -> int:
    """Return the end index so that text[start:end] does not exceed *limit*.

    When count_bytes is True, *limit* is enforced in UTF-8 bytes, so
    multi-byte characters (e.g. emoji, which can be 4 bytes each) are
    measured accurately instead of being undercounted by plain len().
    Otherwise, *limit* is enforced in Unicode code points (previous
    behavior).
    """
    n = len(text)
    if not count_bytes:
        return min(start + limit, n)

    end = start
    byte_total = 0
    while end < n:
        char_bytes = len(text[end].encode("utf-8"))
        if byte_total + char_bytes > limit:
            break
        byte_total += char_bytes
        end += 1
    if end == start and start < n:
        end = start + 1
    return end


def _character_fallback_chunking(
    text: str, chunk_size: int, chunk_overlap: int, count_bytes: bool = False
) -> List[str]:
    """Fallback character-based chunking for non-space or single-token texts (CJK, emojis, long words)."""
    text = text.strip()
    if not text:
        return []

    chunks = []
    step = max(1, chunk_size - chunk_overlap)
    for start in range(0, len(text), step):
        end = _find_length_capped_end(text, start, chunk_size, count_bytes)
        chunk = text[start:end]
        if chunk:
            chunks.append(ChunkString(chunk))
        if end >= len(text):
            break
    return chunks

# ── Sentence boundary search helper (Issue #1480) ────────────────────────────


def _find_sentence_boundary(
    text: str,
    index: int,
    direction: str = "backward",
    max_search: int = 150,
) -> int:
    """Find the nearest sentence boundary relative to the given index.

    Args:
        text: The full document text.
        index: The starting index to search from.
        direction: 'backward' to search left, 'forward' to search right.
        max_search: Maximum number of characters to search before giving up.

    Returns:
        The index of the nearest sentence boundary, or the original index
        if no boundary is found within max_search.
    """
    if not text or index < 0 or index >= len(text):
        return index

    if direction == "backward":
        start_idx = max(0, index - max_search)
        search_space = text[start_idx:index]

        # Find the last occurrence of a sentence boundary in the search space
        matches = list(_SENTENCE_BOUNDARY_PATTERN.finditer(search_space))
        if matches:
            last_match = matches[-1]
            # Return the index immediately after the punctuation
            return start_idx + last_match.end()

    elif direction == "forward":
        end_idx = min(len(text), index + max_search)
        search_space = text[index:end_idx]

        matches = list(_SENTENCE_BOUNDARY_PATTERN.finditer(search_space))
        if matches:
            first_match = matches[0]
            # Return the index immediately after the punctuation
            return index + first_match.end()

    # Fallback to original index if no boundary found
    return index


# ── Fixed-size chunking with sentence-aware padding (Issue #1480) ────────────


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    min_words: int = 5,
    overlap_percentage: float | None = None,
    max_chunks: int = 1000,
    sentence_padding: bool = True,
    count_bytes: bool = False,
) -> List[str]:
    """Split text into chunks of a target character length with overlapping boundaries.

    When *sentence_padding* is enabled (default), chunk start and end boundaries
    are extended to the nearest sentence terminator to preserve semantic context.
    This prevents embeddings from being computed over truncated sentences.

    Args:
        text: The input text to chunk.
        chunk_size: Target length per chunk (see *count_bytes* for units).
        chunk_overlap: Number of characters to overlap between chunks.
        min_words: Minimum word count for a chunk to be included. Chunks with
            fewer words are filtered out to reduce noise from headers/page numbers.
        overlap_percentage: If provided, overrides *chunk_overlap* as a fraction
            of *chunk_size*.
        max_chunks: Maximum number of chunks to generate. Chunking stops once
            this limit is reached, and a warning is logged, to avoid memory
            spikes on extremely large documents.
        sentence_padding: If True, extends chunk boundaries to the nearest
            sentence terminator to preserve semantic context (Issue #1480).
        count_bytes: If True, *chunk_size* is enforced using UTF-8 byte
            length (len(text.encode('utf-8'))) instead of Unicode code
            points. This gives accurate, strict size enforcement for
            multi-byte characters such as emoji (Issue #2435).

    Returns:
        List of chunk strings.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer > 0")

    if overlap_percentage is not None:
        chunk_overlap = int(chunk_size * overlap_percentage)

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be strictly smaller than chunk_size")

    if not text or not text.strip():
        return []

    # Enforce minimum chunk size to prevent infinite loops
    if chunk_size < MIN_CHUNK_SIZE:
        logger.warning(
            "chunk_size %d is too small. Forcing to %d.",
            chunk_size,
            MIN_CHUNK_SIZE,
        )
        chunk_size = MIN_CHUNK_SIZE

    # ── Issue #1390 ───────────────────────────────────────────────────────
    max_chunk_capacity = max_chunks * chunk_size
    if len(text) > max_chunk_capacity:
        logger.warning(
            "Text length (%d chars) exceeded chunk capacity limit; text was truncated",
            len(text),
        )

    # ── Sentence-padding path (Issue #1480) ──────────────────────────────
    if sentence_padding:
        text = text.strip()
        text_len = len(text)
        chunks: List[str] = []
        start = 0

        while start < text_len:
            end = _find_length_capped_end(text, start, chunk_size, count_bytes)

            # Adjust end to the nearest forward sentence boundary
            if end < text_len:
                end = _find_sentence_boundary(
                    text, end, direction="forward", max_search=100
                )
                # Hard cap to prevent chunks from growing too large for embedding models
                max_allowed_end = _find_length_capped_end(
                    text, start, chunk_size * 2, count_bytes
                )
                if end > max_allowed_end:
                    end = max_allowed_end
            chunk = text[start:end].strip()
            if chunk and len(chunk.split()) >= min_words:
                chunks.append(ChunkString(chunk))

            if len(chunks) >= max_chunks:
                logger.warning(
                    "[text_chunking] Document exceeded max_chunks limit "
                    "(%d); truncating remaining chunks.",
                    max_chunks,
                )
                return chunks

            if end >= text_len:
                break

            # Calculate next start position with overlap
            next_start = end - chunk_overlap

            # Apply sentence padding to the start of the next chunk
            if next_start > 0:
                next_start = _find_sentence_boundary(
                    text, next_start, direction="backward", max_search=50
                )

            # Prevent infinite loops if sentence padding doesn't advance the pointer
            if next_start <= start:
                next_start = start + chunk_size - chunk_overlap

            start = next_start

        # Fallback to character-based chunking if no valid chunks were formed
        if not chunks:
            chunks = _character_fallback_chunking(
                text, chunk_size, chunk_overlap, count_bytes=count_bytes
            )
        return [c for c in chunks if len(c.split()) >= min_words]

    # ── Original word-boundary path (sentence_padding=False) ─────────────
    word_headings = getattr(text, "word_headings", None)
    words = text.split()
    chunks = []
    current_chunk_with_indices = []
    current_length = 0

    for i, word in enumerate(words):
        word_len = len(word) + 1  # include space
        if current_length + word_len > chunk_size and current_chunk_with_indices:
            chunk_str = " ".join(w for w, _ in current_chunk_with_indices)

            metadata = {}
            if word_headings:
                first_word_idx = current_chunk_with_indices[0][1]
                if (
                    first_word_idx < len(word_headings)
                    and word_headings[first_word_idx] is not None
                ):
                    metadata["section_title"] = word_headings[first_word_idx]

            if len(chunk_str.split()) >= min_words:
                chunks.append(ChunkString(chunk_str, metadata=metadata))

            if len(chunks) >= max_chunks:
                logger.warning(
                    "[text_chunking] Document exceeded max_chunks limit "
                    "(%d); truncating remaining chunks.",
                    max_chunks,
                )
                return chunks

            # Retain overlap words from the end of the previous chunk
            overlap_words = []
            overlap_len = 0
            for w, idx in reversed(current_chunk_with_indices):
                if overlap_len + len(w) + 1 <= chunk_overlap:
                    overlap_words.insert(0, (w, idx))
                    overlap_len += len(w) + 1
                else:
                    break
            current_chunk_with_indices = overlap_words + [(word, i)]
            current_length = sum(len(w) + 1 for w, _ in current_chunk_with_indices)
        else:
            current_chunk_with_indices.append((word, i))
            current_length += word_len

    if current_chunk_with_indices:
        chunk_str = " ".join(w for w, _ in current_chunk_with_indices)
        metadata = {}
        if word_headings:
            first_word_idx = current_chunk_with_indices[0][1]
            if (
                first_word_idx < len(word_headings)
                and word_headings[first_word_idx] is not None
            ):
                metadata["section_title"] = word_headings[first_word_idx]
        if len(chunk_str.split()) >= min_words:
            chunks.append(ChunkString(chunk_str, metadata=metadata))

    # Fallback to character-based chunking if no valid word chunks were formed
    if not chunks:
        chunks = _character_fallback_chunking(text, chunk_size, chunk_overlap)

    return [c for c in chunks if len(c.split()) >= min_words]


# Alias for backward compatibility with src/core/__init__.py
chunk_document = chunk_text


# ── Sentence-boundary-aware chunking (Issue #919 & #2054) ────────────────────────────


def chunk_by_sentences(
    text: str, 
    max_chunks: int = 1000,
    min_chunk_length: int = 10
) -> List[str]:
    """Split text into chunks based on sentence boundaries.
    
    This function provides a semantic-aware chunking strategy that respects
    natural sentence boundaries, preventing the mid-sentence truncation
    that can occur with fixed-character chunking. This is particularly
    important for maintaining the semantic integrity of embeddings.
    
    Args:
        text: The input text to be chunked.
        max_chunks: Maximum number of chunks to return. Acts as a safety
                   limit to prevent memory exhaustion on extremely large
                   documents. Defaults to 1000. When the limit is reached,
                   the function breaks the loop and logs a warning.
        min_chunk_length: Minimum character length for a chunk to be included.
                         Prevents the creation of tiny, semantically meaningless
                         chunks from fragmented sentences. Defaults to 10.
                         
    Returns:
        A list of string chunks, split by sentence boundaries, respecting
        the max_chunks limit and min_chunk_length threshold.
        
    Raises:
        ValueError: If max_chunks is less than or equal to 0.
        
    Examples:
        >>> text = "First sentence. Second sentence. Third sentence."
        >>> chunks = chunk_by_sentences(text, max_chunks=2)
        >>> len(chunks)
        2
    """
    if not text or not isinstance(text, str):
        return []
        
    if max_chunks <= 0:
        raise ValueError(f"max_chunks must be > 0, got {max_chunks}")
        
    text = text.strip()
    if not text:
        return []
        
    # Split text into individual sentences
    raw_sentences = _SENTENCE_SPLIT_PATTERN.split(text)
    
    chunks: List[str] = []
    current_chunk_sentences: List[str] = []
    current_chunk_length = 0
    
    # Target length for combining short sentences into a single chunk
    # This prevents creating hundreds of 1-word chunks
    target_chunk_length = 500 
    
    for sentence in raw_sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        sentence_length = len(sentence)
        
        # Check if adding this sentence would exceed target chunk length
        if current_chunk_length + sentence_length > target_chunk_length and current_chunk_sentences:
            # Finalize the current chunk
            chunk_text = " ".join(current_chunk_sentences)
            if len(chunk_text) >= min_chunk_length:
                chunks.append(chunk_text)
                
                # Safety limit check (Issue #2054)
                if len(chunks) >= max_chunks:
                    logger.warning(
                        "chunk_by_sentences: Reached max_chunks limit (%d). "
                        "Truncating remaining text to prevent memory exhaustion.",
                        max_chunks
                    )
                    break
                    
            current_chunk_sentences = []
            current_chunk_length = 0
            
        current_chunk_sentences.append(sentence)
        current_chunk_length += sentence_length
        
    # Don't forget the last chunk if we didn't hit the limit
    if current_chunk_sentences and len(chunks) < max_chunks:
        chunk_text = " ".join(current_chunk_sentences)
        if len(chunk_text) >= min_chunk_length:
            chunks.append(chunk_text)
            
    return chunks


# ── Sliding Window Chunk Overlap Optimizer (Issue #1352) ─────────────────────


def chunk_text_dynamic(
    text: str,
    target_size: int = 500,
    min_overlap: int = 50,
    max_chunks: int = 1000,
) -> List[str]:
    """Dynamically split text into sliding window chunks while preserving sentence boundaries.

    Window boundaries are shifted to the nearest sentence end punctuation ('.', '!', '?')
    when a punctuation mark occurs within 20% of target_size.

    Args:
        text: Raw document text to chunk.
        target_size: Target character length per chunk (default: 500).
        min_overlap: Minimum character overlap between consecutive chunks (default: 50).

    Returns:
        List of ChunkString objects representing sentence-boundary-optimized text chunks.
    """
    if not text or not text.strip():
        return []

    if max_chunks <= 0:
        raise ValueError("max_chunks must be greater than 0")

    clean_src = text.strip()
    n_total = len(clean_src)

    if n_total <= target_size:
        return [ChunkString(clean_src)]

    margin = int(target_size * 0.20)
    chunks: List[str] = []
    start = 0

    sentence_punct = {".", "!", "?"}

    while start < n_total:
        target_end = min(n_total, start + target_size)

        if target_end >= n_total:
            actual_end = n_total
        else:
            # Search for sentence ending punctuation within [target_end - margin, target_end + margin]
            min_search = max(start + min_overlap, target_end - margin)
            max_search = min(n_total, target_end + margin)

            candidate_indices = [
                idx
                for idx in range(min_search, max_search)
                if clean_src[idx] in sentence_punct
            ]

            if candidate_indices:
                # Pick sentence ending punctuation closest to target_end
                best_idx = min(
                    candidate_indices, key=lambda idx: abs((idx + 1) - target_end)
                )
                actual_end = best_idx + 1
            else:
                actual_end = target_end

        chunk_content = clean_src[start:actual_end].strip()
        if chunk_content:
            chunks.append(ChunkString(chunk_content))

            if len(chunks) >= max_chunks:
                logger.warning(
                    "Maximum chunk limit reached in chunk_text_dynamic: %d",
                    max_chunks,
                )
                break

        if actual_end >= n_total:
            break

        next_start = actual_end - min_overlap
        if next_start <= start:
            next_start = start + max(1, target_size - min_overlap)
        start = next_start

    return chunks


# ── Multi-document helpers ────────────────────────────────────────────────────


def chunk_documents(
    documents: Dict[str, str],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    min_words: int = 5,
    sentence_padding: bool = True,
) -> Dict[str, List[str]]:
    """Splits a dictionary of document raw texts into chunks respecting customizable
    chunk size and overlap parameters.

    Args:
        documents: Dictionary mapping document name to raw text.
        chunk_size: Target chunk size in characters.
        chunk_overlap: Number of overlapping characters between consecutive chunks.
        min_words: Minimum word count for a chunk to be included.
        sentence_padding: If True, extends chunk boundaries to the nearest
            sentence terminator to preserve semantic context (Issue #1480).

    Returns:
        Dictionary mapping document name to list of chunks.
    """
    chunked_docs = {}
    for doc_name, text in documents.items():
        chunked_docs[doc_name] = chunk_text(
            text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_words=min_words,
            sentence_padding=sentence_padding,
        )
    return chunked_docs
