import hashlib

# ... existing code ...

def _compute_lexical_score(text_a: str, text_b: str) -> float:
    """
    Computes the lexical similarity score between two texts.
    Uses deterministic MD5 hashing for cache keys to ensure compatibility
    across multiple Gunicorn workers or externalized caches.
    """
    # Generate deterministic hashes
    hash_a = hashlib.md5(text_a.encode('utf-8')).hexdigest()  # nosec
    hash_b = hashlib.md5(text_b.encode('utf-8')).hexdigest()  # nosec
    
    # Example cache key or cache lookup implementation
    cache_key = f"lexical_score:{hash_a}:{hash_b}"
    
    # ... rest of your scoring logic ...
