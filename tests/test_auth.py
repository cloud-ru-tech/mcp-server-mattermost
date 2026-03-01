"""Tests for MattermostTokenVerifier."""

import httpx
import pytest
import respx


class TestMattermostTokenVerifier:
    @pytest.mark.asyncio
    async def test_valid_token_returns_access_token(self, mock_settings: None) -> None:
        """Valid Mattermost token returns AccessToken with mattermost_token claim."""
        from mcp_server_mattermost.auth import MattermostTokenVerifier
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        verifier = MattermostTokenVerifier(settings)

        with respx.mock:
            respx.get(f"{settings.url}/api/v4/users/me").mock(
                return_value=httpx.Response(200, json={"id": "user123", "username": "alice"})
            )
            result = await verifier.verify_token("valid-token-abc")

        assert result is not None
        assert result.client_id == "user123"
        assert result.claims["mattermost_token"] == "valid-token-abc"

    @pytest.mark.asyncio
    async def test_invalid_token_returns_none(self, mock_settings: None) -> None:
        """Invalid Mattermost token (401) returns None."""
        from mcp_server_mattermost.auth import MattermostTokenVerifier
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        verifier = MattermostTokenVerifier(settings)

        with respx.mock:
            respx.get(f"{settings.url}/api/v4/users/me").mock(
                return_value=httpx.Response(401, json={"message": "Unauthorized"})
            )
            result = await verifier.verify_token("bad-token")

        assert result is None

    @pytest.mark.asyncio
    async def test_network_error_returns_none(self, mock_settings: None) -> None:
        """Network error during validation returns None (fail-closed)."""
        from mcp_server_mattermost.auth import MattermostTokenVerifier
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        verifier = MattermostTokenVerifier(settings)

        with respx.mock:
            respx.get(f"{settings.url}/api/v4/users/me").mock(side_effect=httpx.ConnectError("connection refused"))
            result = await verifier.verify_token("any-token")

        assert result is None
