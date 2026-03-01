"""Tests for dependency injection providers."""

from unittest.mock import patch

import pytest


class TestGetClient:
    @pytest.mark.asyncio
    async def test_uses_settings_token_without_auth_context(self, mock_settings: None) -> None:
        """Without auth context (STDIO), _token_override is None — settings.token used."""
        from mcp_server_mattermost.client import MattermostClient
        from mcp_server_mattermost.deps import get_client

        # get_access_token() returns None outside HTTP context
        with patch("mcp_server_mattermost.deps.get_access_token", return_value=None):
            async with get_client() as client:
                assert isinstance(client, MattermostClient)
                assert client._token_override is None

    @pytest.mark.asyncio
    async def test_uses_access_token_claims_when_present(self, mock_settings_allow_http: None) -> None:
        """With allow_http_client_tokens and AccessToken, uses mattermost_token from claims."""
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
    async def test_no_override_when_allow_http_disabled(self, mock_settings: None) -> None:
        """When allow_http_client_tokens=False, get_access_token() is not called."""
        from fastmcp.server.auth import AccessToken

        from mcp_server_mattermost.client import MattermostClient
        from mcp_server_mattermost.deps import get_client

        mock_token = AccessToken(
            token="raw-bearer",
            client_id="user123",
            scopes=[],
            claims={"mattermost_token": "should-not-be-used"},
        )

        # Even if access token is present, it should be ignored when flag is False
        with patch("mcp_server_mattermost.deps.get_access_token", return_value=mock_token):
            async with get_client() as client:
                assert isinstance(client, MattermostClient)
                assert client._token_override is None
