"""Integration test: list_my_channels -> get_channel_messages(unread_only) flow."""

import pytest

from tests.integration.utils import to_dict


@pytest.mark.asyncio
@pytest.mark.integration
async def test_unread_flow_against_real_server(mcp_client, mattermost_env) -> None:
    """Agent can list unread channels and fetch their unread windows in one MCP session."""
    channels_result = await mcp_client.call_tool(
        "list_my_channels", {"team_id": mattermost_env.team_id, "only_unread": True}
    )
    channels = to_dict(channels_result)
    for ch in channels:
        assert "last_viewed_at" in ch
        assert isinstance(ch["last_viewed_at"], int)

    for ch in channels:
        posts_result = await mcp_client.call_tool(
            "get_channel_messages",
            {"channel_id": ch["id"], "unread_only": True, "limit_after": 200},
        )
        posts = to_dict(posts_result)
        assert "truncated" in posts
        assert len(posts["order"]) <= 200
