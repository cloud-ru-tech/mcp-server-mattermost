"""Tests for FastMCP server setup."""

import pytest


class TestServerSetup:
    """Tests for FastMCP server instance."""

    def test_mcp_instance_exists(self, mock_settings: None) -> None:
        """Test that mcp instance is properly configured."""
        from mcp_server_mattermost.server import mcp

        assert mcp is not None
        assert mcp.name == "Mattermost"

    def test_mcp_has_instructions(self, mock_settings: None) -> None:
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

    def test_server_imports_work(self, mock_settings: None) -> None:
        """Test that server module exports resolve correctly."""
        from mcp_server_mattermost.server import app_lifespan, mcp

        assert mcp is not None
        assert callable(app_lifespan)

    def test_deps_imports_work(self) -> None:
        """Test that deps module exports resolve correctly."""
        from mcp_server_mattermost.deps import get_client

        assert callable(get_client)

    @pytest.mark.asyncio
    async def test_filesystem_provider_discovers_all_tools(self, mock_settings: None) -> None:
        """Test that FileSystemProvider auto-discovers all tool modules."""
        from mcp_server_mattermost.server import mcp

        tools = await mcp.list_tools()
        assert len(tools) == 37, f"Expected 37 tools, got {len(tools)}: {[t.name for t in tools]}"


class TestMcpAuth:
    """Tests for conditional auth provider on the FastMCP instance."""

    def test_create_mcp_static_token_no_auth(self, clean_env: None) -> None:
        """static_token mode returns instance with auth=None."""
        import os
        from unittest.mock import patch

        with patch.dict(
            os.environ,
            {
                "MATTERMOST_URL": "http://mm.example.com",
                "MATTERMOST_TOKEN": "test-token",
                "MATTERMOST_AUTH_MODE": "static_token",
            },
        ):
            from mcp_server_mattermost.config import get_settings

            get_settings.cache_clear()
            from mcp_server_mattermost.server import _create_mcp

            instance = _create_mcp()
            assert instance.auth is None
            get_settings.cache_clear()

    def test_create_mcp_client_token_auth(self, clean_env: None) -> None:
        """client_token mode attaches MattermostTokenVerifier."""
        import os
        from unittest.mock import patch

        from mcp_server_mattermost.auth import MattermostTokenVerifier

        with patch.dict(
            os.environ,
            {"MATTERMOST_URL": "http://mm.example.com", "MATTERMOST_AUTH_MODE": "client_token"},
        ):
            from mcp_server_mattermost.config import get_settings

            get_settings.cache_clear()
            from mcp_server_mattermost.server import _create_mcp

            instance = _create_mcp()
            assert isinstance(instance.auth, MattermostTokenVerifier)
            get_settings.cache_clear()

    def test_create_mcp_legacy_allow_http_client_tokens_auth(self, clean_env: None) -> None:
        """Legacy allow_http_client_tokens flag still attaches MattermostTokenVerifier."""
        import os
        from unittest.mock import patch

        from mcp_server_mattermost.auth import MattermostTokenVerifier

        with patch.dict(
            os.environ,
            {"MATTERMOST_URL": "http://mm.example.com", "MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS": "true"},
        ):
            from mcp_server_mattermost.config import get_settings

            get_settings.cache_clear()
            from mcp_server_mattermost.server import _create_mcp

            instance = _create_mcp()
            assert isinstance(instance.auth, MattermostTokenVerifier)
            get_settings.cache_clear()

    @pytest.mark.parametrize("value", ["1", "true", "yes", "on", "t", "y", "TRUE", "On", "YES"])
    def test_create_mcp_legacy_truthy_values(self, clean_env: None, value: str) -> None:
        """All pydantic-compatible legacy truthy values enable auth."""
        import os
        from unittest.mock import patch

        from mcp_server_mattermost.auth import MattermostTokenVerifier
        from mcp_server_mattermost.config import get_settings

        with patch.dict(
            os.environ,
            {"MATTERMOST_URL": "http://mm.example.com", "MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS": value},
        ):
            get_settings.cache_clear()
            from mcp_server_mattermost.server import _create_mcp

            instance = _create_mcp()
            assert isinstance(instance.auth, MattermostTokenVerifier), f"Expected auth for value={value!r}"
            get_settings.cache_clear()

    def test_create_mcp_oauth_proxy_auth(self, clean_env: None) -> None:
        """oauth_proxy mode attaches OAuthProxy."""
        import os
        from unittest.mock import patch

        from fastmcp.server.auth import OAuthProxy

        with patch.dict(
            os.environ,
            {
                "MATTERMOST_URL": "http://mattermost.internal",
                "MATTERMOST_AUTH_MODE": "oauth_proxy",
                "MATTERMOST_OAUTH_CLIENT_TYPE": "public",
                "MATTERMOST_OAUTH_CLIENT_ID": "mm-client",
                "MATTERMOST_OAUTH_JWT_SIGNING_KEY": "signing-key-1234567890",
                "MATTERMOST_OAUTH_MCP_PUBLIC_URL": "http://localhost:8000",
                "MATTERMOST_OAUTH_REQUIRE_CONSENT": "false",
            },
        ):
            from mcp_server_mattermost.config import get_settings

            get_settings.cache_clear()
            from mcp_server_mattermost.server import _create_mcp

            instance = _create_mcp()
            assert isinstance(instance.auth, OAuthProxy)
            get_settings.cache_clear()
