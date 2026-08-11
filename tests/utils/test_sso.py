from unittest.mock import patch
import pytest

from src.utils.sso import (
    exchange_github_code,
    exchange_google_code,
    get_github_auth_url,
    get_google_auth_url,
)


def test_get_google_auth_url_missing_client_id(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    with pytest.raises(ValueError, match="GOOGLE_CLIENT_ID environment variable is not configured"):
        get_google_auth_url()


def test_get_google_auth_url_success(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "dummy_google_client_id")
    url, state = get_google_auth_url()
    assert "dummy_google_client_id" in url
    assert state.startswith("google_")


def test_exchange_google_code_missing_client_id(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "dummy_secret")
    with pytest.raises(ValueError, match="GOOGLE_CLIENT_ID environment variable is not configured"):
        exchange_google_code("dummy_code")


def test_exchange_google_code_missing_client_secret(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "dummy_client_id")
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    with pytest.raises(ValueError, match="GOOGLE_CLIENT_SECRET environment variable is not configured"):
        exchange_google_code("dummy_code")


@patch("src.utils.sso.requests.get")
@patch("src.utils.sso.requests.post")
def test_exchange_google_code_success(mock_post, mock_get, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "dummy_client_id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "dummy_secret")

    mock_post.return_value.ok = True
    mock_post.return_value.json.return_value = {"access_token": "google_token_123"}

    mock_get.return_value.ok = True
    mock_get.return_value.json.return_value = {"email": "user@example.com", "name": "Test User"}

    result = exchange_google_code("valid_code")
    assert result == {"email": "user@example.com", "name": "Test User"}
    mock_post.assert_called_once()
    mock_get.assert_called_once()


def test_get_github_auth_url_missing_client_id(monkeypatch):
    monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
    with pytest.raises(ValueError, match="GITHUB_CLIENT_ID environment variable is not configured"):
        get_github_auth_url()


def test_get_github_auth_url_success(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "dummy_github_client_id")
    url, state = get_github_auth_url()
    assert "dummy_github_client_id" in url
    assert state.startswith("github_")


def test_exchange_github_code_missing_client_id(monkeypatch):
    monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "dummy_secret")
    with pytest.raises(ValueError, match="GITHUB_CLIENT_ID environment variable is not configured"):
        exchange_github_code("dummy_code")


def test_exchange_github_code_missing_client_secret(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "dummy_client_id")
    monkeypatch.delenv("GITHUB_CLIENT_SECRET", raising=False)
    with pytest.raises(ValueError, match="GITHUB_CLIENT_SECRET environment variable is not configured"):
        exchange_github_code("dummy_code")


@patch("src.utils.sso.requests.get")
@patch("src.utils.sso.requests.post")
def test_exchange_github_code_success(mock_post, mock_get, monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "dummy_client_id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "dummy_secret")

    mock_post.return_value.ok = True
    mock_post.return_value.json.return_value = {"access_token": "github_token_123"}

    mock_get.return_value.ok = True
    mock_get.return_value.json.return_value = {"login": "octocat", "email": "octocat@github.com"}

    result = exchange_github_code("valid_code")
    assert result == {"login": "octocat", "email": "octocat@github.com"}
    mock_post.assert_called_once()
    mock_get.assert_called_once()
