"""
src/i18n/translator.py
---------------------

Translation manager for dynamic UI internationalization (i18n).
"""

# pylint: disable=streamlit-global-mutation

from __future__ import annotations

import html
import json
import logging
import os
from typing import Any, Dict

import streamlit as st

logger = logging.getLogger(__name__)

_I18N_DIR = os.path.dirname(os.path.abspath(__file__))
_SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
}
LANGUAGE_DISPLAY = _SUPPORTED_LANGUAGES
DISPLAY_TO_CODE = {
    display_name: code for code, display_name in _SUPPORTED_LANGUAGES.items()
}

_translations: Dict[str, Dict[str, str]] = {}


@st.cache_data(show_spinner=False)
def _load_translation_dictionary(
    file_path: str,
) -> Dict[str, str]:
    """Read and cache one translation JSON dictionary.

    The resolved file path is part of Streamlit's cache key, so each
    language file is cached independently. ``st.cache_data`` returns a
    deserialised copy to callers, preventing accidental mutation of the
    cached value.
    """
    with open(file_path, "r", encoding="utf-8") as translation_file:
        loaded = json.load(translation_file)

    if not isinstance(loaded, dict):
        raise ValueError("Translation file must contain a JSON object: " f"{file_path}")

    return {str(key): str(value) for key, value in loaded.items()}


def load_translations() -> None:
    """Load all supported dictionaries through the Streamlit cache.

    Missing or malformed non-English files are skipped with a warning.
    A malformed English dictionary is also logged; ``get_text`` then
    safely falls back to returning the requested key.
    """
    global _translations

    loaded_translations: Dict[str, Dict[str, str]] = {}

    for lang_code in _SUPPORTED_LANGUAGES:
        file_path = os.path.join(
            _I18N_DIR,
            f"{lang_code}.json",
        )

        if not os.path.isfile(file_path):
            logger.warning(
                "Translation file is missing for language %s: %s",
                lang_code,
                file_path,
            )
            continue

        try:
            loaded_translations[lang_code] = _load_translation_dictionary(file_path)
        except (
            OSError,
            json.JSONDecodeError,
            ValueError,
        ) as exception:
            logger.warning(
                "Unable to load translation file for %s: %s",
                lang_code,
                exception,
            )

    _translations = loaded_translations


def clear_translation_cache() -> None:
    """Clear cached dictionaries and reload them from disk on demand."""
    global _translations

    _load_translation_dictionary.clear()
    _translations = {}


# Preload translations on module import. Streamlit's cache prevents
# repeated disk I/O when this function is invoked during reruns.
load_translations()


class _EscapedValue:
    """Wrapper that HTML-escapes a value *after* its format spec is applied.

    The previous implementation escaped values by calling ``html.escape(str(v))``
    before substitution. That coerced every value to ``str``, so a translation
    carrying a numeric format spec — ``"{ai_a:.1%}"``, which all four locale
    files use — raised ``ValueError: Unknown format code '%' for object of
    type 'str'``.

    Deferring the escape to ``__format__`` lets ``str.format`` apply the spec to
    the original object first, so ``{ai_a:.1%}`` still renders as ``85.0%`` and
    only the resulting text is escaped.
    """

    __slots__ = ("_value",)

    def __init__(self, value: Any) -> None:
        self._value = value

    def __format__(self, format_spec: str) -> str:
        return html.escape(format(self._value, format_spec))

    def __str__(self) -> str:
        return html.escape(str(self._value))

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"_EscapedValue({self._value!r})"


def format_text(
    template: str,
    escape_html: bool = True,
    **kwargs: Any,
) -> str:
    """Substitute ``kwargs`` into ``template``, degrading instead of raising.

    Args:
        template: A ``str.format``-style template, typically from ``get_text``.
        escape_html: When True (the default, preserving existing behaviour),
            each substituted value is HTML-escaped after its format spec is
            applied. Set False only for sinks that must receive raw text and
            will never interpret entities -- for example a PDF report cell or
            a CSV field, where ``&amp;`` would be shown literally.
        **kwargs: Values to substitute.

    Returns:
        The formatted string, or the unmodified template if substitution fails.

    Notes:
        A translation file is data, not code: a missing placeholder, a stray
        brace or a spec that does not apply to the supplied value must not take
        down the page. Such failures are logged and the raw template is
        returned so the UI stays usable.
    """
    if not kwargs:
        return template

    values: Dict[str, Any]
    if escape_html:
        values = {name: _EscapedValue(value) for name, value in kwargs.items()}
    else:
        values = dict(kwargs)

    try:
        return template.format(**values)
    except (KeyError, IndexError, ValueError, TypeError, AttributeError) as exception:
        logger.warning(
            "Unable to format translation template %r with keys %s: %s",
            template,
            sorted(kwargs),
            exception,
        )
        return template


def get_text(
    key: str,
    lang: str = "en",
    escape_html: bool = True,
    **kwargs: Any,
) -> str:
    """Return translated text with English and key fallbacks.

    Args:
        key: Translation key to look up.
        lang: Language code. Falls back to English, then to the key itself.
        escape_html: Forwarded to :func:`format_text`. See its docstring for
            when to enable it.
        **kwargs: Values substituted into the translated template.

    Returns:
        The translated and formatted string.
    """
    if not _translations:
        load_translations()

    language_dictionary = _translations.get(lang)
    if not language_dictionary:
        language_dictionary = _translations.get("en", {})

    text = language_dictionary.get(
        key,
        _translations.get("en", {}).get(key, key),
    )

    return format_text(text, escape_html=escape_html, **kwargs)
