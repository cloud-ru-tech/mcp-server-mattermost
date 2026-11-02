"""Integration tests for MATTERMOST_DEFAULT_TEAM_ID via MCP protocol."""

import contextlib

import httpx
import pytest
import pytest_asyncio
from fastmcp import Client

from mcp_server_mattermost.config import get_settings
from tests.integration.utils import cleanup_channel, make_test_name, to_dict


@pytest_asyncio.fixture(loop_scope="session")
async def default_team_client(mattermost_env, monkeypatch):
    """MCP client of a server configured with the test team as its default."""
    from mcp_server_mattermost.server import _create_mcp

    # The root conftest's autouse clean_env strips MATTERMOST_* per test; other
    # integration tests rely on cached settings, this one rebuilds them.
    monkeypatch.setenv("MATTERMOST_URL", mattermost_env.url)
    monkeypatch.setenv("MATTERMOST_TOKEN", mattermost_env.token)
    monkeypatch.setenv("MATTERMOST_DEFAULT_TEAM_ID", mattermost_env.team_id)
    get_settings.cache_clear()
    try:
        async with Client(_create_mcp()) as client:
            yield client
    finally:
        monkeypatch.delenv("MATTERMOST_DEFAULT_TEAM_ID")
        get_settings.cache_clear()
        # Re-cache while URL/token are still set, so later tests see settings without the default.
        get_settings()


@pytest_asyncio.fixture(loop_scope="session")
async def other_team(mattermost_env, bot_user):
    """Second team with the bot as a member (Testcontainers only)."""
    if mattermost_env.admin_token is None:
        pytest.skip("Creating a second team needs the Testcontainers admin token")

    async with httpx.AsyncClient(
        base_url=f"{mattermost_env.url}/api/v4",
        headers={"Authorization": f"Bearer {mattermost_env.admin_token}"},
        timeout=10.0,
    ) as client:
        name = make_test_name("mcp-test-team")
        resp = await client.post("/teams", json={"name": name, "display_name": name, "type": "O"})
        resp.raise_for_status()
        team = resp.json()
        resp = await client.post(
            f"/teams/{team['id']}/members",
            json={"team_id": team["id"], "user_id": bot_user["id"]},
        )
        resp.raise_for_status()

        yield team

        with contextlib.suppress(httpx.HTTPError):
            await client.delete(f"/teams/{team['id']}")


async def test_instructions_name_default_team(default_team_client, mattermost_env):
    """Server instructions advertise the configured default team."""
    assert mattermost_env.team_id in (default_team_client.instructions or "")


async def test_omitted_team_id_uses_default(default_team_client, mattermost_env, test_channel):
    """Team-scoped reads without team_id target the default team."""
    team = to_dict(await default_team_client.call_tool("get_team", {}))
    assert team["id"] == mattermost_env.team_id

    channels = to_dict(await default_team_client.call_tool("list_my_channels", {}))
    assert test_channel["id"] in [ch["id"] for ch in channels]

    channel = to_dict(
        await default_team_client.call_tool("get_channel_by_name", {"channel_name": test_channel["name"]}),
    )
    assert channel["id"] == test_channel["id"]


async def test_create_channel_without_team_id_uses_default(default_team_client, mattermost_env):
    """create_channel without team_id creates the channel in the default team."""
    name = make_test_name()
    channel = to_dict(
        await default_team_client.call_tool(
            "create_channel",
            {"name": name, "display_name": f"Test {name}", "channel_type": "O"},
        ),
    )
    try:
        assert channel["team_id"] == mattermost_env.team_id
    finally:
        await cleanup_channel(channel["id"])


async def test_explicit_team_id_overrides_default(default_team_client, mattermost_env, other_team):
    """An explicit team_id selects another team despite the default."""
    team = to_dict(await default_team_client.call_tool("get_team", {"team_id": other_team["id"]}))
    assert team["id"] == other_team["id"]

    channels = to_dict(await default_team_client.call_tool("list_my_channels", {"team_id": other_team["id"]}))
    # Direct and group channels have no team and are returned for every team.
    assert {ch["team_id"] for ch in channels if ch["team_id"]} == {other_team["id"]}
    assert other_team["id"] != mattermost_env.team_id


async def test_omitted_team_id_without_default_is_rejected(mcp_client):
    """Without a default, omitting team_id fails before any Mattermost call and points to list_teams."""
    assert get_settings().default_team_id is None
    with pytest.raises(Exception, match=r"team_id is required.*list_teams"):
        await mcp_client.call_tool("list_my_channels", {})
