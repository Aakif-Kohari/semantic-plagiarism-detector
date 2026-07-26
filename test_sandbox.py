import pytest
from unittest.mock import Mock

def test_example():
    import hashlib
    # Simulate two different document queries
    query1 = "artificial intelligence trends 2026"
    query2 = "artificial intelligence trends 2025"

    # Generate hashes
    hash1 = hashlib.sha256(query1.encode('utf-8')).hexdigest()
    hash2 = hashlib.sha256(query2.encode('utf-8')).hexdigest()

    assert hash1 != hash2
    
    prefix = "a1b2c3d4"
    simulated_hash1 = f"{prefix}111111"
    simulated_hash2 = f"{prefix}222222"
    
    key1 = f"analysis:{simulated_hash1}"
    key2 = f"analysis:{simulated_hash2}"
    
    assert key1 != key2

test_example()
print("Success")
