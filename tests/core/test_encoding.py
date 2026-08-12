"""
Tests for text encoding normalization and type guards.
"""

import pytest
from src.core.encoding import normalize_encoding


def test_normalize_encoding_with_valid_string():
    """Test normal string input with mojibake replacements."""
    assert normalize_encoding("CafÃ©") == "Café"


def test_normalize_encoding_with_empty_string():
    """Test empty string input returns empty string."""
    assert normalize_encoding("") == ""


def test_normalize_encoding_with_none():
    """Test None input safely returns empty string instead of raising AttributeError."""
    assert normalize_encoding(None) == ""


def test_normalize_encoding_with_bytes():
    """Test bytes input returns empty string or handles non-string gracefully."""
    assert normalize_encoding(b"test bytes") == ""
    