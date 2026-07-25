import os
import time
from unittest.mock import MagicMock, patch

import requests

from src.core.webhook import send_plagiarism_alert
import src.core.webhook as webhook


@patch.dict(os.environ, {}, clear=True)
def test_send_plagiarism_alert_no_url():
    # Verify the function handles a missing PLAGIARISM_WEBHOOK_URL gracefully
    assert send_plagiarism_alert("DocA", "DocB", 0.95) is False


@patch.dict(
    os.environ,
    {
        "PLAGIARISM_WEBHOOK_URL": "https://mock-webhook.url",
        "APP_BASE_URL": "http://test-dashboard",
    },
)
@patch("src.core.webhook.requests.post")
def test_send_plagiarism_alert_success(mock_post):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    # Call the function
    result = send_plagiarism_alert("student_essay.pdf", "wikipedia_source.pdf", 0.925)

    # Assert result and POST details
    assert result is True
    mock_post.assert_called_once()

    args, kwargs = mock_post.call_args
    assert args[0] == "https://mock-webhook.url"

    payload = kwargs["json"]
    assert "text" in payload
    assert "content" in payload
    assert "student_essay.pdf" in payload["text"]
    assert "wikipedia_source.pdf" in payload["text"]
    assert "92.5%" in payload["text"]
    assert "http://test-dashboard" in payload["text"]


@patch.dict(os.environ, {"PLAGIARISM_WEBHOOK_URL": "https://mock-webhook.url"})
@patch("src.core.webhook.requests.post")
def test_send_plagiarism_alert_network_failure(mock_post):
    # Setup mock post to raise RequestException
    mock_post.side_effect = requests.exceptions.ConnectionError("Connection timed out")

    # Call function and verify it returns False instead of raising an exception
    result = send_plagiarism_alert("DocA", "DocB", 0.99)
    assert result is False
    mock_post.assert_called_once()


@patch.dict(os.environ, {"PLAGIARISM_WEBHOOK_URL": "https://mock-webhook.url"})
@patch("src.core.webhook.requests.post")
def test_send_plagiarism_alert_rate_limits_bursts(mock_post):
    webhook._webhook_dispatches.clear()
    mock_post.return_value = MagicMock(status_code=200)

    results = [send_plagiarism_alert("DocA", f"Doc{i}", 0.95) for i in range(6)]

    assert results == [True, True, True, True, True, False]
    assert mock_post.call_count == 5


@patch.dict(os.environ, {"PLAGIARISM_WEBHOOK_URL": "https://mock-webhook.url"})
@patch("src.core.webhook.requests.post")
def test_send_plagiarism_alert_rate_limit_expires(mock_post, monkeypatch):
    webhook._webhook_dispatches.clear()
    mock_post.return_value = MagicMock(status_code=200)
    clock = iter([100.0, 100.0, 100.0, 100.0, 100.0, 161.0])
    monkeypatch.setattr(time, "monotonic", lambda: next(clock))

    for index in range(5):
        assert send_plagiarism_alert("DocA", f"Doc{index}", 0.95) is True
    assert send_plagiarism_alert("DocA", "Doc5", 0.95) is True
