"""Helpers for keeping similarity-analysis cache entries mode-specific."""

from __future__ import annotations


def build_similarity_cache_key(session_id: str, *, use_hybrid: bool) -> str:
    """Build a mode-specific analysis cache key.

    Lexical and Hybrid scoring produce different result spaces. Keeping the
    mode in the key prevents a result generated in one mode from being reused
    after the UI switches to the other mode.
    """
    suffix = "hybrid_v1" if use_hybrid else "lexical"
    return f"{session_id}:analysis_results_{suffix}"
