"""Data models for API Gateway, Keys, Webhooks, and Integrations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass
class APIKeyRecord:
    """Record storing metadata and hash for an API Key."""

    id: str
    name: str
    key_hash: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None
    rate_limit: int = 100  # requests per minute

    @property
    def is_active(self) -> bool:
        """Return True if the key is not revoked and not expired."""
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True


@dataclass
class WebhookRecord:
    """Record representing a registered outgoing or incoming webhook."""

    id: str
    name: str
    url: str
    event: str
    secret: str
    active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WebhookDeliveryRecord:
    """Record tracking delivery attempt of a webhook."""

    id: str
    webhook_id: str
    status: str  # "delivered", "failed", "pending"
    response_code: int | None = None
    attempt_count: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    delivered_at: datetime | None = None
    error_message: str | None = None


@dataclass
class IntegrationRecord:
    """Record representing a third-party service integration."""

    id: str
    name: str
    provider: str
    credentials: dict[str, Any]
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ExposedEndpointRecord:
    """Record representing an internal function exposed as an API route."""

    method: str
    path: str
    handler: Callable[..., Any]
    name: str | None = None
    require_api_key: bool = True
