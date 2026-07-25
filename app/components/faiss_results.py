"""Sortable FAISS search-result table helpers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd


RESULT_COLUMNS = [
    "Rank",
    "Target Document",
    "Chunk",
    "Similarity Score",
    "Matching Text",
]


def _record_value(record: Any, name: str, default: Any = None) -> Any:
    """Read a field from dataclass-like or mapping-like records."""
    if isinstance(record, dict):
        return record.get(name, default)
    return getattr(record, name, default)


def faiss_results_dataframe(
    results: Iterable[tuple[Any, float]],
    min_similarity: float | None = None,
    max_similarity: float | None = None,
) -> pd.DataFrame:
    """Convert FAISS records into a sortable display DataFrame."""
    rows: list[dict[str, Any]] = []

    RESULT_COLUMNS = [
        "Rank",
        "Target Document",
        "Chunk",
        "Similarity Score",
        "Matching Text",
        "Stats",
    ]

    for record, raw_score in results:
        score = float(raw_score)
        if min_similarity is not None and score < min_similarity:
            continue
        if max_similarity is not None and score > max_similarity:
            continue

        document = str(
            _record_value(record, "doc_name", "Unknown document")
        )
        chunk_index = int(_record_value(record, "chunk_index", 0))
        chunk_text = str(_record_value(record, "chunk_text", ""))

        from src.utils.text_stats import format_text_stats
        
        rows.append(
            {
                "Target Document": document,
                "Chunk": chunk_index + 1,
                "Similarity Score": score,
                "Matching Text": chunk_text,
                "Stats": format_text_stats(chunk_text),
            }
        )

    if not rows:
        return pd.DataFrame(columns=RESULT_COLUMNS)

    dataframe = pd.DataFrame(rows)
    dataframe = dataframe.sort_values(
        by=["Similarity Score", "Target Document", "Chunk"],
        ascending=[False, True, True],
        kind="stable",
    ).reset_index(drop=True)
    dataframe.insert(0, "Rank", range(1, len(dataframe) + 1))

    return dataframe[RESULT_COLUMNS]
