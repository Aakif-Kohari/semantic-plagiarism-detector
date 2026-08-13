"""
tests/core/test_webhook.py
--------------------------
Unit tests for webhook delivery, retry logic, HMAC signatures, and thread safety.
"""

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.core.webhook import (
    _thread_local,
    compute_webhook_signature,
    send_plagiarism_alert,
    verify_webhook_signature,
)

WEBHOOK_URL = "https://mock-webhook.url"


def make_response(status_code: int) -> MagicMock:
    response = MagicMock(spec=requests.Response)
    response.status_code = status_code

    if status_code >= 400:
        response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            f"{status_code} response",
            response=response,
        )

    return response


@pytest.fixture(autouse=True)
def disable_retry_wait(monkeypatch):
    """Keep retry tests immediate while retaining production backoff."""
    from src.core import webhook

    monkeypatch.setattr(
        webhook._post_webhook.retry,
        "sleep",
        lambda _seconds: None,
    )


@pytest.fixture(autouse=True)
def reset_thread_local():
    """Ensure thread-local storage is clean before and after each test."""
    if hasattr(_thread_local, "attempt_counter"):
        del _thread_local.attempt_counter
    yield
    if hasattr(_thread_local, "attempt_counter"):
        del _thread_local.attempt_counter


@patch.dict(os.environ, {}, clear=True)
def test_send_plagiarism_alert_no_url():
    success, attempts = send_plagiarism_alert("DocA", "DocB", 0.95)
    assert success is False
    assert attempts == 0


@patch.dict(
    os.environ,
    {
        "PLAGIARISM_WEBHOOK_URL": WEBHOOK_URL,
        "APP_BASE_URL": "http://test-dashboard",
    },
)
@patch("src.core.webhook.SSRFProtector.validate_webhook_url")
@patch("src.core.webhook.requests.post")
def test_send_plagiarism_alert_success(
    mock_post,
    mock_validate_url,
):
    mock_post.return_value = make_response(200)

    success, attempts = send_plagiarism_alert(
        "student_essay.pdf",
        "wikipedia_source.pdf",
        0.925,
    )

    assert success is True
    assert attempts == 1
    mock_validate_url.assert_called_once_with(WEBHOOK_URL)
    mock_post.assert_called_once()


@patch.dict(
    os.environ,
    {"PLAGIARISM_WEBHOOK_URL": WEBHOOK_URL},
)
@patch("src.core.webhook.SSRFProtector.validate_webhook_url")
@patch("src.core.webhook.requests.post")
def test_connection_error_retries_three_times(
    mock_post,
    mock_validate_url,
):
    mock_post.side_effect = requests.exceptions.ConnectionError("Connection timed out")

    success, attempts = send_plagiarism_alert("DocA", "DocB", 0.99)

    assert success is False
    assert attempts == 3
    assert mock_post.call_count == 3


class TestWebhookThreadSafety:
    """Test suite for thread-safe attempt counting (Issue #1994)."""

    @patch.dict(os.environ, {"PLAGIARISM_WEBHOOK_URL": WEBHOOK_URL})
    @patch("src.core.webhook.SSRFProtector.validate_webhook_url")
    @patch("src.core.webhook.requests.post")
    def test_concurrent_webhook_sends_do_not_share_counters(
        self, mock_post, mock_validate_url
    ):
        """Verify that concurrent webhook deliveries maintain isolated attempt counters.

        This test simulates multiple background tasks dispatching webhooks
        simultaneously. Each thread should track its own retry attempts
        without clobbering the counters of other threads.
        """

        # Configure mock to fail twice then succeed (3 attempts total per thread)
        def side_effect(*args, **kwargs):
            # Use a thread-local counter inside the mock to simulate per-thread failures
            if not hasattr(side_effect, "thread_counts"):
                side_effect.thread_counts = threading.local()

            if not hasattr(side_effect.thread_counts, "count"):
                side_effect.thread_counts.count = 0

            side_effect.thread_counts.count += 1

            if side_effect.thread_counts.count < 3:
                raise requests.exceptions.ConnectionError("Simulated timeout")

            return make_response(200)

        mock_post.side_effect = side_effect

        results = []

        def worker(worker_id):
            success, attempts = send_plagiarism_alert(
                f"DocA_{worker_id}", f"DocB_{worker_id}", 0.90
            )
            results.append((worker_id, success, attempts))

        # Run 5 concurrent webhook deliveries
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, i) for i in range(5)]
            for f in futures:
                f.result()

        # Verify each thread saw exactly 3 attempts (2 failures + 1 success)
        assert len(results) == 5
        for worker_id, success, attempts in results:
            assert success is True, f"Worker {worker_id} failed"
            assert (
                attempts == 3
            ), f"Worker {worker_id} saw {attempts} attempts instead of 3"

    @patch.dict(os.environ, {"PLAGIARISM_WEBHOOK_URL": WEBHOOK_URL})
    @patch("src.core.webhook.SSRFProtector.validate_webhook_url")
    @patch("src.core.webhook.requests.post")
    def test_sequential_sends_reset_counter(self, mock_post, mock_validate_url):
        """Verify that sequential sends in the same thread reset the counter."""
        mock_post.return_value = make_response(200)

        success1, attempts1 = send_plagiarism_alert("DocA", "DocB", 0.90)
        success2, attempts2 = send_plagiarism_alert("DocC", "DocD", 0.85)

        assert success1 is True
        assert attempts1 == 1

        assert success2 is True
        assert attempts2 == 1  # Should be 1, not 2 (counter was reset)


class TestHMACSignatures:
    """Test suite for HMAC signature generation and verification."""

    def test_compute_signature_deterministic(self):
        payload = b'{"test": "data"}'
        sig1 = compute_webhook_signature(payload, "secret", timestamp=1000)
        sig2 = compute_webhook_signature(payload, "secret", timestamp=1000)
        assert sig1 == sig2

    def test_verify_signature_valid(self):
        payload = b'{"alert": "test"}'
        secret = "my_secret"
        timestamp = int(time.time())

        signature = compute_webhook_signature(payload, secret, timestamp=timestamp)
        assert (
            verify_webhook_signature(payload, signature, secret, timestamp=timestamp)
            is True
        )

    def test_verify_signature_invalid(self):
        payload = b'{"alert": "test"}'
        assert (
            verify_webhook_signature(
                payload, "wrong_sig", "secret", timestamp=int(time.time())
            )
            is False
        )
