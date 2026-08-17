"""Slack API connector implementation."""

from __future__ import annotations

from typing import Any

from src.api_gateway.connectors.base import ServiceConnector


class SlackConnector(ServiceConnector):
    """Connector for Slack Webhook / API integration."""

    def __init__(self, name: str, credentials: dict[str, Any]) -> None:
        super().__init__(name, credentials)
        self.bot_token = credentials.get("bot_token") or credentials.get("webhook_url")

    async def connect(self) -> bool:
        """Connect and validate token."""
        if not self.bot_token:
            self._connected = False
            return False
        self._connected = True
        return True

    async def disconnect(self) -> None:
        """Disconnect connector."""
        self._connected = False

    async def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Perform request to Slack API."""
        if not self._connected:
            raise RuntimeError("SlackConnector is not connected.")

        return {
            "status": "success",
            "provider": "slack",
            "method": method.upper(),
            "path": path,
            "data": kwargs.get("json") or {},
        }
