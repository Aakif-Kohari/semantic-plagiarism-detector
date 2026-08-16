"""Unit tests for External Integrations & Connectors."""

import asyncio

from src.api_gateway.connectors.github import GitHubConnector
from src.api_gateway.integrations import IntegrationService


def test_register_and_retrieve_connector():
    service = IntegrationService()
    integration = service.create_integration(
        name="GitHub Integration",
        provider="github",
        credentials={"token": "ghp_1234567890"},
        enabled=True,
    )

    assert integration.provider == "github"
    assert integration.enabled is True

    connector = service.get_connector(integration.id)
    assert connector is not None
    assert isinstance(connector, GitHubConnector)


def test_disabled_integration_cannot_execute():
    async def run():
        service = IntegrationService()
        integration = service.create_integration(
            name="Disabled Slack",
            provider="slack",
            credentials={"bot_token": "xoxb-12345"},
            enabled=False,
        )

        assert service.get_connector(integration.id) is None

        try:
            await service.execute_request(integration.id, "POST", "/chat.postMessage")
            assert False, "Should have raised RuntimeError"
        except RuntimeError as exc:
            assert "disabled" in str(exc)

    asyncio.run(run())


def test_execute_integration_request():
    async def run():
        service = IntegrationService()
        integration = service.create_integration(
            name="GitHub Repo Reader",
            provider="github",
            credentials={"token": "ghp_test_token"},
            enabled=True,
        )

        res = await service.execute_request(
            integration.id, "GET", "/user/repos", params={"type": "owner"}
        )
        assert res["status"] == "success"
        assert res["provider"] == "github"
        assert res["method"] == "GET"
        assert res["path"] == "/user/repos"

    asyncio.run(run())
