import csv
import io
import json
import logging
import zipfile
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np

import pandas as pd

from src.core.similarity import find_most_similar_chunks
from src.utils.pdf_report import generate_plagiarism_report

logger = logging.getLogger(__name__)

# Standard column headers for the incident CSV export
_CSV_HEADERS = [
    "Incident ID",
    "Doc A",
    "Doc B",
    "Similarity",
    "Severity",
    "Status",
    "Date",
]


def export_incidents_csv_stream(incidents_list: List[Dict]) -> bytes:
    """Stream a list of incident dicts into a CSV-formatted byte stream
    encoded with **utf-8-sig** (UTF-8 with BOM) for Excel compatibility.

    The function writes the following columns in order:

    * **Incident ID** – ``incident_id`` field (default: empty string)
    * **Doc A**       – ``document_a`` field
    * **Doc B**       – ``document_b`` field
    * **Similarity**  – ``similarity_score`` formatted as a percentage (e.g. ``95.00%``)
    * **Severity**    – ``severity_rank`` field
    * **Status**      – ``review_status`` field
    * **Date**        – ``date_flagged`` field

    Parameters
    ----------
    incidents_list:
        A list of incident dictionaries, as returned by
        :func:`~src.db.incidents.get_all_incidents`.

    Returns
    -------
    bytes
        UTF-8-SIG encoded CSV byte stream (includes UTF-8 BOM) ready for
        direct use with Streamlit download buttons or file writing, ensuring
        Excel on Windows opens the file with correct character encoding.

    Examples
    --------
    >>> csv_bytes = export_incidents_csv_stream(incidents)
    >>> assert csv_bytes.startswith(b"\\xef\\xbb\\xbf")  # UTF-8 BOM
    """
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=_CSV_HEADERS,
        extrasaction="ignore",
        lineterminator="\r\n",
    )
    writer.writeheader()

    for incident in incidents_list:
        raw_score = incident.get("similarity_score", 0.0)
        try:
            similarity_str = f"{float(raw_score):.2%}"
        except (TypeError, ValueError):
            similarity_str = str(raw_score)

        writer.writerow(
            {
                "Incident ID": incident.get("incident_id", ""),
                "Doc A": incident.get("document_a", ""),
                "Doc B": incident.get("document_b", ""),
                "Similarity": similarity_str,
                "Severity": incident.get("severity_rank", ""),
                "Status": incident.get("review_status", ""),
                "Date": incident.get("date_flagged", ""),
            }
        )

    csv_text = output.getvalue()
    return csv_text.encode("utf-8-sig")


def _sanitise_filename(name: str) -> str:
    """Strip non-alphanumeric characters (except ``-``, ``_``) for safe filenames."""
    return (
        "".join(c for c in name if c.isalnum() or c in ("-", "_")).rstrip() or "unnamed"
    )


def generate_bulk_reports_zip(
    flags: List[Dict],
    *,
    chunked_docs: Optional[Dict[str, List[str]]] = None,
    embeddings: Optional[Dict[str, "np.ndarray"]] = None,
    include_pdf: bool = True,
    include_csv: bool = True,
    include_json: bool = True,
) -> bytes:
    """Generate a ZIP file containing selected artefacts for flagged document pairs.

    Parameters
    ----------
    flags:
        List of flag dicts returned by :func:`~src.core.similarity.flag_plagiarism`.
        Each dict must contain ``doc_a``, ``doc_b``, ``similarity`` and
        ``threshold_at_time_of_flag``.
    chunked_docs:
        Optional mapping of document name → list of text chunks.
    embeddings:
        Optional mapping of document name → NumPy embedding array.
    include_pdf:
        Whether to generate per‑pair PDF reports.
    include_csv:
        Whether to include a summary CSV of all flagged pairs.
    include_json:
        Whether to include a metadata JSON file describing the export.

    Returns
    -------
    bytes
        In‑memory ZIP file contents.
    """

    memory_file = io.BytesIO()
    csv_rows = []  # collect rows for optional CSV

    with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, flag in enumerate(flags):
            doc_a = flag.get("doc_a", f"doc_A_{idx}")
            doc_b = flag.get("doc_b", f"doc_B_{idx}")
            score = float(flag.get("similarity", 0.0))
            threshold = float(flag.get("threshold_at_time_of_flag", 0.5))

            # Gather CSV row data early
            csv_rows.append(
                {
                    "doc_a": doc_a,
                    "doc_b": doc_b,
                    "similarity_score": score,
                    "threshold_at_time_of_flag": threshold,
                }
            )

            # Attempt to enrich the report with top matching chunk pairs
            top_pairs = []
            if (
                chunked_docs
                and embeddings
                and doc_a in chunked_docs
                and doc_b in chunked_docs
            ):
                try:
                    emb_a = embeddings[doc_a]
                    emb_b = embeddings[doc_b]
                    top_pairs = find_most_similar_chunks(
                        chunked_docs[doc_a],
                        chunked_docs[doc_b],
                        emb_a,
                        emb_b,
                        top_k=3,
                        threshold=threshold,
                    )
                except Exception as exc:
                    logger.debug(
                        "Could not compute chunk pairs for %s ↔ %s: %s",
                        doc_a,
                        doc_b,
                        exc,
                    )

            if include_pdf:
                try:
                    pdf_buffer = generate_plagiarism_report(
                        doc_a=doc_a,
                        doc_b=doc_b,
                        overall_similarity=score,
                        threshold=threshold,
                        top_pairs=top_pairs,
                        report_title=f"Plagiarism Report: {doc_a} vs {doc_b}",
                    )
                    safe_a = _sanitise_filename(doc_a)
                    safe_b = _sanitise_filename(doc_b)
                    pdf_filename = f"report_{safe_a}_{safe_b}.pdf"
                    zf.writestr(pdf_filename, pdf_buffer.getvalue())
                except Exception as exc:
                    logger.error(
                        "Failed to generate PDF for %s ↔ %s: %s", doc_a, doc_b, exc
                    )
                    # Fallback JSON per‑pair if PDF generation fails
                    safe_a = _sanitise_filename(doc_a)
                    safe_b = _sanitise_filename(doc_b)
                    fallback = {
                        "generated_at": datetime.now().isoformat(),
                        "document_a": doc_a,
                        "document_b": doc_b,
                        "similarity_score": score,
                        "threshold": threshold,
                        "note": "PDF generation failed; JSON fallback provided.",
                    }
                    zf.writestr(
                        f"report_{safe_a}_{safe_b}.json", json.dumps(fallback, indent=2)
                    )

        # Optional CSV summary
        if include_csv:
            try:
                df = pd.DataFrame(csv_rows)
                csv_bytes = df.to_csv(index=False).encode("utf-8")
                zf.writestr("summary.csv", csv_bytes)
            except Exception as exc:
                logger.warning("Failed to generate CSV summary: %s", exc)

        # Optional JSON metadata
        if include_json:
            try:
                metadata = {
                    "generated_at": datetime.now().isoformat(),
                    "flags": flags,
                }
                zf.writestr("metadata.json", json.dumps(metadata, indent=2))
            except Exception as exc:
                logger.warning("Failed to generate JSON metadata: %s", exc)

    return memory_file.getvalue()
