"""
src/i18n/translator.py
----------------------
Translation manager for dynamic UI internationalization (i18n).
"""

# pylint: disable=streamlit-global-mutation

import json
import os
from typing import Dict

_I18N_DIR = os.path.dirname(os.path.abspath(__file__))
_SUPPORTED_LANGUAGES = {"en": "English", "es": "Español"}

_translations: Dict[str, Dict[str, str]] = {}


def load_translations() -> None:
    """Loads all JSON translation files from the i18n directory."""
    global _translations
    _translations = {}
    for lang_code in _SUPPORTED_LANGUAGES.keys():
        file_path = os.path.join(_I18N_DIR, f"{lang_code}.json")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                _translations[lang_code] = json.load(f)


# Preload translations on module import
load_translations()


def get_text(key: str, lang: str = "en") -> str:
    """
    Returns the translated string for a given key and language code.
    Fallbacks to English if key or language is missing.
    """
    if not _translations:
        load_translations()

    lang_dict = _translations.get(lang)
    if not lang_dict:
        lang_dict = _translations.get("en", {})

    return lang_dict.get(key, _translations.get("en", {}).get(key, key))
