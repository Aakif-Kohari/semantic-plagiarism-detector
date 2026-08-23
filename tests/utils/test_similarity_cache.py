import importlib.util
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[2] / "src" / "utils" / "similarity_cache.py"
_SPEC = importlib.util.spec_from_file_location("similarity_cache", _MODULE_PATH)
_MODULE = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MODULE)

build_similarity_cache_key = _MODULE.build_similarity_cache_key


def test_lexical_cache_key_uses_lexical_suffix():
    assert build_similarity_cache_key("session-123", use_hybrid=False) == (
        "session-123:analysis_results_lexical"
    )


def test_hybrid_cache_key_uses_hybrid_v1_suffix():
    assert build_similarity_cache_key("session-123", use_hybrid=True) == (
        "session-123:analysis_results_hybrid_v1"
    )


def test_lexical_and_hybrid_cache_keys_are_distinct():
    lexical = build_similarity_cache_key("session-123", use_hybrid=False)
    hybrid = build_similarity_cache_key("session-123", use_hybrid=True)
    assert lexical != hybrid


def test_hybrid_scorer_lru_cache_bounded_size():
    """Verify that HybridScorer._lexical_cache is bounded by LRUCache maxsize (Issue #3003)."""
    from src.core.hybrid_scorer import HybridConfig, HybridScorer, LRUCache

    cache = LRUCache(maxsize=3)
    cache["a"] = 1.0
    cache["b"] = 2.0
    cache["c"] = 3.0
    assert len(cache) == 3

    # Adding 4th entry should evict oldest ("a")
    cache["d"] = 4.0
    assert len(cache) == 3
    assert "a" not in cache
    assert "b" in cache
    assert "c" in cache
    assert "d" in cache

    # Accessing "b" makes it most recent; adding "e" should evict "c"
    _ = cache["b"]
    cache["e"] = 5.0
    assert len(cache) == 3
    assert "c" not in cache
    assert "b" in cache
    assert "d" in cache
    assert "e" in cache

    scorer = HybridScorer(HybridConfig())
    assert isinstance(scorer._lexical_cache, LRUCache)
    assert scorer._lexical_cache.maxsize == 50000

