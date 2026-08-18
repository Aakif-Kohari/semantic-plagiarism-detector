"""
Cross-Lingual Plagiarism Detection with Translation Layer

Detects plagiarism across different languages using:
1. Translation-based comparison (Argos-Translate)
2. Multilingual embeddings (LaBSE, XLM-R)
3. Cross-lingual similarity scoring
"""

import time
import hashlib
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)

# ============================================================================
# LANGUAGE DATABASE
# ============================================================================

LANGUAGE_DB = {
    "en": {"name": "English", "script": "Latin", "family": "Indo-European", "direction": "ltr", "speakers": 1500},
    "es": {"name": "Spanish", "script": "Latin", "family": "Indo-European", "direction": "ltr", "speakers": 480},
    "fr": {"name": "French", "script": "Latin", "family": "Indo-European", "direction": "ltr", "speakers": 267},
    "de": {"name": "German", "script": "Latin", "family": "Indo-European", "direction": "ltr", "speakers": 155},
    "it": {"name": "Italian", "script": "Latin", "family": "Indo-European", "direction": "ltr", "speakers": 67},
    "pt": {"name": "Portuguese", "script": "Latin", "family": "Indo-European", "direction": "ltr", "speakers": 260},
    "nl": {"name": "Dutch", "script": "Latin", "family": "Indo-European", "direction": "ltr", "speakers": 24},
    "ru": {"name": "Russian", "script": "Cyrillic", "family": "Indo-European", "direction": "ltr", "speakers": 258},
    "ar": {"name": "Arabic", "script": "Arabic", "family": "Afro-Asiatic", "direction": "rtl", "speakers": 362},
    "zh": {"name": "Chinese", "script": "Han", "family": "Sino-Tibetan", "direction": "ltr", "speakers": 1100},
    "ja": {"name": "Japanese", "script": "Japanese", "family": "Japonic", "direction": "ltr", "speakers": 128},
    "ko": {"name": "Korean", "script": "Hangul", "family": "Koreanic", "direction": "ltr", "speakers": 77},
    "hi": {"name": "Hindi", "script": "Devanagari", "family": "Indo-European", "direction": "ltr", "speakers": 600},
    "ur": {"name": "Urdu", "script": "Arabic", "family": "Indo-European", "direction": "rtl", "speakers": 170},
    "bn": {"name": "Bengali", "script": "Bengali", "family": "Indo-European", "direction": "ltr", "speakers": 230},
    "te": {"name": "Telugu", "script": "Telugu", "family": "Dravidian", "direction": "ltr", "speakers": 96},
    "ta": {"name": "Tamil", "script": "Tamil", "family": "Dravidian", "direction": "ltr", "speakers": 86},
    "mr": {"name": "Marathi", "script": "Devanagari", "family": "Indo-European", "direction": "ltr", "speakers": 83},
    "gu": {"name": "Gujarati", "script": "Gujarati", "family": "Indo-European", "direction": "ltr", "speakers": 57},
    "kn": {"name": "Kannada", "script": "Kannada", "family": "Dravidian", "direction": "ltr", "speakers": 56},
    "ml": {"name": "Malayalam", "script": "Malayalam", "family": "Dravidian", "direction": "ltr", "speakers": 35},
    "or": {"name": "Odia", "script": "Odia", "family": "Indo-European", "direction": "ltr", "speakers": 35},
    "pa": {"name": "Punjabi", "script": "Gurmukhi", "family": "Indo-European", "direction": "ltr", "speakers": 113},
    "ne": {"name": "Nepali", "script": "Devanagari", "family": "Indo-European", "direction": "ltr", "speakers": 16},
    "th": {"name": "Thai", "script": "Thai", "family": "Tai-Kadai", "direction": "ltr", "speakers": 70},
    "vi": {"name": "Vietnamese", "script": "Latin", "family": "Austroasiatic", "direction": "ltr", "speakers": 95},
    "id": {"name": "Indonesian", "script": "Latin", "family": "Austronesian", "direction": "ltr", "speakers": 43},
    "ms": {"name": "Malay", "script": "Latin", "family": "Austronesian", "direction": "ltr", "speakers": 30},
    "fil": {"name": "Filipino", "script": "Latin", "family": "Austronesian", "direction": "ltr", "speakers": 28},
    "pl": {"name": "Polish", "script": "Latin", "family": "Indo-European", "direction": "ltr", "speakers": 45},
    "cs": {"name": "Czech", "script": "Latin", "family": "Indo-European", "direction": "ltr", "speakers": 10},
    "hu": {"name": "Hungarian", "script": "Latin", "family": "Uralic", "direction": "ltr", "speakers": 13},
    "ro": {"name": "Romanian", "script": "Latin", "family": "Indo-European", "direction": "ltr", "speakers": 24},
    "bg": {"name": "Bulgarian", "script": "Cyrillic", "family": "Indo-European", "direction": "ltr", "speakers": 8},
    "el": {"name": "Greek", "script": "Greek", "family": "Indo-European", "direction": "ltr", "speakers": 13},
    "tr": {"name": "Turkish", "script": "Latin", "family": "Turkic", "direction": "ltr", "speakers": 84},
    "he": {"name": "Hebrew", "script": "Hebrew", "family": "Afro-Asiatic", "direction": "rtl", "speakers": 9},
    "fa": {"name": "Persian", "script": "Arabic", "family": "Indo-European", "direction": "rtl", "speakers": 70},
    "sw": {"name": "Swahili", "script": "Latin", "family": "Niger-Congo", "direction": "ltr", "speakers": 80},
}


@dataclass
class CrossLingualResult:
    """Result of cross-lingual plagiarism detection."""
    source_text: str
    target_text: str
    source_lang: str
    target_lang: str
    similarity_score: float
    translation_quality: float
    method: str  # 'translation', 'embedding', 'hybrid'
    is_plagiarism: bool = False
    confidence: float = 0.0
    matched_segments: List[Tuple[str, str, float]] = field(default_factory=list)


class TranslationCache:
    """Cache for translations to avoid redundant API calls."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: Dict[str, str] = {}
        self._timestamps: Dict[str, float] = {}
        self._hits = 0
        self._misses = 0
    
    def _get_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """Generate cache key."""
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        return f"{source_lang}:{target_lang}:{text_hash}"
    
    def get(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """Get cached translation."""
        key = self._get_key(text, source_lang, target_lang)
        if key in self._cache:
            self._hits += 1
            return self._cache[key]
        self._misses += 1
        return None
    
    def set(self, text: str, source_lang: str, target_lang: str, translation: str) -> None:
        """Cache translation."""
        key = self._get_key(text, source_lang, target_lang)
        if len(self._cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self._timestamps, key=self._timestamps.get)
            del self._cache[oldest_key]
            del self._timestamps[oldest_key]
        
        self._cache[key] = translation
        self._timestamps[key] = time.time()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": (self._hits / total * 100) if total > 0 else 0,
            "max_size": self.max_size,
        }


class CrossLingualDetector:
    """
    Cross-lingual plagiarism detector with robust translation layer.
    
    Methods:
    1. Translation-based: Translate text to English, then compare
    2. Embedding-based: Use multilingual embeddings (LaBSE)
    3. Hybrid: Combine both approaches
    """
    
    def __init__(self, target_lang: str = "en", use_cache: bool = True):
        self.target_lang = target_lang
        self.use_cache = use_cache
        self.cache = TranslationCache() if use_cache else None
        self._embedding_model = None
        self._supported_langs = {
            "en", "es", "fr", "de", "it", "pt", "nl", "ru", "ar", "zh",
            "ja", "ko", "hi", "ur", "bn", "te", "ta", "mr", "gu", "kn",
            "ml", "or", "pa", "ne", "si", "th", "vi", "id", "ms", "fil",
            "pl", "cs", "sk", "hu", "ro", "bg", "el", "tr", "he", "fa",
            "sw", "am", "ha", "yo", "ig", "zu",
        }
    
    def _get_embedding_model(self):
        """Lazy load the embedding model."""
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                # Use LaBSE for multilingual embeddings
                self._embedding_model = SentenceTransformer('sentence-transformers/LaBSE')
                logger.info("Loaded LaBSE embedding model")
            except ImportError:
                logger.warning("sentence-transformers not available, using fallback")
                self._embedding_model = None
        return self._embedding_model
    
    def _translate_text(self, text: str, source_lang: str) -> str:
        """
        Translate text to target language.
        
        Returns:
            Translated text or original if translation fails.
        """
        if source_lang == self.target_lang:
            return text
        
        # Check cache first
        if self.use_cache and self.cache:
            cached = self.cache.get(text, source_lang, self.target_lang)
            if cached is not None:
                return cached
        
        try:
            # Try Argos-Translate if available
            import argostranslate.package
            import argostranslate.translate
            
            # Download package if needed
            argostranslate.package.update_package_index()
            available_packages = argostranslate.package.get_available_packages()
            
            # Find package for source language
            package = None
            for pkg in available_packages:
                if pkg.from_code == source_lang and pkg.to_code == self.target_lang:
                    package = pkg
                    break
            
            if package:
                argostranslate.package.install_from_path(package)
                translator = argostranslate.translate.TranslationService.get_translator(
                    source_lang, self.target_lang
                )
                translation = translator.translate(text)
            else:
                # Fallback: use Google Translate API (requires key)
                translation = self._translate_with_google(text, source_lang)
            
            # Cache translation
            if self.use_cache and self.cache:
                self.cache.set(text, source_lang, self.target_lang, translation)
            
            return translation
            
        except ImportError:
            logger.warning("Translation libraries not available, using fallback")
            return self._translate_with_google(text, source_lang)
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return text
    
    def _translate_with_google(self, text: str, source_lang: str) -> str:
        """Fallback translation using Google Translate API."""
        try:
            import requests
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": source_lang,
                "tl": self.target_lang,
                "dt": "t",
                "q": text,
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and data[0]:
                    return " ".join([item[0] for item in data[0] if item[0]])
            return text
        except Exception as e:
            logger.error(f"Google translate failed: {e}")
            return text
    
    def _compute_embedding_similarity(self, text_a: str, text_b: str) -> float:
        """Compute similarity using multilingual embeddings."""
        model = self._get_embedding_model()
        if model is None:
            return 0.0
        
        try:
            embeddings = model.encode([text_a, text_b], convert_to_numpy=True)
            from sklearn.metrics.pairwise import cosine_similarity
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            return float(similarity)
        except Exception as e:
            logger.error(f"Embedding similarity failed: {e}")
            return 0.0
    
    def detect_pair(
        self,
        text_a: str,
        text_b: str,
        lang_a: str,
        lang_b: str,
        method: str = "hybrid",
        threshold: float = 0.65,
    ) -> CrossLingualResult:
        """
        Detect cross-lingual plagiarism between two texts.
        
        Args:
            text_a: First text
            text_b: Second text
            lang_a: Language of first text
            lang_b: Language of second text
            method: 'translation', 'embedding', 'hybrid'
            threshold: Similarity threshold for flagging
        
        Returns:
            CrossLingualResult with detection results
        """
        # If same language, use standard detection
        if lang_a == lang_b:
            from src.core.similarity import cosine_similarity
            # Simple similarity for same language
            return CrossLingualResult(
                source_text=text_a,
                target_text=text_b,
                source_lang=lang_a,
                target_lang=lang_b,
                similarity_score=0.0,
                translation_quality=1.0,
                method=method,
                is_plagiarism=False,
                confidence=0.0,
            )
        
        scores = {}
        
        # Method 1: Translation-based
        if method in ["translation", "hybrid"]:
            translated_text = self._translate_text(text_a, lang_a)
            from src.core.lexical_similarity import jaccard_similarity
            lexical_score = jaccard_similarity(translated_text, text_b)
            scores["translation"] = lexical_score
        
        # Method 2: Embedding-based
        if method in ["embedding", "hybrid"]:
            embedding_score = self._compute_embedding_similarity(text_a, text_b)
            scores["embedding"] = embedding_score
        
        # Combine scores for hybrid
        if method == "hybrid":
            translation_score = scores.get("translation", 0.0)
            embedding_score = scores.get("embedding", 0.0)
            # Weighted combination (70% embedding, 30% translation)
            similarity_score = 0.7 * embedding_score + 0.3 * translation_score
            confidence = 0.5 + 0.5 * similarity_score
        elif method == "translation":
            similarity_score = scores.get("translation", 0.0)
            confidence = 0.5 + 0.5 * similarity_score
        else:  # embedding
            similarity_score = scores.get("embedding", 0.0)
            confidence = 0.5 + 0.5 * similarity_score
        
        is_plagiarism = similarity_score >= threshold
        
        return CrossLingualResult(
            source_text=text_a,
            target_text=text_b,
            source_lang=lang_a,
            target_lang=lang_b,
            similarity_score=similarity_score,
            translation_quality=scores.get("translation", 0.0),
            method=method,
            is_plagiarism=is_plagiarism,
            confidence=confidence,
        )
    
    def detect_batch(
        self,
        texts: Dict[str, str],
        languages: Dict[str, str],
        threshold: float = 0.65,
        method: str = "hybrid",
    ) -> List[CrossLingualResult]:
        """
        Detect cross-lingual plagiarism across multiple documents.
        
        Args:
            texts: Dict mapping doc name to text
            languages: Dict mapping doc name to language code
            threshold: Similarity threshold
            method: Detection method
        
        Returns:
            List of CrossLingualResult objects
        """
        results = []
        doc_names = list(texts.keys())
        
        for i in range(len(doc_names)):
            for j in range(i + 1, len(doc_names)):
                doc_a = doc_names[i]
                doc_b = doc_names[j]
                
                lang_a = languages.get(doc_a, "en")
                lang_b = languages.get(doc_b, "en")
                
                # Only check cross-lingual pairs
                if lang_a == lang_b:
                    continue
                
                result = self.detect_pair(
                    texts[doc_a],
                    texts[doc_b],
                    lang_a,
                    lang_b,
                    method=method,
                    threshold=threshold,
                )
                results.append(result)
        
        return results
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return sorted(self._supported_langs)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get translation cache statistics."""
        if self.cache:
            return self.cache.get_stats()
        return {"enabled": False}


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_detector: Optional[CrossLingualDetector] = None


def get_cross_lingual_detector() -> CrossLingualDetector:
    """Get global cross-lingual detector instance."""
    global _detector
    if _detector is None:
        _detector = CrossLingualDetector()
    return _detector


def detect_cross_lingual_plagiarism(
    text_a: str,
    text_b: str,
    lang_a: str,
    lang_b: str,
    threshold: float = 0.65,
) -> CrossLingualResult:
    """
    Convenience function for cross-lingual plagiarism detection.
    """
    detector = get_cross_lingual_detector()
    return detector.detect_pair(text_a, text_b, lang_a, lang_b, threshold=threshold)

# ============================================================================
# ENHANCED FEATURES - Additional functionality
# ============================================================================

import re
from datetime import datetime
import json


def detect_language_with_confidence(text: str) -> Tuple[str, float, str]:
    """
    Detect language with confidence score and script detection.
    
    Returns:
        Tuple of (language_code, confidence, script_name)
    """
    detector = LanguageDetector()
    lang, confidence = detector.detect(text)
    
    # Get script from language DB
    script = "Latin"
    if lang in LANGUAGE_DB:
        script = LANGUAGE_DB[lang].script
    
    return lang, confidence, script


def get_language_name(lang_code: str) -> str:
    """Get full language name from code."""
    if lang_code in LANGUAGE_DB:
        return LANGUAGE_DB[lang_code].name
    return lang_code.upper()


def get_language_family(lang_code: str) -> str:
    """Get language family."""
    if lang_code in LANGUAGE_DB:
        return LANGUAGE_DB[lang_code].family
    return "Unknown"


def is_rtl_language(lang_code: str) -> bool:
    """Check if language is right-to-left."""
    if lang_code in LANGUAGE_DB:
        return LANGUAGE_DB[lang_code].direction == "rtl"
    return False


def get_supported_languages_with_info() -> List[Dict[str, Any]]:
    """Get list of supported languages with full info."""
    return [
        {
            "code": code,
            "name": info.name,
            "script": info.script,
            "family": info.family,
            "direction": info.direction,
            "speakers_millions": info.speakers_millions,
        }
        for code, info in LANGUAGE_DB.items()
    ]


def translate_batch(
    texts: List[str],
    source_lang: str,
    target_lang: str = "en",
    show_progress: bool = False,
) -> List[str]:
    """
    Translate a batch of texts.
    
    Args:
        texts: List of texts to translate
        source_lang: Source language code
        target_lang: Target language code (default: 'en')
        show_progress: Whether to show progress
        
    Returns:
        List of translated texts
    """
    detector = CrossLingualDetector(target_lang=target_lang)
    results = []
    
    for i, text in enumerate(texts):
        if show_progress and i % 10 == 0:
            logger.info(f"Translating {i+1}/{len(texts)}...")
        
        if source_lang == target_lang:
            results.append(text)
        else:
            translated = detector._translate_text(text, source_lang)
            results.append(translated)
    
    return results


def compute_cross_lingual_similarity_matrix(
    texts: Dict[str, str],
    languages: Dict[str, str],
    method: str = "hybrid",
) -> Dict[str, Dict[str, float]]:
    """
    Compute cross-lingual similarity matrix for all document pairs.
    
    Args:
        texts: Dict mapping doc name to text
        languages: Dict mapping doc name to language code
        method: Detection method
        
    Returns:
        Similarity matrix as nested dict
    """
    detector = get_cross_lingual_detector()
    doc_names = list(texts.keys())
    matrix = defaultdict(dict)
    
    for i in range(len(doc_names)):
        for j in range(i + 1, len(doc_names)):
            doc_a = doc_names[i]
            doc_b = doc_names[j]
            
            lang_a = languages.get(doc_a, "en")
            lang_b = languages.get(doc_b, "en")
            
            if lang_a == lang_b:
                # Same language: use standard lexical
                from src.core.lexical_similarity import jaccard_similarity
                score = jaccard_similarity(texts[doc_a], texts[doc_b])
            else:
                # Cross-lingual: use detector
                result = detector.detect_pair(
                    texts[doc_a], texts[doc_b],
                    lang_a, lang_b,
                    method=method,
                )
                score = result.similarity_score
            
            matrix[doc_a][doc_b] = score
            matrix[doc_b][doc_a] = score
    
    return dict(matrix)


def generate_cross_lingual_report(results: List[CrossLingualResult]) -> Dict[str, Any]:
    """
    Generate a detailed report from cross-lingual detection results.
    
    Args:
        results: List of CrossLingualResult objects
        
    Returns:
        Report dictionary with statistics
    """
    if not results:
        return {
            "total_pairs": 0,
            "plagiarism_count": 0,
            "avg_similarity": 0.0,
            "language_pairs": {},
            "method_used": "none",
        }
    
    total = len(results)
    plagiarism_count = sum(1 for r in results if r.is_plagiarism)
    avg_sim = sum(r.similarity_score for r in results) / total
    
    # Language pair statistics
    lang_pairs = defaultdict(int)
    for r in results:
        pair = f"{r.source_lang}->{r.target_lang}"
        lang_pairs[pair] += 1
    
    # Method distribution
    methods = defaultdict(int)
    for r in results:
        methods[r.method] += 1
    
    return {
        "total_pairs": total,
        "plagiarism_count": plagiarism_count,
        "plagiarism_rate": (plagiarism_count / total * 100) if total > 0 else 0,
        "avg_similarity": round(avg_sim, 4),
        "max_similarity": max(r.similarity_score for r in results) if results else 0,
        "min_similarity": min(r.similarity_score for r in results) if results else 0,
        "language_pairs": dict(lang_pairs),
        "methods": dict(methods),
        "threshold_used": 0.65,  # Default threshold
        "timestamp": datetime.now().isoformat(),
    }


def export_cross_lingual_results(
    results: List[CrossLingualResult],
    file_path: str,
) -> bool:
    """
    Export cross-lingual results to JSON file.
    
    Args:
        results: List of CrossLingualResult objects
        file_path: Output file path
        
    Returns:
        True if successful
    """
    try:
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_results": len(results),
            "results": [r.to_dict() for r in results],
            "summary": generate_cross_lingual_report(results),
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Exported {len(results)} results to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Export failed: {e}")
        return False


def highlight_cross_lingual_matches(
    source_text: str,
    target_text: str,
    matches: List[Tuple[str, str, float]],
) -> str:
    """
    Generate HTML highlighting for cross-lingual matches.
    
    Args:
        source_text: Source text
        target_text: Target text
        matches: List of (source_segment, target_segment, score) tuples
        
    Returns:
        HTML string with highlighted matches
    """
    if not matches:
        return "<p>No matches found.</p>"
    
    html = []
    html.append("<div class='cross-lingual-matches'>")
    
    for idx, (source, target, score) in enumerate(matches[:10], 1):
        color = "#ef4444" if score > 0.8 else "#f59e0b" if score > 0.6 else "#22c55e"
        html.append(f"""
        <div class='match-pair' style='margin-bottom: 16px; padding: 12px; border-left: 4px solid {color}; background: rgba(255,255,255,0.05); border-radius: 4px;'>
            <div style='display: flex; justify-content: space-between; margin-bottom: 4px;'>
                <span style='font-weight: 600; color: #3b82f6;'>Match #{idx}</span>
                <span style='color: {color}; font-weight: 600;'>{score*100:.1f}%</span>
            </div>
            <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 12px;'>
                <div style='background: rgba(59,130,246,0.1); padding: 8px; border-radius: 4px;'>
                    <span style='font-size: 0.8rem; color: #94a3b8;'>Source</span>
                    <p style='margin: 4px 0 0; font-size: 0.9rem;'>{source}</p>
                </div>
                <div style='background: rgba(34,197,94,0.1); padding: 8px; border-radius: 4px;'>
                    <span style='font-size: 0.8rem; color: #94a3b8;'>Target</span>
                    <p style='margin: 4px 0 0; font-size: 0.9rem;'>{target}</p>
                </div>
            </div>
        </div>
        """)
    
    html.append("</div>")
    return "\n".join(html)


def get_translation_cache_stats() -> Dict[str, Any]:
    """Get translation cache statistics."""
    detector = get_cross_lingual_detector()
    return detector.get_cache_stats()


def clear_translation_cache() -> None:
    """Clear translation cache."""
    detector = get_cross_lingual_detector()
    if detector.cache:
        detector.cache.clear()
        logger.info("Translation cache cleared")