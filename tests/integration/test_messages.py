"""Integration tests for message tools via MCP protocol."""

import time

import pytest

from tests.integration.utils import to_dict, wait_for_indexing


class TestMessageHappyPath:
    """Basic successful message operations through MCP protocol."""

    async def test_post_message_creates_message(self, mcp_client, test_channel):
        """post_message: creates message with text."""
        result = await mcp_client.call_tool(
            "post_message",
            {
                "channel_id": test_channel["id"],
                "message": "Hello from integration test!",
            },
        )

        post = to_dict(result)
        assert post["message"] == "Hello from integration test!"
        assert post["channel_id"] == test_channel["id"]

        await mcp_client.call_tool("delete_message", {"post_id": post["id"]})

    async def test_post_message_with_reply(self, mcp_client, test_channel, test_post):
        """post_message: creates reply with root_id."""
        result = await mcp_client.call_tool(
            "post_message",
            {
                "channel_id": test_channel["id"],
                "message": "This is a reply",
                "root_id": test_post["id"],
            },
        )

        reply = to_dict(result)
        try:
            assert reply["root_id"] == test_post["id"]
        finally:
            await mcp_client.call_tool("delete_message", {"post_id": reply["id"]})

    async def test_get_channel_messages(self, mcp_client, test_channel, test_post):
        """get_channel_messages: returns messages in channel."""
        result = await mcp_client.call_tool(
            "get_channel_messages",
            {"channel_id": test_channel["id"]},
        )

        data = to_dict(result)
        assert "posts" in data or isinstance(data, list)

    async def test_update_message(self, mcp_client, test_post):
        """update_message: updates message content."""
        result = await mcp_client.call_tool(
            "update_message",
            {
                "post_id": test_post["id"],
                "message": "Updated message content",
            },
        )

        updated = to_dict(result)
        assert updated["message"] == "Updated message content"
        assert updated["edit_at"] > 0

    @pytest.mark.destructive
    async def test_delete_message(self, mcp_client, test_channel):
        """delete_message: deletes message successfully."""
        create_result = await mcp_client.call_tool(
            "post_message",
            {
                "channel_id": test_channel["id"],
                "message": "Message to delete",
            },
        )
        post_id = to_dict(create_result.data)["id"]

        await mcp_client.call_tool(
            "delete_message",
            {"post_id": post_id},
        )

    @pytest.mark.slow
    async def test_search_messages_finds_content(self, mcp_client, team, test_channel):
        """search_messages: finds message by content."""
        unique_term = f"searchtest{int(time.time())}"
        post_result = await mcp_client.call_tool(
            "post_message",
            {
                "channel_id": test_channel["id"],
                "message": f"This is a {unique_term} message",
            },
        )
        post = to_dict(post_result.data)

        try:

            async def check_indexed():
                result = await mcp_client.call_tool(
                    "search_messages",
                    {"team_id": team["id"], "terms": unique_term},
                )
                data = to_dict(result)
                posts = data.get("posts", {}) if isinstance(data, dict) else {}
                return post["id"] in posts

            await wait_for_indexing(check_indexed, timeout=10.0)

            result = await mcp_client.call_tool(
                "search_messages",
                {"team_id": team["id"], "terms": unique_term},
            )

            data = to_dict(result)
            posts = data.get("posts", {}) if isinstance(data, dict) else {}
            assert post["id"] in posts
        finally:
            await mcp_client.call_tool("delete_message", {"post_id": post["id"]})


class TestMessageValidation:
    """Message input validation through MCP protocol."""

    async def test_post_message_min_length(self, mcp_client, test_channel):
        """post_message: accepts minimum message (1 char)."""
        result = await mcp_client.call_tool(
            "post_message",
            {"channel_id": test_channel["id"], "message": "A"},
        )
        post = to_dict(result)
        try:
            assert post["message"] == "A"
        finally:
            await mcp_client.call_tool("delete_message", {"post_id": post["id"]})

    async def test_post_message_empty_error(self, mcp_client, test_channel):
        """post_message: ValidationError for empty message."""
        with pytest.raises(Exception, match=r"validation|empty|required"):
            await mcp_client.call_tool(
                "post_message",
                {"channel_id": test_channel["id"], "message": ""},
            )

    async def test_post_message_too_long_error(self, mcp_client, test_channel):
        """post_message: ValidationError for message > 16383 chars."""
        long_message = "a" * 16384
        with pytest.raises(Exception, match=r"validation|16383|too long|max"):
            await mcp_client.call_tool(
                "post_message",
                {"channel_id": test_channel["id"], "message": long_message},
            )

    @pytest.mark.parametrize(
        ("terms", "expected_error"),
        [
            ("", r"validation|empty|required"),
            ("a" * 513, r"validation|512|too long"),
        ],
    )
    async def test_search_messages_invalid_terms(self, mcp_client, terms, expected_error):
        """search_messages: ValidationError for invalid search terms."""
        with pytest.raises(Exception, match=expected_error):
            await mcp_client.call_tool("search_messages", {"terms": terms})


class TestMessagePagination:
    """Message listing pagination through MCP protocol."""

    async def test_get_channel_messages_per_page_1(self, mcp_client, test_channel, test_post):
        """get_channel_messages: pagination with per_page=1."""
        result = await mcp_client.call_tool(
            "get_channel_messages",
            {"channel_id": test_channel["id"], "per_page": 1},
        )
        data = to_dict(result)
        assert len(data.get("order", [])) == 1

    @pytest.mark.parametrize(
        ("per_page", "expected_error"),
        [
            (0, r"validation|per_page|0|greater"),
            (201, r"validation|per_page|200|max"),
        ],
    )
    async def test_get_channel_messages_invalid_per_page(self, mcp_client, test_channel, per_page, expected_error):
        """get_channel_messages: ValidationError for invalid per_page."""
        with pytest.raises(Exception, match=expected_error):
            await mcp_client.call_tool(
                "get_channel_messages",
                {"channel_id": test_channel["id"], "per_page": per_page},
            )

    async def test_get_channel_messages_negative_page(self, mcp_client, test_channel):
        """get_channel_messages: ValidationError for negative page."""
        with pytest.raises(Exception, match=r"validation|page|negative"):
            await mcp_client.call_tool(
                "get_channel_messages",
                {"channel_id": test_channel["id"], "page": -1},
            )


class TestMessagePermissions:
    """Message permission boundaries through MCP protocol."""

    async def test_update_deleted_message_error(self, mcp_client, test_channel):
        """update_message: error for already deleted message."""
        result = await mcp_client.call_tool(
            "post_message",
            {"channel_id": test_channel["id"], "message": "Will be deleted"},
        )
        post = to_dict(result)
        await mcp_client.call_tool("delete_message", {"post_id": post["id"]})

        with pytest.raises(Exception, match=r"403|404|not found|deleted|permissions"):
            await mcp_client.call_tool(
                "update_message",
                {"post_id": post["id"], "message": "Updated"},
            )


class TestPostMessageWithAttachments:
    """Integration tests for post_message with attachments."""

    async def test_post_message_with_color_attachment(self, mcp_client, test_channel):
        """post_message: creates message with colored attachment."""
        result = await mcp_client.call_tool(
            "post_message",
            {
                "channel_id": test_channel["id"],
                "message": "Status update",
                "attachments": [{"color": "good", "text": "All systems operational"}],
            },
        )

        post = to_dict(result)
        try:
            assert post["channel_id"] == test_channel["id"]
            assert post["message"] == "Status update"
        finally:
            await mcp_client.call_tool("delete_message", {"post_id": post["id"]})

    async def test_post_message_with_fields(self, mcp_client, test_channel):
        """post_message: creates message with attachment fields."""
        result = await mcp_client.call_tool(
            "post_message",
            {
                "channel_id": test_channel["id"],
                "message": "Task notification",
                "attachments": [
                    {
                        "color": "warning",
                        "title": "Task #123",
                        "text": "Needs review",
                        "fields": [
                            {"title": "Assignee", "value": "@john", "short": True},
                            {"title": "Priority", "value": "High", "short": True},
                        ],
                        "footer": "Task Bot",
                    }
                ],
            },
        )

        post = to_dict(result)
        try:
            assert post["channel_id"] == test_channel["id"]
        finally:
            await mcp_client.call_tool("delete_message", {"post_id": post["id"]})

    async def test_post_message_invalid_color_rejected(self, mcp_client, test_channel):
        """post_message: ValidationError for invalid color."""
        with pytest.raises(Exception, match=r"color|validation|invalid"):
            await mcp_client.call_tool(
                "post_message",
                {
                    "channel_id": test_channel["id"],
                    "message": "Bad attachment",
                    "attachments": [{"color": "red", "text": "This should fail"}],
                },
            )

    async def test_post_message_author_link_without_name_rejected(self, mcp_client, test_channel):
        """post_message: ValidationError for author_link without author_name."""
        with pytest.raises(Exception, match=r"author_name|validation"):
            await mcp_client.call_tool(
                "post_message",
                {
                    "channel_id": test_channel["id"],
                    "message": "Bad attachment",
                    "attachments": [{"author_link": "https://example.com", "text": "This should fail"}],
                },
            )
