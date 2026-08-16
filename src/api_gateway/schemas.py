"""Pydantic schemas for API Gateway endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class APIKeyCreateRequest(BaseModel):
    """Schema for creating a new API key."""

    name: str = Field(..., description="Descriptive name for the API key")
    expires_in_days: int | None = Field(
        default=None, description="Optional expiry in days"
    )
    rate_limit: int = Field(
        default=100, description="Requests per minute limit for this key"
    )


class APIKeyCreateResponse(BaseModel):
    """Response returning the raw API key (shown only once)."""

    id: str
    name: str
    raw_key: str
    created_at: datetime
    expires_at: datetime | None = None
    rate_limit: int


class APIKeyMetadataResponse(BaseModel):
    """Metadata response for API key listing."""

    id: str
    name: str
    created_at: datetime
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None
    is_active: bool
    rate_limit: int


class WebhookCreateRequest(BaseModel):
    """Schema for registering a webhook."""

    name: str
    url: str
    event: str
    secret: str | None = None


class WebhookResponse(BaseModel):
    """Response schema for webhook info."""

    id: str
    name: str
    url: str
    event: str
    active: bool
    created_at: datetime
    updated_at: datetime


class WebhookDeliveryResponse(BaseModel):
    """Response schema for webhook delivery history."""

    id: str
    webhook_id: str
    status: str
    response_code: int | None = None
    attempt_count: int
    created_at: datetime
    delivered_at: datetime | None = None
    error_message: str | None = None


class IntegrationCreateRequest(BaseModel):
    """Schema for adding an integration."""

    name: str
    provider: str
    credentials: dict[str, Any]
    enabled: bool = True


class IntegrationResponse(BaseModel):
    """Response schema for integration (credentials masked)."""

    id: str
    name: str
    provider: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class EndpointRegisterRequest(BaseModel):
    """Schema for registering internal functions as API endpoints."""

    method: str
    path: str
    name: str | None = None
    require_api_key: bool = True
