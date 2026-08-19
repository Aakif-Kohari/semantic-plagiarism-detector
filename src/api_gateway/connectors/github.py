"""GitHub API connector implementation."""

from __future__ import annotations

from typing import Any

from src.api_gateway.connectors.base import ServiceConnector


class GitHubConnector(ServiceConnector):
    """Connector for GitHub API integration."""

    def __init__(self, name: str, credentials: dict[str, Any]) -> None:
        super().__init__(name, credentials)
        self.api_token = credentials.get("token") or credentials.get("api_key")
        self.base_url = credentials.get("base_url", "https://api.github.com")

    async def connect(self) -> bool:
        """Connect and validate API token."""
        if not self.api_token:
            self._connected = False
            return False
        self._connected = True
        return True

    async def disconnect(self) -> None:
        """Disconnect connector."""
        self._connected = False

    async def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Perform simulated request to GitHub API."""
        if not self._connected:
            raise RuntimeError("GitHubConnector is not connected.")

        return {
            "status": "success",
            "provider": "github",
            "method": method.upper(),
            "path": path,
            "data": kwargs.get("json") or kwargs.get("params") or {},
        }
