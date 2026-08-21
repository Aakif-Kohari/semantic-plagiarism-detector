"""FAISS Semantic Vector Domain Model.

Defines data structures for document vector embeddings, FAISS index configurations,
k-NN similarity query parameters, and vector search match records.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class VectorDocumentChunk:
    """Represents a chunked document text vector embedding for FAISS index insertion."""

    chunk_id: str
    document_id: str
    document_title: str
    chunk_index: int
    raw_text: str
    embedding_vector: List[float] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class VectorSearchMatch:
    """Represents a similarity search result returned from FAISS vector search."""

    match_id: str
    query_chunk_id: str
    matched_chunk_id: str
    matched_document_title: str
    matched_text_snippet: str
    cosine_similarity_score: float  # Range: 0.0 - 1.0
    l2_distance: float
    rank_position: int
    search_timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class FaissIndexTelemetry:
    """Telemetry metrics for the FAISS vector database index state."""

    index_id: str
    total_vectors_indexed: int
    vector_dimensions: int
    metric_type: str  # 'METRIC_INNER_PRODUCT' or 'METRIC_L2'
    index_type: str  # 'IndexFlatIP', 'IndexIVFFlat', 'IndexHNSWFlat'
    is_trained: bool
    memory_usage_mb: float
    last_updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class VectorSearchAuditReport:
    """Audit report aggregating vector similarity query execution metrics."""

    query_id: str
    query_text: str
    top_k_requested: int
    execution_time_ms: float
    total_matches_found: int
    highest_similarity_ratio: float
    matches: List[VectorSearchMatch] = field(default_factory=list)
