"""
lexical_similarity.py
---------------------
Computes lexical similarity between documents using TF-IDF vectorization.

This module provides a TF-IDF based baseline for plagiarism detection,
which excels at identifying identical lexical copy-pasting.

Issue #222: Stop-words (the, and, is, a, …) are filtered out before the
TF-IDF set intersection is computed, so common function words cannot
artificially inflate the lexical similarity between unrelated essays.
Filtering is applied both in the TF-IDF vectorizer (via ``stop_words``)
and in the standalone ``jaccard_similarity`` / ``remove_stopwords``
helpers, so any Jaccard-style fallback comparison benefits from the same
filtering.
"""

import functools
import hashlib
import re
from typing import Dict, Iterable, Optional, Set

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ── Stop-word handling (issue #222) ───────────────────────────────────────────
#
# We prefer NLTK's English stop-word list when it is available (it is the
# canonical list the issue asks for), but fall back to a built-in compact
# list so the module stays importable and testable in environments where
# NLTK data hasn't been downloaded yet. Either way, the list is resolved
# ONCE at import time and reused for every comparison.

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")

# Compact fallback list — covers the high-frequency English function words
# that most inflate lexical similarity. Kept intentionally short; NLTK's
# list (179 words) is used when available.
_FALLBACK_STOPWORDS: Set[str] = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "but",
    "if",
    "then",
    "else",
    "when",
    "at",
    "by",
    "for",
    "with",
    "about",
    "against",
    "between",
    "into",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "to",
    "from",
    "up",
    "down",
    "in",
    "out",
    "on",
    "off",
    "over",
    "under",
    "again",
    "further",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "am",
    "have",
    "has",
    "had",
    "having",
    "do",
    "does",
    "did",
    "doing",
    "will",
    "would",
    "shall",
    "should",
    "can",
    "could",
    "may",
    "might",
    "must",
    "of",
    "as",
    "it",
    "its",
    "this",
    "that",
    "these",
    "those",
    "i",
    "you",
    "he",
    "she",
    "we",
    "they",
    "them",
    "his",
    "her",
    "their",
    "our",
    "my",
    "your",
    "me",
    "him",
    "us",
    "so",
    "than",
    "too",
    "very",
    "s",
    "t",
    "just",
    "also",
    "not",
    "no",
    "nor",
    "only",
    "own",
    "same",
    "such",
    "more",
    "most",
    "other",
    "some",
    "any",
    "each",
    "few",
    "both",
    "all",
    "there",
    "here",
    "where",
    "why",
    "how",
    "what",
    "which",
    "who",
    "whom",
}


def _load_stopwords() -> Set[str]:
    """Resolve the English stop-word set.

    Tries NLTK first (per the issue's definition-of-done); falls back to a
    built-in list if NLTK or its corpus is unavailable so the module never
    hard-fails at import time in CI / fresh environments.
    """
    try:
        from nltk.corpus import stopwords as _nltk_stopwords  # type: ignore

        return set(_nltk_stopwords.words("english"))
    except Exception:
        # NLTK not installed, or the 'stopwords' corpus not downloaded.
        # The fallback list still removes the vast majority of function
        # words that inflate Jaccard/TF-IDF similarity.
        return set(_FALLBACK_STOPWORDS)


#: Module-level stop-word set resolved once at import. Exposed publicly so
#: callers (and tests) can inspect / override it without re-importing NLTK.
STOPWORDS: Set[str] = _load_stopwords()


def remove_stopwords(text: str, stopwords: Optional[Iterable[str]] = None) -> str:
    """Return ``text`` with stop-words removed (case-insensitive).

    Tokenizes on word boundaries, lower-cases, drops any token that appears
    in the stop-word set, and re-joins with single spaces. Punctuation and
    casing are not preserved because TF-IDF / Jaccard ignore them anyway.

    Args:
        text: Raw input text.
        stopwords: Optional custom stop-word iterable. Defaults to the
            module-level ``STOPWORDS`` set (NLTK English when available).

    Returns:
        Filtered string. Empty if the input was empty or all stop-words.
    """
    if not text:
        return ""
    stop_set = set(stopwords) if stopwords is not None else STOPWORDS
    tokens = [tok for tok in _TOKEN_RE.findall(text.lower()) if tok not in stop_set]
    return " ".join(tokens)


def tokenize(text: str, stopwords: Optional[Iterable[str]] = None) -> Set[str]:
    """Tokenize ``text`` into a set of lower-cased non-stop-word tokens.

    Used by :func:`jaccard_similarity` for the set-intersection comparison.
    """
    if not text:
        return set()
    stop_set = set(stopwords) if stopwords is not None else STOPWORDS
    return {tok for tok in _TOKEN_RE.findall(text.lower()) if tok not in stop_set}


def jaccard_similarity(
    text_a: str, text_b: str, stopwords: Optional[Iterable[str]] = None
) -> float:
    """Jaccard similarity over stop-word-filtered token sets.

    ``|A ∩ B| / |A ∪ B|``, where A and B are the non-stop-word token sets
    of the two documents. Returns 0.0 if both documents reduce to empty
    sets (e.g. they contained only stop-words).

    Args:
        text_a: First document text.
        text_b: Second document text.
        stopwords: Optional custom stop-word iterable. Defaults to
            ``STOPWORDS``.
    """
    set_a = tokenize(text_a, stopwords=stopwords)
    set_b = tokenize(text_b, stopwords=stopwords)
    if not set_a and not set_b:
        return 0.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def _make_documents_hash(documents: Dict[str, str]) -> str:
    """
    Create a stable hash from document contents for caching.

    Args:
        documents: Dict mapping doc name → raw text content.

    Returns:
        SHA256 hash string of the sorted document contents.
    """
    # Sort by document name to ensure consistent hashing
    sorted_items = sorted(documents.items())
    hash_input = str(sorted_items).encode("utf-8")
    return hashlib.sha256(hash_input).hexdigest()


@functools.lru_cache(maxsize=32)
def _cached_lexical_similarity_matrix(
    documents_hash: str, documents_tuple: tuple
) -> pd.DataFrame:
    """
    Internal cached implementation of lexical similarity matrix.

    This function uses lru_cache for Python-level caching. The documents
    are passed as a tuple to make them hashable for the cache.

    Args:
        documents_hash: Hash of the document contents (for cache key).
        documents_tuple: Tuple of (doc_name, doc_text) pairs.

    Returns:
        Symmetric pandas DataFrame with document names as index and columns.
        Values range 0.0 – 1.0 (1.0 = identical).
    """
    documents = dict(documents_tuple)
    doc_names = list(documents.keys())
    n = len(doc_names)

    if n == 0:
        return pd.DataFrame()

    # Extract texts in the same order as doc_names
    texts = [documents[name] for name in doc_names]

    # Fit a single TfidfVectorizer across all documents.
    # stop_words=list(STOPWORDS) filters common English function words so
    # they cannot inflate similarity between unrelated essays (issue #222).
    vectorizer = TfidfVectorizer(stop_words=list(STOPWORDS))
    tfidf_matrix = vectorizer.fit_transform(texts)  # (N, vocab_size)

    # Compute cosine similarity matrix
    sim_matrix = cosine_similarity(tfidf_matrix)  # (N, N)
    sim_matrix = np.clip(sim_matrix, 0.0, 1.0)  # Numerical safety

    df = pd.DataFrame(sim_matrix, index=doc_names, columns=doc_names)
    return df


def lexical_similarity_matrix(
    documents: Dict[str, str], use_cache: bool = True
) -> pd.DataFrame:
    """
    Build an N×N TF-IDF cosine similarity matrix between all document pairs.

    A single TfidfVectorizer is fitted across all documents to ensure
    consistent vocabulary across the entire corpus, then cosine similarity
    is computed between all document pairs.

    Stop-words (the, and, is, …) are filtered out before vectorization so
    they cannot artificially inflate similarity (issue #222).

    Args:
        documents: Dict mapping doc name → raw text content.
        use_cache: If True (default), use LRU cache to avoid recomputing
                   TF-IDF matrices for identical document sets. Set to False
                   to force recomputation.

    Returns:
        Symmetric pandas DataFrame with document names as index and columns.
        Values range 0.0 – 1.0 (1.0 = identical).
    """
    if use_cache:
        # Convert dict to tuple for hashability
        documents_tuple = tuple(sorted(documents.items()))
        documents_hash = _make_documents_hash(documents)
        return _cached_lexical_similarity_matrix(documents_hash, documents_tuple)
    else:
        # Uncached path for testing or when cache should be bypassed
        doc_names = list(documents.keys())
        n = len(doc_names)

        if n == 0:
            return pd.DataFrame()

        # Extract texts in the same order as doc_names
        texts = [documents[name] for name in doc_names]

        # Fit a single TfidfVectorizer across all documents.
        # stop_words=list(STOPWORDS) filters common English function words
        # so they cannot inflate similarity between unrelated essays (#222).
        vectorizer = TfidfVectorizer(stop_words=list(STOPWORDS))
        tfidf_matrix = vectorizer.fit_transform(texts)  # (N, vocab_size)

        # Compute cosine similarity matrix
        sim_matrix = cosine_similarity(tfidf_matrix)  # (N, N)
        sim_matrix = np.clip(sim_matrix, 0.0, 1.0)  # Numerical safety

        df = pd.DataFrame(sim_matrix, index=doc_names, columns=doc_names)
        return df
