"""Unit tests for API Key Management Service."""

import pytest

from src.api_gateway.api_keys import APIKeyService, hash_api_key


@pytest.fixture
def service():
    return APIKeyService()


def test_create_and_validate_key(service):
    record, raw_key = service.create_key("test-key", rate_limit=50)

    assert record.name == "test-key"
    assert record.key_hash == hash_api_key(raw_key)
    assert record.is_active is True
    assert record.rate_limit == 50

    # Valid key lookup succeeds
    validated = service.validate_key(raw_key)
    assert validated is not None
    assert validated.id == record.id
    assert validated.last_used_at is not None


def test_invalid_key_rejected(service):
    service.create_key("test-key")

    assert service.validate_key("invalid_key_12345") is None
    assert service.validate_key("") is None


def test_revoked_key_rejected(service):
    record, raw_key = service.create_key("test-key")

    # Revoke key
    assert service.revoke_key(record.id) is True
    assert record.is_active is False

    # Validating revoked key fails
    assert service.validate_key(raw_key) is None

    # Revoking already revoked key returns False
    assert service.revoke_key(record.id) is False


def test_rotation_invalidates_old_key(service):
    old_record, old_raw_key = service.create_key("prod-key")

    # Rotate key
    rotate_result = service.rotate_key(old_record.id)
    assert rotate_result is not None
    new_record, new_raw_key = rotate_result

    assert old_raw_key != new_raw_key
    assert service.validate_key(old_raw_key) is None
    assert service.validate_key(new_raw_key) is not None
    assert service.validate_key(new_raw_key).id == new_record.id
