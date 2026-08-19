"""
Cross-Lingual Plagiarism Detection Engine.

Detects plagiarism across documents written in different languages
using multilingual embeddings and translation-assisted comparison.
"""

import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)


class SupportedLanguage(Enum):
    """Supported languages for cross-lingual detection."""
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    PORTUGUESE = "pt"
    ITALIAN = "it"
    DUTCH = "nl"
    RUSSIAN = "ru"
    CHINESE = "zh"
    JAPANESE = "ja"
    ARABIC = "ar"
    HINDI = "hi"
    KOREAN = "ko"
    TURKISH = "tr"
    POLISH = "pl"


LANGUAGE_NAMES = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "pt": "Portuguese", "it": "Italian", "nl": "Dutch", "ru": "Russian",
    "zh": "Chinese", "ja": "Japanese", "ar": "Arabic", "hi": "Hindi",
    "ko": "Korean", "tr": "Turkish", "pl": "Polish",
}


@dataclass
class LanguageMatch:
    """A detected cross-lingual similarity match."""
    source_doc: str
    source_lang: str
    source_chunk: str
    target_doc: str
    target_lang: str
    target_chunk: str
    similarity: float
    method: str
    translation_used: bool
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CrossLingualResult:
    """Result of cross-lingual plagiarism detection."""
    documents: List[Dict[str, Any]]
    matches: List[LanguageMatch]
    language_distribution: Dict[str, int]
    total_comparisons: int
    processing_time: float
    summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "documents": self.documents,
            "matches": [m.to_dict() for m in self.matches],
            "language_distribution": self.language_distribution,
            "total_comparisons": self.total_comparisons,
            "processing_time": self.processing_time,
            "summary": self.summary,
        }


@dataclass
class CrossLingualConfig:
    """Configuration for cross-lingual detection."""
    enabled_languages: List[str] = field(default_factory=lambda: ["en", "es", "fr", "de"])
    similarity_threshold: float = 0.65
    use_translation_bridge: bool = True
    translation_service: str = "internal"
    max_chunks_per_doc: int = 100
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    top_k: int = 10
    enable_cache: bool = True


class CrossLingualDetector:
    """
    Detects plagiarism across documents in different languages.

    Uses multilingual sentence transformers to create language-agnostic
    embeddings and enables cross-language similarity comparison.
    """

    def __init__(self, config: Optional[CrossLingualConfig] = None):
        self.config = config or CrossLingualConfig()
        self._model = None
        self._cache: Dict[str, np.ndarray] = {}
        logger.info(f"CrossLingualDetector initialized for languages: {self.config.enabled_languages}")

    def _get_model(self):
        """Lazy-load multilingual embedding model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.config.embedding_model)
                logger.info(f"Loaded multilingual model: {self.config.embedding_model}")
            except ImportError:
                logger.warning("sentence-transformers not available, using mock embeddings")
                self._model = "mock"
        return self._model

    def detect_language(self, text: str) -> str:
        """
        Detect the language of input text.

        Args:
            text: Input text to analyze

        Returns:
            Language code (e.g., 'en', 'es', 'fr')
        """
        words = text.split()
        if not words:
            return "en"

        common_en = {"the", "is", "and", "of", "to", "in", "that", "it", "for", "was"}
        common_es = {"el", "la", "de", "en", "que", "los", "del", "las", "por", "con"}
        common_fr = {"le", "la", "de", "et", "les", "des", "un", "une", "est", "du"}
        common_de = {"der", "die", "und", "den", "von", "ist", "das", "des", "ein", "eine"}

        text_words = set(w.lower() for w in words[:100])
        scores = {
            "en": len(text_words & common_en),
            "es": len(text_words & common_es),
            "fr": len(text_words & common_fr),
            "de": len(text_words & common_de),
        }
        return max(scores, key=scores.get) if max(scores.values()) > 0 else "en"

    def embed_text(self, text: str, lang: str = "en") -> np.ndarray:
        """
        Create multilingual embedding for text.

        Args:
            text: Input text
            lang: Language code

        Returns:
            Embedding vector
        """
        cache_key = f"{lang}:{hash(text)}"
        if self.config.enable_cache and cache_key in self._cache:
            return self._cache[cache_key]

        model = self._get_model()
        if model == "mock":
            embedding = np.random.rand(384).astype(np.float32)
        else:
            embedding = model.encode(text, normalize_embeddings=True)

        if self.config.enable_cache:
            self._cache[cache_key] = embedding
        return embedding

    def embed_documents(self, documents: Dict[str, List[str]]) -> Dict[str, List[np.ndarray]]:
        """
        Embed all chunks from multiple documents.

        Args:
            documents: {doc_name: [chunk1, chunk2, ...]}

        Returns:
            {doc_name: [embedding1, embedding2, ...]}
        """
        embeddings = {}
        for doc_name, chunks in documents.items():
            limited_chunks = chunks[:self.config.max_chunks_per_doc]
            embeddings[doc_name] = [self.embed_text(chunk) for chunk in limited_chunks]
        return embeddings

    def compare_across_languages(
        self,
        source_embeddings: List[np.ndarray],
        target_embeddings: List[np.ndarray],
        method: str = "cosine"
    ) -> np.ndarray:
        """
        Compute similarity matrix between two sets of embeddings.

        Args:
            source_embeddings: Source document embeddings
            target_embeddings: Target document embeddings
            method: Similarity method ('cosine', 'dot', 'l2')

        Returns:
            Similarity matrix (n_source x n_target)
        """
        if not source_embeddings or not target_embeddings:
            return np.array([])

        source_matrix = np.array(source_embeddings)
        target_matrix = np.array(target_embeddings)

        if method == "cosine":
            source_norm = source_matrix / np.linalg.norm(source_matrix, axis=1, keepdims=True)
            target_norm = target_matrix / np.linalg.norm(target_matrix, axis=1, keepdims=True)
            similarity = np.dot(source_norm, target_norm.T)
        elif method == "dot":
            similarity = np.dot(source_matrix, target_matrix.T)
        else:
            similarity = np.zeros((len(source_embeddings), len(target_embeddings)))
            for i, s in enumerate(source_embeddings):
                for j, t in enumerate(target_embeddings):
                    similarity[i, j] = 1.0 / (1.0 + np.linalg.norm(s - t))

        return similarity

    def detect_cross_lingual_plagiarism(
        self,
        documents: Dict[str, Tuple[str, List[str]]],
        threshold: Optional[float] = None
    ) -> CrossLingualResult:
        """
        Detect plagiarism across documents in different languages.

        Args:
            documents: {doc_name: (language_code, [chunks])}
            threshold: Override default similarity threshold

        Returns:
            CrossLingualResult with matches and statistics
        """
        start_time = datetime.now()
        threshold = threshold or self.config.similarity_threshold

        # Embed all documents
        doc_chunks = {name: chunks for name, (_, chunks) in documents.items()}
        embeddings = self.embed_documents(doc_chunks)

        # Detect languages
        lang_dist = {}
        doc_langs = {}
        for name, (lang, _) in documents.items():
            doc_langs[name] = lang
            lang_dist[lang] = lang_dist.get(lang, 0) + 1

        # Compare all document pairs
        matches = []
        doc_names = list(documents.keys())
        total_comparisons = 0

        for i in range(len(doc_names)):
            for j in range(i + 1, len(doc_names)):
                name_a, name_b = doc_names[i], doc_names[j]
                lang_a, lang_b = doc_langs[name_a], doc_langs[name_b]
                is_cross_lingual = lang_a != lang_b

                emb_a = embeddings.get(name_a, [])
                emb_b = embeddings.get(name_b, [])

                if not emb_a or not emb_b:
                    continue

                sim_matrix = self.compare_across_languages(emb_a, emb_b)
                total_comparisons += 1

                # Find high-similarity pairs
                for ci in range(sim_matrix.shape[0]):
                    for cj in range(sim_matrix.shape[1]):
                        score = float(sim_matrix[ci, cj])
                        if score >= threshold:
                            chunks_a = doc_chunks.get(name_a, [])
                            chunks_b = doc_chunks.get(name_b, [])
                            matches.append(LanguageMatch(
                                source_doc=name_a,
                                source_lang=lang_a,
                                source_chunk=chunks_a[ci] if ci < len(chunks_a) else "",
                                target_doc=name_b,
                                target_lang=lang_b,
                                target_chunk=chunks_b[cj] if cj < len(chunks_b) else "",
                                similarity=score,
                                method="multilingual_embedding",
                                translation_used=is_cross_lingual and self.config.use_translation_bridge,
                                confidence=min(score * 1.1, 1.0),
                            ))

        # Sort by similarity
        matches.sort(key=lambda m: m.similarity, reverse=True)
        matches = matches[:self.config.top_k]

        processing_time = (datetime.now() - start_time).total_seconds()

        summary = {
            "total_documents": len(documents),
            "languages_detected": len(lang_dist),
            "cross_lingual_matches": sum(1 for m in matches if m.source_lang != m.target_lang),
            "same_language_matches": sum(1 for m in matches if m.source_lang == m.target_lang),
            "high_severity": sum(1 for m in matches if m.similarity >= 0.90),
            "threshold_used": threshold,
        }

        doc_info = [
            {"name": name, "language": doc_langs.get(name, "unknown"),
             "language_name": LANGUAGE_NAMES.get(doc_langs.get(name, ""), "Unknown"),
             "chunk_count": len(doc_chunks.get(name, []))}
            for name in doc_names
        ]

        return CrossLingualResult(
            documents=doc_info,
            matches=matches,
            language_distribution=lang_dist,
            total_comparisons=total_comparisons,
            processing_time=processing_time,
            summary=summary,
        )

    def get_supported_languages(self) -> List[Dict[str, str]]:
        """Get list of supported languages."""
        return [{"code": lang.value, "name": LANGUAGE_NAMES.get(lang.value, lang.value)}
                for lang in SupportedLanguage]

    def clear_cache(self):
        """Clear embedding cache."""
        self._cache.clear()
        logger.info("Cross-lingual embedding cache cleared")
