"""
src/utils/json_export.py
------------------------
Utility for exporting similarity matrices into a clean JSON format.
"""

import json
import math
from typing import Dict, List, Union

import pandas as pd


def export_similarity_matrix_to_json(df: Union[pd.DataFrame, None]) -> str:
    """
    Serializes a similarity matrix DataFrame into a clean JSON string.

    Format:
    [
      {
        "document_1": "doc_a",
        "document_2": "doc_b",
        "similarity_score": 0.92
      }
    ]

    Includes only unique document pairs (upper triangle of the symmetric matrix, j > i).
    Handles empty, single-document, NaN, and Unicode filename values.

    Args:
        df: Symmetric similarity DataFrame (doc × doc) or None.

    Returns:
        str: JSON formatted string representation of the unique similarity pairs.
    """
    if df is None or df.empty:
        return "[]"

    doc_names = df.columns.tolist()
    n = len(doc_names)
    pairs: List[Dict[str, Union[str, float]]] = []

    for i in range(n):
        for j in range(i + 1, n):
            score = df.iloc[i, j]
            # Handle NaN values
            if pd.isna(score) or (isinstance(score, float) and math.isnan(score)):
                score_val = 0.0
            else:
                score_val = round(float(score), 4)

            pairs.append(
                {
                    "document_1": str(doc_names[i]),
                    "document_2": str(doc_names[j]),
                    "similarity_score": score_val,
                }
            )

    return json.dumps(pairs, indent=2, ensure_ascii=False)
