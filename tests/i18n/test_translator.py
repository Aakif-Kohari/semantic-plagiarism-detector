"""
tests/i18n/test_translator.py
------------------------------
Unit tests for the i18n translation engine.
"""

from src.i18n.translator import get_text


def test_translation_english():
    title = get_text("title", lang="en")
    assert "Semantic Plagiarism" in title


def test_translation_spanish():
    title = get_text("title", lang="es")
    assert "Plagio Semántico" in title


def test_translation_fallback():
    missing_key = get_text("non_existent_key_xyz", lang="en")
    assert missing_key == "non_existent_key_xyz"
