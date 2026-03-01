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
        verifier = MattermostTokenVerifier()

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
        verifier = MattermostTokenVerifier()

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
        verifier = MattermostTokenVerifier()

        with respx.mock:
            respx.get(f"{settings.url}/api/v4/users/me").mock(side_effect=httpx.ConnectError("connection refused"))
            result = await verifier.verify_token("any-token")

        assert result is None

    @pytest.mark.asyncio
    async def test_cached_token_skips_http_call(self, mock_settings: None) -> None:
        """Second verify_token call with same token uses cache, no HTTP request."""
        from mcp_server_mattermost.auth import MattermostTokenVerifier
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        verifier = MattermostTokenVerifier()

        with respx.mock:
            route = respx.get(f"{settings.url}/api/v4/users/me").mock(
                return_value=httpx.Response(200, json={"id": "user123", "username": "alice"})
            )
            result1 = await verifier.verify_token("cached-token")
            result2 = await verifier.verify_token("cached-token")

        assert result1 is not None
        assert result2 is not None
        assert result2.client_id == "user123"
        assert route.call_count == 1

    @pytest.mark.asyncio
    async def test_reuses_http_client(self, mock_settings: None) -> None:
        """verify_token reuses httpx.AsyncClient across calls."""
        from mcp_server_mattermost.auth import MattermostTokenVerifier
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        verifier = MattermostTokenVerifier()

        with respx.mock:
            respx.get(f"{settings.url}/api/v4/users/me").mock(
                return_value=httpx.Response(200, json={"id": "u1", "username": "a"})
            )
            await verifier.verify_token("token-a")

        with respx.mock:
            respx.get(f"{settings.url}/api/v4/users/me").mock(
                return_value=httpx.Response(200, json={"id": "u2", "username": "b"})
            )
            await verifier.verify_token("token-b")

        assert verifier._client is not None

    @pytest.mark.asyncio
    async def test_expired_cache_makes_new_request(self, mock_settings: None) -> None:
        """Expired cache entry triggers fresh HTTP request."""
        import time
        from unittest.mock import patch

        from mcp_server_mattermost.auth import MattermostTokenVerifier
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        verifier = MattermostTokenVerifier()

        with respx.mock:
            route = respx.get(f"{settings.url}/api/v4/users/me").mock(
                return_value=httpx.Response(200, json={"id": "user1", "username": "alice"})
            )
            await verifier.verify_token("expiring-token")

            with patch("mcp_server_mattermost.auth.time.monotonic", return_value=time.monotonic() + 120):
                await verifier.verify_token("expiring-token")

            assert route.call_count == 2
