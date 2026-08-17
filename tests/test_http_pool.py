"""Tests for the shared HTTP connection pool and its lifecycle."""

import asyncio

import httpx
import pytest
import respx
from fastmcp import Client, FastMCP


TEAM = {
    "id": "tm1234567890123456789012",
    "create_at": 1706400000000,
    "update_at": 1706400000000,
    "delete_at": 0,
    "display_name": "My Team",
    "name": "team",
    "description": "",
    "email": "",
    "type": "O",
    "allowed_domains": "",
    "invite_id": "",
    "allow_open_invite": False,
}

USER = {
    "id": "us1234567890123456789012",
    "delete_at": 0,
    "username": "bot",
    "first_name": "",
    "last_name": "",
    "nickname": "",
    "email": "bot@example.com",
    "auth_service": "",
    "roles": "system_user",
    "locale": "en",
    "create_at": 1706400000000,
    "update_at": 1706400000000,
}


def _mock_teams():
    return respx.get("https://test.mattermost.com/api/v4/users/me/teams").mock(
        return_value=httpx.Response(200, json=[TEAM]),
    )


class TestSharedPool:
    @pytest.mark.asyncio
    @respx.mock
    async def test_series_of_tool_calls_creates_one_client(self, mock_settings, mocker):
        from mcp_server_mattermost import http_pool
        from mcp_server_mattermost.server import mcp

        _mock_teams()
        spy = mocker.spy(http_pool, "create_http_client")

        async with Client(mcp) as client:
            await client.call_tool("list_teams", {})
            await client.call_tool("list_teams", {})
            await asyncio.gather(
                client.call_tool("list_teams", {}),
                client.call_tool("list_teams", {}),
            )

        assert spy.call_count == 1

    @pytest.mark.asyncio
    async def test_lifespan_closes_pool_on_shutdown(self, mock_settings, mocker):
        from mcp_server_mattermost import http_pool
        from mcp_server_mattermost.server import mcp

        spy = mocker.spy(http_pool, "create_http_client")

        async with Client(mcp):
            pass

        assert spy.call_count == 1
        assert spy.spy_return.is_closed is True

    @pytest.mark.asyncio
    async def test_teardown_closes_auth_even_if_pool_close_raises(self, mock_settings, mocker):
        # Shutdown must free the auth provider even if the pool's aclose() fails.
        from mcp_server_mattermost import http_pool
        from mcp_server_mattermost.server import mcp

        failing_client = mocker.MagicMock()
        failing_client.aclose = mocker.AsyncMock(side_effect=RuntimeError("aclose boom"))
        mocker.patch.object(http_pool, "create_http_client", return_value=failing_client)

        fake_auth = mocker.MagicMock()
        fake_auth.close = mocker.AsyncMock()
        mocker.patch.object(mcp, "auth", fake_auth)

        with pytest.raises(RuntimeError, match="aclose boom"):
            async with Client(mcp):
                pass

        failing_client.aclose.assert_awaited_once()
        fake_auth.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_failed_close_does_not_leave_the_pool_registered(self, mock_settings, mocker):
        # A pool whose aclose() blew up is still gone from the registry, so the
        # next caller builds a working one instead of inheriting the wreckage.
        from mcp_server_mattermost import http_pool
        from mcp_server_mattermost.config import get_settings

        failing_client = mocker.MagicMock()
        failing_client.aclose = mocker.AsyncMock(side_effect=RuntimeError("aclose boom"))
        mocker.patch.object(http_pool, "create_http_client", return_value=failing_client)

        settings = get_settings()
        with pytest.raises(RuntimeError, match="aclose boom"):
            async with http_pool.owned_shared_client(settings):
                pass

        assert asyncio.get_running_loop() not in http_pool._entries


class TestPoolLifetime:
    @pytest.mark.asyncio
    async def test_borrowers_share_the_owner_pool(self, mock_settings):
        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.http_pool import owned_shared_client, shared_http_client

        settings = get_settings()
        async with owned_shared_client(settings) as pool:
            async with shared_http_client(settings) as borrowed:
                assert borrowed is pool
            # The owner is still in, so returning a borrowed pool closes nothing.
            assert pool.is_closed is False

        assert pool.is_closed is True

    @pytest.mark.asyncio
    async def test_pool_outlives_an_owner_that_leaves_mid_request(self, mock_settings):
        # FastMCP closes the lifespan stack when the first of several sessions
        # exits, without waiting for the rest. An in-flight request must not
        # have its socket pulled out from under it.
        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.http_pool import owned_shared_client, shared_http_client

        settings = get_settings()
        owner = owned_shared_client(settings)
        pool = await owner.__aenter__()

        borrow = shared_http_client(settings)
        borrowed = await borrow.__aenter__()
        assert borrowed is pool

        await owner.__aexit__(None, None, None)
        assert borrowed.is_closed is False

        await borrow.__aexit__(None, None, None)
        assert borrowed.is_closed is True

    @pytest.mark.asyncio
    async def test_retired_pool_is_never_handed_out_again(self, mock_settings):
        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.http_pool import owned_shared_client, shared_http_client

        settings = get_settings()
        owner = owned_shared_client(settings)
        retiring = await owner.__aenter__()
        borrow = shared_http_client(settings)
        await borrow.__aenter__()
        await owner.__aexit__(None, None, None)

        async with shared_http_client(settings) as fresh:
            assert fresh is not retiring
            assert fresh.is_closed is False

        await borrow.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_changed_settings_produce_a_new_pool(self, mock_settings, monkeypatch):
        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.http_pool import shared_http_client

        async with shared_http_client(get_settings()) as first:
            pass

        monkeypatch.setenv("MATTERMOST_URL", "https://other.mattermost.com")
        get_settings.cache_clear()

        async with shared_http_client(get_settings()) as second:
            assert second is not first
            assert str(second.base_url).rstrip("/") == "https://other.mattermost.com/api/v4"
            # The superseded pool is closed, not merely dropped and leaked.
            assert first.is_closed is True

    @pytest.mark.asyncio
    async def test_reset_shared_pool_forces_a_rebuild(self, mock_settings):
        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.http_pool import reset_shared_pool, shared_http_client

        settings = get_settings()
        async with shared_http_client(settings) as first:
            pass

        await reset_shared_pool()
        assert first.is_closed is True

        async with shared_http_client(settings) as second:
            assert second is not first


class TestPoolWithoutOurLifespan:
    @pytest.mark.asyncio
    @respx.mock
    async def test_second_session_survives_the_first_one_shutting_down(self, mock_settings, mocker):
        # FastMCP tears the lifespan down on the first session's exit. The
        # second session must keep serving calls, on a fresh pool.
        from mcp_server_mattermost import http_pool
        from mcp_server_mattermost.server import mcp

        _mock_teams()
        spy = mocker.spy(http_pool, "create_http_client")

        first, second = Client(mcp), Client(mcp)
        await first.__aenter__()
        await second.__aenter__()
        try:
            await first.call_tool("list_teams", {})
            await second.call_tool("list_teams", {})
            assert spy.call_count == 1

            await first.__aexit__(None, None, None)

            result = await second.call_tool("list_teams", {})
            assert result.data[0].name == "team"
            assert spy.call_count == 2
        finally:
            await second.__aexit__(None, None, None)

    @pytest.mark.asyncio
    @respx.mock
    async def test_tools_added_to_a_foreign_server_still_work(self, mock_settings, mocker):
        # Embedding: someone adds our tools to their own server, which never
        # runs app_lifespan. Before the registry this failed to resolve at all.
        from mcp_server_mattermost import http_pool
        from mcp_server_mattermost.tools.users import get_me

        respx.get("https://test.mattermost.com/api/v4/users/me").mock(
            return_value=httpx.Response(200, json=USER),
        )
        spy = mocker.spy(http_pool, "create_http_client")

        foreign = FastMCP("foreign")
        foreign.add_tool(get_me)

        async with Client(foreign) as client:
            first = await client.call_tool("get_me", {})
            second = await client.call_tool("get_me", {})

        assert first.data.username == "bot"
        assert second.data.username == "bot"
        # Embedded or not, both calls went through one pool.
        assert spy.call_count == 1
