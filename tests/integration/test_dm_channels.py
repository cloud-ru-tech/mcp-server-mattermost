"""Integration tests for Direct Message channels via MCP protocol."""

import contextlib

from tests.integration.utils import to_dict


class TestDMHappyPath:
    """DM channel operations through MCP protocol."""

    async def test_create_dm_returns_type_d(self, mcp_client, bot_user):
        """create_direct_channel: creates DM with type=D."""
        result = await mcp_client.call_tool(
            "create_direct_channel",
            {"user_id_1": bot_user["id"], "user_id_2": bot_user["id"]},
        )
        channel = to_dict(result)
        assert channel["type"] == "D"

    async def test_post_message_in_dm(self, mcp_client, bot_user):
        """post_message: posts to DM channel."""
        dm_result = await mcp_client.call_tool(
            "create_direct_channel",
            {"user_id_1": bot_user["id"], "user_id_2": bot_user["id"]},
        )
        dm = to_dict(dm_result.data)

        result = await mcp_client.call_tool(
            "post_message",
            {"channel_id": dm["id"], "message": "DM test message"},
        )
        post = to_dict(result)

        try:
            assert post["channel_id"] == dm["id"]
            assert post["message"] == "DM test message"
        finally:
            with contextlib.suppress(Exception):
                await mcp_client.call_tool("delete_message", {"post_id": post["id"]})

    async def test_get_dm_messages(self, mcp_client, bot_user):
        """get_channel_messages: returns DM messages."""
        dm_result = await mcp_client.call_tool(
            "create_direct_channel",
            {"user_id_1": bot_user["id"], "user_id_2": bot_user["id"]},
        )
        dm = to_dict(dm_result.data)

        post_result = await mcp_client.call_tool(
            "post_message",
            {"channel_id": dm["id"], "message": "DM history test"},
        )
        post = to_dict(post_result.data)

        try:
            result = await mcp_client.call_tool(
                "get_channel_messages",
                {"channel_id": dm["id"]},
            )
            data = to_dict(result)
            posts = data.get("posts", {})
            assert post["id"] in posts
        finally:
            with contextlib.suppress(Exception):
                await mcp_client.call_tool("delete_message", {"post_id": post["id"]})

    async def test_react_in_dm(self, mcp_client, bot_user):
        """add_reaction: works in DM channel."""
        dm_result = await mcp_client.call_tool(
            "create_direct_channel",
            {"user_id_1": bot_user["id"], "user_id_2": bot_user["id"]},
        )
        dm = to_dict(dm_result.data)

        post_result = await mcp_client.call_tool(
            "post_message",
            {"channel_id": dm["id"], "message": "React to this"},
        )
        post = to_dict(post_result.data)

        try:
            result = await mcp_client.call_tool(
                "add_reaction",
                {"post_id": post["id"], "emoji_name": "thumbsup"},
            )
            reaction = to_dict(result)
            assert reaction["emoji_name"] == "thumbsup"
        finally:
            with contextlib.suppress(Exception):
                await mcp_client.call_tool("delete_message", {"post_id": post["id"]})

    async def test_reply_in_dm(self, mcp_client, bot_user):
        """post_message: reply works in DM with root_id."""
        dm_result = await mcp_client.call_tool(
            "create_direct_channel",
            {"user_id_1": bot_user["id"], "user_id_2": bot_user["id"]},
        )
        dm = to_dict(dm_result.data)

        root_result = await mcp_client.call_tool(
            "post_message",
            {"channel_id": dm["id"], "message": "Root message"},
        )
        root = to_dict(root_result.data)

        try:
            reply_result = await mcp_client.call_tool(
                "post_message",
                {"channel_id": dm["id"], "message": "Reply", "root_id": root["id"]},
            )
            reply = to_dict(reply_result.data)

            assert reply["root_id"] == root["id"]
        finally:
            with contextlib.suppress(Exception):
                await mcp_client.call_tool("delete_message", {"post_id": root["id"]})
