"""Unit tests for RateLimiter."""

import pytest

from src.api_gateway.rate_limiter import RateLimiter


@pytest.fixture
def limiter():
    return RateLimiter(default_limit=3, window_seconds=60)


def test_requests_under_limit_succeed(limiter):
    key = "user_1"
    assert limiter.allow(key) is True
    assert limiter.allow(key) is True
    assert limiter.allow(key) is True


def test_request_over_limit_fails(limiter):
    key = "user_2"
    # Exhaust allowed count of 3
    for _ in range(3):
        assert limiter.allow(key) is True

    # 4th request exceeds limit
    assert limiter.allow(key) is False


def test_separate_keys_have_independent_limits(limiter):
    key_a = "key_a"
    key_b = "key_b"

    # Exhaust key_a
    for _ in range(3):
        limiter.allow(key_a)
    assert limiter.allow(key_a) is False

    # key_b still allowed
    assert limiter.allow(key_b) is True
    assert limiter.allow(key_b) is True
