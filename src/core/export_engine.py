"""LMS-compatible incident export generation and safe file writing."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

from src.utils.html_report import generate_html_report

logger = logging.getLogger(__name__)


class LMSExportEngine:
    """Generate LMS-compatible incident exports."""

    @staticmethod
    def generate_incident_html(
        incidents: Sequence[Mapping[str, Any]],
    ) -> str | None:
        """Generate a standardized HTML incident report."""
        if not incidents:
            logger.warning("Attempted to export an empty incident list to HTML.")
            return None

        try:
            return generate_html_report(incidents)
        except Exception as exception:
            logger.error("Failed to format incident data as HTML: %s", exception)
            return None
