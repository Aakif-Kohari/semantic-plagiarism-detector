"""Base abstract service connector interface for external integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ServiceConnector(ABC):
    """Abstract Base Class for third-party service connectors."""

    def __init__(self, name: str, credentials: dict[str, Any]) -> None:
        self.name = name
        self.credentials = credentials
        self._connected: bool = False

    @property
    def is_connected(self) -> bool:
        """Return True if the connector is connected."""
        return self._connected

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection or validate credentials with the external service."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection with the external service."""
        pass

    @abstractmethod
    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Send HTTP or API request to the third-party service."""
        pass
