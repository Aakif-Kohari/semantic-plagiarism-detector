"""Adversarial Text Watermark Domain Model.

Defines data classes for statistical z-score watermark tests, green/red list token entropy,
AI-generated text fingerprinting, and audit report summaries.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class WatermarkTokenDistribution:
    """Represents token frequency breakdown across green/red lists."""

    total_tokens_analyzed: int
    green_list_tokens_count: int
    red_list_tokens_count: int
    observed_green_ratio: float  # Range: 0.0 - 1.0
    expected_green_ratio: float  # Default: 0.50 (for gamma = 0.5)
    entropy_score: float


@dataclass
class WatermarkDetectionMatch:
    """Represents a statistical watermark detection result for an analyzed text snippet."""

    detection_id: str
    document_id: str
    document_title: str
    z_score: float  # Standardized statistical test score
    p_value: float  # Probability value for hypothesis testing
    watermark_confidence_percentage: float  # Range: 0.0 - 100.0%
    is_watermark_present: bool
    model_generator_signature: str  # e.g., 'Kirchenbauer-Logits', 'AAR-Entropy', 'None'
    token_distribution: WatermarkTokenDistribution
    analyzed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WatermarkAuditReport:
    """Audit report summary aggregating adversarial watermark detection queries."""

    report_id: str
    total_documents_analyzed: int
    watermarked_documents_count: int
    average_z_score: float
    highest_confidence_score: float
    report_generated_at: datetime = field(default_factory=datetime.utcnow)
    detections: List[WatermarkDetectionMatch] = field(default_factory=list)
