"""Integration tests for post tools (reactions, pins, threads) via MCP protocol."""

import pytest

from tests.integration.utils import to_dict


class TestReactions:
    """Reaction operations through MCP protocol."""

    async def test_add_reaction(self, mcp_client, test_post):
        """add_reaction: adds reaction to post."""
        result = await mcp_client.call_tool(
            "add_reaction",
            {
                "post_id": test_post["id"],
                "emoji_name": "thumbsup",
            },
        )

        reaction = to_dict(result)
        assert reaction["emoji_name"] == "thumbsup"
        assert reaction["post_id"] == test_post["id"]

    async def test_add_reaction_idempotent(self, mcp_client, test_post):
        """add_reaction: idempotent (no error for duplicate)."""
        await mcp_client.call_tool(
            "add_reaction",
            {"post_id": test_post["id"], "emoji_name": "smile"},
        )

        result = await mcp_client.call_tool(
            "add_reaction",
            {"post_id": test_post["id"], "emoji_name": "smile"},
        )

        assert result is not None

    async def test_get_reactions(self, mcp_client, test_post):
        """get_reactions: returns reactions array."""
        await mcp_client.call_tool(
            "add_reaction",
            {"post_id": test_post["id"], "emoji_name": "heart"},
        )

        result = await mcp_client.call_tool(
            "get_reactions",
            {"post_id": test_post["id"]},
        )

        reactions = to_dict(result)
        assert isinstance(reactions, list)
        assert any(r["emoji_name"] == "heart" for r in reactions)

    async def test_get_reactions_empty_for_no_reactions(self, mcp_client, test_channel):
        """get_reactions: returns empty array for post without reactions."""
        post_result = await mcp_client.call_tool(
            "post_message",
            {"channel_id": test_channel["id"], "message": "No reactions here"},
        )
        post = to_dict(post_result.data)

        try:
            result = await mcp_client.call_tool(
                "get_reactions",
                {"post_id": post["id"]},
            )

            reactions = to_dict(result)
            assert reactions == []
        finally:
            await mcp_client.call_tool("delete_message", {"post_id": post["id"]})

    async def test_remove_reaction(self, mcp_client, test_post):
        """remove_reaction: removes reaction."""
        await mcp_client.call_tool(
            "add_reaction",
            {"post_id": test_post["id"], "emoji_name": "wave"},
        )

        await mcp_client.call_tool(
            "remove_reaction",
            {"post_id": test_post["id"], "emoji_name": "wave"},
        )


class TestPins:
    """Pin operations through MCP protocol."""

    async def test_pin_message(self, mcp_client, test_post):
        """pin_message: pins message (is_pinned=true)."""
        result = await mcp_client.call_tool(
            "pin_message",
            {"post_id": test_post["id"]},
        )

        post = to_dict(result)
        assert post["is_pinned"] is True

    async def test_pin_message_idempotent(self, mcp_client, test_post):
        """pin_message: idempotent (no error for already pinned)."""
        await mcp_client.call_tool("pin_message", {"post_id": test_post["id"]})
        await mcp_client.call_tool("pin_message", {"post_id": test_post["id"]})

    async def test_unpin_message(self, mcp_client, test_post):
        """unpin_message: unpins message (is_pinned=false)."""
        await mcp_client.call_tool("pin_message", {"post_id": test_post["id"]})

        result = await mcp_client.call_tool(
            "unpin_message",
            {"post_id": test_post["id"]},
        )

        post = to_dict(result)
        assert post["is_pinned"] is False

    async def test_unpin_message_idempotent(self, mcp_client, test_post):
        """unpin_message: idempotent (no error for not pinned)."""
        await mcp_client.call_tool(
            "unpin_message",
            {"post_id": test_post["id"]},
        )


class TestThreads:
    """Thread operations through MCP protocol."""

    async def test_get_thread_with_replies(self, mcp_client, test_channel, test_post):
        """get_thread: returns thread with root + replies."""
        reply_result = await mcp_client.call_tool(
            "post_message",
            {
                "channel_id": test_channel["id"],
                "message": "Reply to thread",
                "root_id": test_post["id"],
            },
        )
        reply = to_dict(reply_result.data)

        try:
            result = await mcp_client.call_tool(
                "get_thread",
                {"post_id": test_post["id"]},
            )

            thread = to_dict(result)
            assert "posts" in thread
            assert "order" in thread
            assert test_post["id"] in thread["posts"]
            assert reply["id"] in thread["posts"]
        finally:
            await mcp_client.call_tool("delete_message", {"post_id": reply["id"]})

    async def test_get_thread_without_replies(self, mcp_client, test_post):
        """get_thread: returns only root for post without replies."""
        result = await mcp_client.call_tool(
            "get_thread",
            {"post_id": test_post["id"]},
        )

        thread = to_dict(result)
        assert "posts" in thread
        assert test_post["id"] in thread["posts"]
        assert len(thread["order"]) >= 1


class TestReactionValidation:
    """Reaction input validation through MCP protocol."""

    @pytest.mark.parametrize(
        ("emoji_name", "expected_error"),
        [
            ("", r"validation|empty|required"),
            (":thumbsup:", r"validation|colon"),
            ("has space", r"validation|space"),
            ("a" * 65, r"validation|64|too long"),
            ("emoji@invalid", r"validation|character|@"),
        ],
    )
    async def test_add_reaction_invalid_emoji(self, mcp_client, test_post, emoji_name, expected_error):
        """add_reaction: ValidationError for invalid emoji_name."""
        with pytest.raises(Exception, match=expected_error):
            await mcp_client.call_tool(
                "add_reaction",
                {"post_id": test_post["id"], "emoji_name": emoji_name},
            )

    @pytest.mark.parametrize(
        "emoji_name",
        [
            "thumbsup",
            "smile",
            "heart",
            "+1",
        ],
    )
    async def test_add_reaction_valid_emoji(self, mcp_client, test_post, emoji_name):
        """add_reaction: accepts valid emoji formats (standard emoji only).

        Note: Custom emoji names (custom_emoji, emoji-with-dash, etc.) are valid
        format-wise but require the emoji to actually exist on the server.
        We test with standard emoji that exist on all Mattermost instances.
        """
        result = await mcp_client.call_tool(
            "add_reaction",
            {"post_id": test_post["id"], "emoji_name": emoji_name},
        )
        reaction = to_dict(result)
        assert reaction["emoji_name"] == emoji_name

        await mcp_client.call_tool(
            "remove_reaction",
            {"post_id": test_post["id"], "emoji_name": emoji_name},
        )
