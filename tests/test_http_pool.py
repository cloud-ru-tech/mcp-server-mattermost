"""Tests proving tool calls reuse one shared HTTP client."""

import asyncio

import httpx
import pytest
import respx
from fastmcp import Client


class TestSharedPool:
    @pytest.mark.asyncio
    @respx.mock
    async def test_series_of_tool_calls_creates_one_client(self, mock_settings, mocker):
        from mcp_server_mattermost import server
        from mcp_server_mattermost.server import mcp

        team = {
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
        respx.get("https://test.mattermost.com/api/v4/users/me/teams").mock(
            return_value=httpx.Response(200, json=[team]),
        )
        spy = mocker.spy(server, "create_http_client")

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
        from mcp_server_mattermost import server
        from mcp_server_mattermost.server import mcp

        spy = mocker.spy(server, "create_http_client")

        async with Client(mcp):
            pass

        assert spy.call_count == 1
        assert spy.spy_return.is_closed is True

    @pytest.mark.asyncio
    async def test_teardown_closes_auth_even_if_pool_close_raises(self, mock_settings, mocker):
        # Shutdown must free the auth provider even if the pool's aclose() fails.
        from mcp_server_mattermost import server
        from mcp_server_mattermost.server import mcp

        failing_client = mocker.MagicMock()
        failing_client.aclose = mocker.AsyncMock(side_effect=RuntimeError("aclose boom"))
        mocker.patch.object(server, "create_http_client", return_value=failing_client)

        fake_auth = mocker.MagicMock()
        fake_auth.close = mocker.AsyncMock()
        mocker.patch.object(mcp, "auth", fake_auth)

        with pytest.raises(RuntimeError, match="aclose boom"):
            async with Client(mcp):
                pass

        failing_client.aclose.assert_awaited_once()
        fake_auth.close.assert_awaited_once()
