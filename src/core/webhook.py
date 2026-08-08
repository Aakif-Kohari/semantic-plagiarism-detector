from __future__ import annotations

"""
Webhook notification delivery with transient-failure retries and HMAC signatures.

Provides secure webhook delivery with:
- Cryptographic HMAC-SHA256 signatures for payload authenticity
- Transient-failure retries with exponential backoff
- SSRF protection for outbound URLs
- Configurable timeouts and retry policies

Recent Additions (Issue #1373):
- Added HMAC-SHA256 signature generation for outgoing webhooks
- Added X-Plagiarism-Signature header (t=timestamp,v1=signature)
- Added verify_webhook_signature() helper for receivers to validate payloads
"""

import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any, Optional

import requests
from dotenv import load_dotenv
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from src.security.ssrf_protector import (
    SSRFProtector,
    SSRFSecurityException,
)

logger = logging.getLogger(__name__)

load_dotenv()

WEBHOOK_TIMEOUT_SECONDS = 10
WEBHOOK_MAX_ATTEMPTS = 3
WEBHOOK_RETRY_MIN_SECONDS = 1
WEBHOOK_RETRY_MAX_SECONDS = 4

_RETRYABLE_STATUS_CODES = {
    408,
    425,
    429,
    500,
    502,
    503,
    504,
}


def _is_retryable_request_error(exception: BaseException) -> bool:
    """Return whether a webhook request error is temporary.

    Connection errors and timeouts are considered transient. HTTP responses
    are retried only for throttling, request timeout, and common server-side
    failures. Permanent client errors such as 400 or 401 are not retried.
    """
    if isinstance(
        exception,
        (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ),
    ):
        return True

    if isinstance(exception, requests.exceptions.HTTPError):
        response = exception.response
        return response is not None and response.status_code in _RETRYABLE_STATUS_CODES

    return False


def _log_retry(retry_state: RetryCallState) -> None:
    """Log a webhook retry without exposing the payload or secret URL."""
    exception = retry_state.outcome.exception()
    wait_seconds = retry_state.next_action.sleep

    logger.warning(
        "Webhook attempt %s/%s failed with %s. Retrying in %.1f seconds.",
        retry_state.attempt_number,
        WEBHOOK_MAX_ATTEMPTS,
        exception,
        wait_seconds,
    )


def compute_webhook_signature(
    payload_bytes: bytes,
    secret_key: str,
    timestamp: Optional[int] = None,
) -> str:
    """
    Compute HMAC-SHA256 signature for webhook payload authentication.

    Generates a cryptographic signature that receivers can use to verify
    the authenticity and integrity of webhook payloads. The signature is
    computed over the raw payload bytes using the shared secret key.

    Args:
        payload_bytes: The raw bytes of the webhook payload (JSON encoded).
        secret_key: The shared secret key used for HMAC computation.
        timestamp: Optional Unix timestamp to include in signature.
                   If None, current time is used.

    Returns:
        Hexadecimal string of the HMAC-SHA256 signature.

    Examples:
        >>> payload = json.dumps({"text": "alert"}).encode()
        >>> sig = compute_webhook_signature(payload, "my_secret_key")
        >>> print(sig)
        'a1b2c3d4e5f6...'
    """
    if not secret_key:
        logger.warning("compute_webhook_signature: No secret key provided")
        return ""

    if timestamp is None:
        timestamp = int(time.time())

    # Create the signed payload: timestamp + payload
    # This prevents replay attacks by binding signature to specific time
    signed_content = f"{timestamp}.".encode("utf-8") + payload_bytes

    signature = hmac.new(
        secret_key.encode("utf-8"),
        signed_content,
        hashlib.sha256,
    ).hexdigest()

    return signature


def verify_webhook_signature(
    payload_bytes: bytes,
    signature: str,
    secret_key: str,
    timestamp: Optional[int] = None,
    max_age_seconds: int = 300,
) -> bool:
    """
    Verify the authenticity of a webhook payload using HMAC-SHA256.

    Recomputes the signature using the provided secret key and compares
    it with the received signature using constant-time comparison to
    prevent timing attacks.

    Args:
        payload_bytes: The raw bytes of the received webhook payload.
        signature: The signature string to verify (hex format).
        secret_key: The shared secret key used for verification.
        timestamp: The timestamp from the webhook header. If None,
                   timestamp validation is skipped.
        max_age_seconds: Maximum allowed age of the webhook in seconds.
                         Defaults to 300 (5 minutes).

    Returns:
        True if signature is valid and timestamp is within acceptable range,
        False otherwise.

    Examples:
        >>> payload = json.dumps({"text": "alert"}).encode()
        >>> sig = compute_webhook_signature(payload, "secret", timestamp=1234567890)
        >>> verify_webhook_signature(payload, sig, "secret", timestamp=1234567890)
        True
    """
    if not secret_key or not signature:
        logger.warning("verify_webhook_signature: Missing secret key or signature")
        return False

    # Validate timestamp to prevent replay attacks
    if timestamp is not None:
        current_time = int(time.time())
        age = abs(current_time - timestamp)

        if age > max_age_seconds:
            logger.warning(
                "verify_webhook_signature: Timestamp too old (%d seconds). "
                "Max allowed: %d seconds.",
                age,
                max_age_seconds,
            )
            return False

    # Recompute the expected signature
    expected_signature = compute_webhook_signature(
        payload_bytes,
        secret_key,
        timestamp=timestamp,
    )

    if not expected_signature:
        return False

    # Use constant-time comparison to prevent timing attacks
    # hmac.compare_digest is designed for this purpose
    is_valid = hmac.compare_digest(
        expected_signature.encode("utf-8"),
        signature.encode("utf-8"),
    )

    if not is_valid:
        logger.warning("verify_webhook_signature: Signature mismatch detected")

    return is_valid


_attempt_counter = 0


@retry(
    retry=retry_if_exception(_is_retryable_request_error),
    stop=stop_after_attempt(WEBHOOK_MAX_ATTEMPTS),
    wait=wait_exponential(
        multiplier=1,
        min=WEBHOOK_RETRY_MIN_SECONDS,
        max=WEBHOOK_RETRY_MAX_SECONDS,
    ),
    before_sleep=_log_retry,
    reraise=True,
)
def _post_webhook(
    webhook_url: str,
    payload: dict[str, Any],
) -> requests.Response:
    """POST one webhook attempt with HMAC signature header.

    Tenacity retries this function for transient request failures only.
    Adds X-Plagiarism-Signature header for payload authentication.
    """
    global _attempt_counter
    _attempt_counter += 1

    # Serialize payload to JSON bytes for signature computation
    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")

    # Get secret key from environment
    secret_key = os.getenv("WEBHOOK_SECRET_KEY", "")

    # Generate timestamp and signature
    timestamp = int(time.time())
    signature = compute_webhook_signature(payload_bytes, secret_key, timestamp)

    # Construct signature header: t=timestamp,v1=signature
    signature_header = f"t={timestamp},v1={signature}" if signature else ""

    headers = {
        "Content-Type": "application/json",
    }

    # Only add signature header if we have a valid signature
    if signature_header:
        headers["X-Plagiarism-Signature"] = signature_header

    response = requests.post(
        webhook_url,
        json=payload,
        headers=headers,
        timeout=WEBHOOK_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response


def send_plagiarism_alert(
    doc_a: str,
    doc_b: str,
    similarity: float,
) -> tuple[bool, int]:
    """Send a plagiarism alert to the configured webhook with retry logic.

    The webhook URL is validated once before any outbound request. Temporary
    connection failures, timeouts, rate limiting, and selected 5xx responses
    (500, 502, 503, 504) are retried up to 3 times with exponential backoff.

    Args:
        doc_a: Name of the first student document.
        doc_b: Name of the second student document.
        similarity: Cosine similarity score between 0.0 and 1.0.

    Returns:
        A tuple of `(success, total_attempts)` where `success` is a boolean
        indicating delivery success, and `total_attempts` is the total number
        of HTTP delivery attempts made.
    """
    global _attempt_counter
    _attempt_counter = 0

    webhook_url = os.getenv("PLAGIARISM_WEBHOOK_URL")

    if not webhook_url:
        logger.warning("PLAGIARISM_WEBHOOK_URL is not configured in the environment.")
        return False, 0

    base_url = os.getenv(
        "APP_BASE_URL",
        "http://localhost:8501",
    ).rstrip("/")
    similarity_percent = similarity * 100

    message = (
        "🚨 *Plagiarism Alert!* "
        f"Student document *{doc_a}* matches *{doc_b}* by "
        f"*{similarity_percent:.1f}%*.\n"
        f"Review details here: {base_url}"
    )
    payload = {
        "text": message,
        "content": message,
    }

    try:
        # Validate once. Retrying cannot make an unsafe URL safe.
        SSRFProtector.validate_webhook_url(webhook_url)
    except SSRFSecurityException as exception:
        logger.error(
            "SECURITY BLOCKED: Webhook failed SSRF validation: %s",
            exception,
        )
        return False, 0

    try:
        _post_webhook(webhook_url, payload)
        attempts = _attempt_counter
    except requests.exceptions.RequestException as exception:
        attempts = _attempt_counter
        logger.error(
            "Failed to send webhook notification for pair %s <-> %s "
            "after %s attempt(s): %s",
            doc_a,
            doc_b,
            attempts,
            exception,
        )
        return False, attempts

    logger.info(
        "Webhook alert successfully sent for pair %s <-> %s (%.1f%%) after %s attempt(s).",
        doc_a,
        doc_b,
        similarity_percent,
        attempts,
    )
    return True, attempts


# Alias or main function for dispatching plagiarism alerts
def dispatch_plagiarism_alert(
    doc_a: str,
    doc_b: str,
    similarity: float,
    webhook_url: str | None = None,
) -> bool:
    """Dispatch a plagiarism alert payload to the configured webhook endpoint."""
    return send_plagiarism_alert(doc_a=doc_a, doc_b=doc_b, similarity=similarity)
