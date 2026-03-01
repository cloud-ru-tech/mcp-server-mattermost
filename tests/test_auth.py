"""Tests for MattermostTokenVerifier."""

import asyncio

import httpx
import pytest
import respx
from cachetools import TTLCache


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
        """verify_token reuses httpx.AsyncClient across calls (no extra HTTP overhead)."""
        from mcp_server_mattermost.auth import MattermostTokenVerifier
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        verifier = MattermostTokenVerifier()

        with respx.mock:
            route = respx.get(f"{settings.url}/api/v4/users/me").mock(
                return_value=httpx.Response(200, json={"id": "u1", "username": "a"})
            )
            await verifier.verify_token("token-a")
            await verifier.verify_token("token-b")

        assert route.call_count == 2

    @pytest.mark.asyncio
    async def test_expired_cache_makes_new_request(self, mock_settings: None) -> None:
        """Expired cache entry triggers fresh HTTP request."""
        from mcp_server_mattermost.auth import _TOKEN_CACHE_TTL, MattermostTokenVerifier
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        verifier = MattermostTokenVerifier()

        # Replace cache with one using a controllable timer
        fake_time = 0.0

        def mock_timer() -> float:
            return fake_time

        verifier._cache = TTLCache(maxsize=512, ttl=_TOKEN_CACHE_TTL, timer=mock_timer)

        with respx.mock:
            route = respx.get(f"{settings.url}/api/v4/users/me").mock(
                return_value=httpx.Response(200, json={"id": "user1", "username": "alice"})
            )
            await verifier.verify_token("expiring-token")

            # Advance time past TTL to expire the cache entry
            fake_time = _TOKEN_CACHE_TTL + 1.0
            await verifier.verify_token("expiring-token")

            assert route.call_count == 2

    @pytest.mark.asyncio
    async def test_close_cleans_up_client(self, mock_settings: None) -> None:
        """After close(), verify_token still succeeds via lazy re-initialization."""
        from mcp_server_mattermost.auth import MattermostTokenVerifier
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        verifier = MattermostTokenVerifier()

        with respx.mock:
            route = respx.get(f"{settings.url}/api/v4/users/me").mock(
                return_value=httpx.Response(200, json={"id": "user1", "username": "alice"})
            )
            # First call creates the client
            result1 = await verifier.verify_token("token-1")
            assert result1 is not None

            # Close discards the client
            await verifier.close()

            # Next call should lazy re-init and succeed
            result2 = await verifier.verify_token("token-2")
            assert result2 is not None
            assert result2.client_id == "user1"
            assert route.call_count == 2

    @pytest.mark.asyncio
    async def test_close_when_never_used_is_safe(self, mock_settings: None) -> None:
        """Calling close() on a verifier that was never used does not raise."""
        from mcp_server_mattermost.auth import MattermostTokenVerifier

        verifier = MattermostTokenVerifier()
        await verifier.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_concurrent_verify_token(self, mock_settings: None) -> None:
        """Multiple concurrent verify_token calls all return valid results."""
        from mcp_server_mattermost.auth import MattermostTokenVerifier
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        verifier = MattermostTokenVerifier()

        with respx.mock:
            route = respx.get(f"{settings.url}/api/v4/users/me").mock(
                return_value=httpx.Response(200, json={"id": "user1", "username": "alice"})
            )
            results = await asyncio.gather(*[verifier.verify_token("same-token") for _ in range(5)])

        assert all(r is not None for r in results)
        assert all(r.client_id == "user1" for r in results)
        # Cache deduplication: all 5 concurrent calls share the same token,
        # so only 1 HTTP request must be made regardless of concurrency.
        assert route.call_count == 1
