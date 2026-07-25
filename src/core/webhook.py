"""
webhook.py
----------
Utility to dispatch notifications to a Slack or Discord webhook channel
when high-similarity plagiarism incidents (>= 90%) are detected.
"""

import logging
import os

import requests
from dotenv import load_dotenv
from src.security.ssrf_protector import SSRFProtector, SSRFSecurityException

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables from .env
load_dotenv()


def send_plagiarism_alert(doc_a: str, doc_b: str, similarity: float) -> bool:
    """
    Send an alert to the configured PLAGIARISM_WEBHOOK_URL when high-similarity matches occur.

    Args:
        doc_a: Name of the first student document.
        doc_b: Name of the second student document.
        similarity: Cosine similarity score (between 0.0 and 1.0).

    Returns:
        bool: True if the alert was successfully sent, False otherwise.
    """
    webhook_url = os.getenv("PLAGIARISM_WEBHOOK_URL")

    if not webhook_url:
        logger.warning("PLAGIARISM_WEBHOOK_URL is not configured in the environment.")
        return False

    # Get base URL of the Streamlit dashboard for the review link
    base_url = os.getenv("APP_BASE_URL", "http://localhost:8501").rstrip("/")

    # Format similarity percentage
    sim_percent = similarity * 100

    # Construct the message payload
    message = (
        f"🚨 *Plagiarism Alert!* Student document *{doc_a}* matches *{doc_b}* by *{sim_percent:.1f}%*.\n"
        f"Review details here: {base_url}"
    )

    # Webhook payload compatible with both Slack (expects 'text') and Discord (expects 'content')
    payload = {"text": message, "content": message}

    try:
        # Prevent Server-Side Request Forgery (Issue #301)
        SSRFProtector.validate_webhook_url(webhook_url)
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        # Check if request returned an unsuccessful status code (4xx, 5xx)
        response.raise_for_status()
        logger.info(
            f"Webhook alert successfully sent for pair: {doc_a} <-> {doc_b} ({sim_percent:.1f}%)"
        )
        return True
    except SSRFSecurityException as e:
        logger.error(f"SECURITY BLOCKED: Webhook {webhook_url} failed SSRF validation: {e}")
        return False
    except requests.exceptions.RequestException as e:
        # Gracefully handle all network / request failures so indexing is not blocked
        logger.error(
            f"Failed to send webhook notification for pair: {doc_a} <-> {doc_b}. Error: {e}"
        )
        return False
