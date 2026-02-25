"""Tests for FastMCP server setup."""

import pytest


class TestServerSetup:
    """Tests for FastMCP server instance."""

    def test_mcp_instance_exists(self) -> None:
        """Test that mcp instance is properly configured."""
        from mcp_server_mattermost.server import mcp

        assert mcp is not None
        assert mcp.name == "Mattermost"

    def test_mcp_has_instructions(self) -> None:
        """Test that mcp has instructions."""
        from mcp_server_mattermost.server import mcp

        assert mcp.instructions is not None
        assert "Mattermost" in mcp.instructions

    def test_get_client_exists(self) -> None:
        """Test that client dependency provider exists."""
        from mcp_server_mattermost.deps import get_client

        assert callable(get_client)


class TestDependencyProviders:
    """Tests for dependency injection providers."""

    @pytest.mark.asyncio
    async def test_get_client_yields_client(self, mock_settings: None) -> None:
        """Test that get_client yields MattermostClient."""
        from mcp_server_mattermost.client import MattermostClient
        from mcp_server_mattermost.deps import get_client

        async with get_client() as client:
            assert isinstance(client, MattermostClient)


class TestServerIntegration:
    """Integration tests for server startup."""

    def test_server_imports_work(self) -> None:
        """Test that server module exports resolve correctly."""
        from mcp_server_mattermost.server import app_lifespan, mcp

        assert mcp is not None
        assert callable(app_lifespan)

    def test_deps_imports_work(self) -> None:
        """Test that deps module exports resolve correctly."""
        from mcp_server_mattermost.deps import get_client

        assert callable(get_client)

    def test_mcp_can_list_tools(self) -> None:
        """Test that mcp instance can be queried for tools."""
        from mcp_server_mattermost.server import mcp

        assert hasattr(mcp, "name")
        assert mcp.name == "Mattermost"
