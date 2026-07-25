"""
src/i18n/translator.py
----------------------
Translation dictionary and helper function for UI internationalization
and translation API integration with SQLite caching.
"""

from typing import Optional
from src.db.translation_cache import cache_translation, get_cached_translation

TRANSLATIONS = {
    "en": {
        "title": "Semantic Plagiarism Detector",
        "subtitle": "Advanced NLP & Vector Search Plagiarism Detection System",
        "settings": "Settings",
        "threshold": "Similarity Threshold",
        "upload_title": "📤 Document Upload",
        "analysis_summary": "📊 Analysis Summary",
        "metric_docs": "Total Documents",
        "metric_pairs": "Compared Pairs",
        "metric_flagged": "Flagged Pairs",
        "metric_faiss": "FAISS Vectors",
        "tab_warnings": "🚨 Plagiarism Warnings",
        "tab_matrix": "📈 Similarity Matrix",
        "tab_users": "🔐 Account Settings",
        "download_excel": "📥 Download Excel Matrix",
    },
    "es": {
        "title": "Detector Semántico de Plagio",
        "subtitle": "Sistema Avanzado de Detección de Plagio con NLP y Búsqueda Vectorial",
        "settings": "Configuración",
        "threshold": "Umbral de Similitud",
        "upload_title": "📤 Cargar Documentos",
        "analysis_summary": "📊 Resumen del Análisis",
        "metric_docs": "Documentos Totales",
        "metric_pairs": "Pares Comparados",
        "metric_flagged": "Pares Marcados",
        "metric_faiss": "Vectores FAISS",
        "tab_warnings": "🚨 Advertencias de Plagio",
        "tab_matrix": "📈 Matriz de Similitud",
        "tab_users": "🔐 Configuración de Cuenta",
        "download_excel": "📥 Descargar Matriz en Excel",
    },
}


def get_text(key: str, lang: str = "en") -> str:
    """Retrieve translated UI string for given key and language code."""
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    return lang_dict.get(key, key)


def translate_text(
    text: str, source_lang: str = "auto", target_lang: str = "en"
) -> str:
    """
    Translates foreign text into target language while utilizing SQLite caching.
    
    Checks cache first to save API quota. On cache miss, performs translation 
    and caches the result.
    """
    if not text or not text.strip():
        return text

    # 1. Check SQLite translation cache
    cached_result = get_cached_translation(
        text, source_lang=source_lang, target_lang=target_lang
    )
    if cached_result is not None:
        return cached_result

    # 2. External Translation API call fallback/logic
    # Replace this with your actual external API call if present (e.g. Google/DeepL API)
    translated_text = text

    # 3. Cache the new translation in SQLite
    cache_translation(
        foreign_text=text,
        translated_text=translated_text,
        source_lang=source_lang,
        target_lang=target_lang,
    )

    return translated_text
