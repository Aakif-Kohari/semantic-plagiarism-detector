import csv
import io
import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class LMSExportEngine:
    """
    Core data pipeline engine for exporting system data into LMS-compatible formats.
    Designed to stream data efficiently using in-memory string buffers to avoid
    high RAM overhead when exporting tens of thousands of incident records.
    """
    
    @staticmethod
    def _calculate_severity(sim_score: float) -> str:
        """Internal helper to classify severity based on numeric score."""
        return "CRITICAL" if sim_score > 0.90 else "HIGH" if sim_score > 0.80 else "MODERATE"
    
    @staticmethod
    def _safe_document_name(value: object) -> str:
        """Return a readable document name for exports."""
        name = str(value or "").strip()
        return name or "Unknown"

    @staticmethod
    def _format_similarity_percent(sim_score: float) -> str:
        """Return a human-readable similarity percentage."""
        return f"{sim_score * 100:.1f}%"

    @staticmethod
    def generate_incident_txt(
        incidents: List[Dict[str, any]],
    ) -> Optional[str]:
        """Generate a readable plain-text summary of flagged incidents.

        Args:
            incidents: Incident dictionaries containing ``doc_a``, ``doc_b``,
                and ``similarity``. Optional fields such as ``matched_length``
                and ``matched_text`` are included when present.

        Returns:
            A UTF-8-compatible plain-text report, or ``None`` when there are
            no incidents to export.
        """
        if not incidents:
            logger.warning(
                "Attempted to export an empty incident list to TXT."
            )
            return None

        try:
            lines = [
                "SEMANTIC PLAGIARISM INCIDENT REPORT",
                "=" * 38,
                f"Total flagged pairs: {len(incidents)}",
                "",
            ]

            for index, row in enumerate(incidents, start=1):
                sim_score = float(row.get("similarity", 0))
                severity = LMSExportEngine._calculate_severity(sim_score)
                doc_a = LMSExportEngine._safe_document_name(
                    row.get("doc_a")
                )
                doc_b = LMSExportEngine._safe_document_name(
                    row.get("doc_b")
                )

                lines.extend(
                    [
                        f"Incident #{index}",
                        "-" * 24,
                        f"Document A: {doc_a}",
                        f"Document B: {doc_b}",
                        (
                            "Similarity: "
                            f"{LMSExportEngine._format_similarity_percent(sim_score)} "
                            f"({sim_score:.4f})"
                        ),
                        f"Severity: {severity}",
                    ]
                )

                matched_length = row.get("matched_length")
                if matched_length not in (None, ""):
                    lines.append(
                        f"Matched length: {matched_length} words"
                    )

                matched_text = str(
                    row.get("matched_text")
                    or row.get("matching_text")
                    or ""
                ).strip()
                if matched_text:
                    lines.extend(
                        [
                            "Matching text:",
                            matched_text,
                        ]
                    )

                lines.append("")

            lines.extend(
                [
                    "=" * 38,
                    "End of report",
                    "",
                ]
            )

            txt_data = "\n".join(lines)
            logger.info(
                "Successfully generated TXT export for %s incidents.",
                len(incidents),
            )
            return txt_data
        except (TypeError, ValueError) as exc:
            logger.error(
                "Failed to format incident data as TXT: %s",
                exc,
            )
            return None

    @staticmethod
    def generate_incident_csv(incidents: List[Dict[str, any]]) -> Optional[str]:
        """
        Generates a standardized CSV string representing flagged incidents.
        
        Args:
            incidents: A list of dictionaries containing at least:
                       'doc_a', 'doc_b', and 'similarity'
        Returns:
            A raw CSV formatted string ready for file writing or web download.
        """
        if not incidents:
            logger.warning("Attempted to export an empty incident list to CSV.")
            return None
            
        try:
            output = io.StringIO()
            # Define the exact column schema required for LMS integration
            fieldnames = ['Document A', 'Document B', 'Similarity Score', 'Severity Flag']
            
            writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator='\\n')
            writer.writeheader()
            
            for row in incidents:
                sim_score = float(row.get("similarity", 0))
                severity = LMSExportEngine._calculate_severity(sim_score)
                
                writer.writerow({
                    'Document A': row.get("doc_a", "Unknown"),
                    'Document B': row.get("doc_b", "Unknown"),
                    'Similarity Score': f"{sim_score:.4f}",
                    'Severity Flag': severity
                })
                
            csv_data = output.getvalue()
            output.close()
            logger.info(f"Successfully generated LMS CSV export for {len(incidents)} incidents.")
            return csv_data
            
        except Exception as e:
            logger.error(f"Failed to stream incident data to CSV: {e}")
            return None

    @staticmethod
    def generate_incident_json(incidents: List[Dict[str, any]]) -> Optional[str]:
        """
        Generates a standardized JSON payload representing flagged incidents.
        Useful for REST API integrations with modern LMS platforms (Canvas, Blackboard).
        
        Args:
            incidents: A list of dictionaries containing incident data.
        Returns:
            A raw JSON formatted string.
        """
        if not incidents:
            logger.warning("Attempted to export an empty incident list to JSON.")
            return None
            
        try:
            payload = {
                "metadata": {
                    "total_incidents": len(incidents),
                    "export_format": "LMS_JSON_v1"
                },
                "incidents": []
            }
            
            for row in incidents:
                sim_score = float(row.get("similarity", 0))
                severity = LMSExportEngine._calculate_severity(sim_score)
                
                payload["incidents"].append({
                    "document_a": row.get("doc_a", "Unknown"),
                    "document_b": row.get("doc_b", "Unknown"),
                    "similarity_score": round(sim_score, 4),
                    "severity_flag": severity
                })
                
            json_data = json.dumps(payload, indent=2)
            logger.info(f"Successfully generated LMS JSON payload for {len(incidents)} incidents.")
            return json_data
            
        except Exception as e:
            logger.error(f"Failed to serialize incident data to JSON: {e}")
            return None
