"""
tests/i18n/test_translator.py
------------------------------
Unit tests for the i18n translation engine.
"""

import json
import os

from src.i18n.translator import _SUPPORTED_LANGUAGES, _I18N_DIR, get_text


def test_translation_english():
    title = get_text("title", lang="en")
    assert "Semantic Plagiarism" in title


def test_translation_spanish():
    title = get_text("title", lang="es")
    assert "Plagio Semántico" in title


def test_translation_french():
    title = get_text("title", lang="fr")
    assert "Détection de Plagiat" in title


def test_french_supported_languages():
    assert "fr" in _SUPPORTED_LANGUAGES
    assert _SUPPORTED_LANGUAGES["fr"] == "Français"


def test_french_all_keys_match_english():
    """fr.json must have every key that en.json has."""
    en_path = os.path.join(_I18N_DIR, "en.json")
    fr_path = os.path.join(_I18N_DIR, "fr.json")
    with open(en_path, encoding="utf-8") as f:
        en_keys = set(json.load(f).keys())
    with open(fr_path, encoding="utf-8") as f:
        fr_keys = set(json.load(f).keys())
    missing = en_keys - fr_keys
    extra = fr_keys - en_keys
    assert not missing, f"Keys missing from fr.json: {missing}"
    assert not extra, f"Unexpected keys in fr.json: {extra}"


def test_translation_fallback():
    missing_key = get_text("non_existent_key_xyz", lang="en")
    assert missing_key == "non_existent_key_xyz"
