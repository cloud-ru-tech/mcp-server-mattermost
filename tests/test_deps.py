"""Tests for dependency injection providers."""

from unittest.mock import patch

import pytest


class TestGetClient:
    @pytest.mark.asyncio
    async def test_static_token_uses_settings_token_without_override(self, mock_settings: None) -> None:
        """static_token mode lets MattermostClient use settings.token."""
        from mcp_server_mattermost.client import MattermostClient
        from mcp_server_mattermost.deps import get_client

        with patch("mcp_server_mattermost.deps.get_access_token", return_value=None):
            async with get_client() as client:
                assert isinstance(client, MattermostClient)
                assert client._token_override is None

    @pytest.mark.asyncio
    async def test_client_token_uses_access_token_claims(self, mock_settings_allow_http: None) -> None:
        """client_token mode uses mattermost_token from auth context."""
        from fastmcp.server.auth import AccessToken

        from mcp_server_mattermost.client import MattermostClient
        from mcp_server_mattermost.deps import get_client

        mock_token = AccessToken(
            token="raw-bearer",
            client_id="user123",
            scopes=[],
            claims={"mattermost_token": "from-mattermost-token"},
        )

        with patch("mcp_server_mattermost.deps.get_access_token", return_value=mock_token):
            async with get_client() as client:
                assert isinstance(client, MattermostClient)
                assert client._token_override == "from-mattermost-token"

    @pytest.mark.asyncio
    async def test_client_token_missing_access_token_raises(self, mock_settings_allow_http: None) -> None:
        """client_token mode never falls back to a static token."""
        from mcp_server_mattermost.deps import get_client
        from mcp_server_mattermost.exceptions import AuthenticationError

        with (
            patch("mcp_server_mattermost.deps.get_access_token", return_value=None),
            pytest.raises(AuthenticationError, match="Mattermost token is required"),
        ):
            async with get_client():
                pass

    @pytest.mark.asyncio
    async def test_client_token_missing_mattermost_claim_raises(self, mock_settings_allow_http: None) -> None:
        """client_token mode requires mattermost_token claim."""
        from fastmcp.server.auth import AccessToken

        from mcp_server_mattermost.deps import get_client
        from mcp_server_mattermost.exceptions import AuthenticationError

        mock_token = AccessToken(
            token="raw-bearer",
            client_id="user123",
            scopes=[],
            claims={"some_other_claim": "value"},
        )

        with (
            patch("mcp_server_mattermost.deps.get_access_token", return_value=mock_token),
            pytest.raises(AuthenticationError, match="Mattermost token is required"),
        ):
            async with get_client():
                pass

    @pytest.mark.asyncio
    async def test_oauth_proxy_uses_access_token_claims(self, monkeypatch) -> None:
        """oauth_proxy mode uses mattermost_token from FastMCP OAuthProxy auth context."""
        from fastmcp.server.auth import AccessToken

        from mcp_server_mattermost.client import MattermostClient
        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.deps import get_client

        get_settings.cache_clear()
        monkeypatch.setenv("MATTERMOST_URL", "http://mattermost.internal")
        monkeypatch.setenv("MATTERMOST_AUTH_MODE", "oauth_proxy")
        monkeypatch.setenv("MATTERMOST_OAUTH_CLIENT_TYPE", "public")
        monkeypatch.setenv("MATTERMOST_OAUTH_CLIENT_ID", "mm-client")
        monkeypatch.setenv("MATTERMOST_OAUTH_JWT_SIGNING_KEY", "signing-key-1234567890")
        monkeypatch.setenv("MATTERMOST_OAUTH_MCP_PUBLIC_URL", "http://localhost:8000")

        mock_token = AccessToken(
            token="fastmcp-jwt",
            client_id="user123",
            scopes=[],
            claims={"mattermost_token": "from-oauth-proxy"},
        )

        with patch("mcp_server_mattermost.deps.get_access_token", return_value=mock_token):
            async with get_client() as client:
                assert isinstance(client, MattermostClient)
                assert client._token_override == "from-oauth-proxy"

        get_settings.cache_clear()
