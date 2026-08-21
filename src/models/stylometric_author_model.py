"""Stylometric Author Attribution Domain Model.

Defines data structures for sentence length variance, vocabulary richness metrics,
function word frequency distributions, and author attribution match reports.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class StylometricFingerprint:
    """Represents writing style metrics extracted from a document."""

    document_id: str
    author_alias: str
    average_sentence_length: float
    sentence_length_variance: float
    type_token_ratio: float  # Vocabulary richness (unique words / total words)
    hapax_legomena_ratio: float  # Ratio of words occurring only once
    function_word_frequencies: Dict[str, float] = field(default_factory=dict)
    punctuation_density: float = 0.0
    extracted_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class StylometricAuthorMatch:
    """Represents an author attribution comparison between two stylometric fingerprints."""

    match_id: str
    query_document_id: str
    candidate_author_alias: str
    candidate_document_id: str
    stylometric_distance: float  # Euclidean distance between feature vectors
    attribution_confidence_percentage: float  # Range: 0.0 - 100.0%
    is_same_author: bool
    dominant_stylometric_trait: str  # e.g., 'Function Word Overlap', 'Sentence Structure'
    compared_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class StylometricAuditReport:
    """Audit report summary aggregating stylometric author attribution queries."""

    report_id: str
    total_authors_in_corpus: int
    query_document_id: str
    top_attributed_author: str
    highest_confidence_score: float
    report_generated_at: datetime = field(default_factory=datetime.utcnow)
    matches: List[StylometricAuthorMatch] = field(default_factory=list)
