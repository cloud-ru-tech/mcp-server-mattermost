# tests/integration/test_bookmarks.py
"""Integration tests for bookmark tools via MCP protocol."""

import contextlib

import pytest

from tests.integration.utils import to_dict


async def cleanup_bookmark(mcp_client, channel_id: str, bookmark_id: str) -> None:
    """Helper to clean up test bookmarks."""
    with contextlib.suppress(Exception):
        await mcp_client.call_tool(
            "delete_bookmark",
            {"channel_id": channel_id, "bookmark_id": bookmark_id},
        )


class TestBookmarkHappyPath:
    """Basic successful bookmark operations through MCP protocol."""

    async def test_list_bookmarks_empty(self, mcp_client, test_channel):
        """list_bookmarks: returns empty list for channel without bookmarks."""
        result = await mcp_client.call_tool(
            "list_bookmarks",
            {"channel_id": test_channel["id"]},
        )

        bookmarks = to_dict(result)
        assert bookmarks == []

    async def test_create_link_bookmark(self, mcp_client, test_channel):
        """create_bookmark: creates link bookmark with URL."""
        bookmark_id = None

        try:
            result = await mcp_client.call_tool(
                "create_bookmark",
                {
                    "channel_id": test_channel["id"],
                    "display_name": "Test Link",
                    "bookmark_type": "link",
                    "link_url": "https://example.com",
                },
            )

            bookmark = to_dict(result)
            bookmark_id = bookmark["id"]
            assert bookmark["display_name"] == "Test Link"
            assert bookmark["type"] == "link"
            assert bookmark["link_url"] == "https://example.com"
        finally:
            if bookmark_id:
                await cleanup_bookmark(mcp_client, test_channel["id"], bookmark_id)

    async def test_create_bookmark_with_emoji(self, mcp_client, test_channel):
        """create_bookmark: creates bookmark with emoji icon."""
        bookmark_id = None

        try:
            result = await mcp_client.call_tool(
                "create_bookmark",
                {
                    "channel_id": test_channel["id"],
                    "display_name": "Docs",
                    "bookmark_type": "link",
                    "link_url": "https://docs.example.com",
                    "emoji": "book",
                },
            )

            bookmark = to_dict(result)
            bookmark_id = bookmark["id"]
            assert bookmark["emoji"] == "book"
        finally:
            if bookmark_id:
                await cleanup_bookmark(mcp_client, test_channel["id"], bookmark_id)

    async def test_list_bookmarks_after_create(self, mcp_client, test_channel):
        """list_bookmarks: returns created bookmark."""
        bookmark_id = None

        try:
            # Create bookmark
            create_result = await mcp_client.call_tool(
                "create_bookmark",
                {
                    "channel_id": test_channel["id"],
                    "display_name": "List Test",
                    "bookmark_type": "link",
                    "link_url": "https://example.com",
                },
            )
            bookmark_id = to_dict(create_result.data)["id"]

            # List bookmarks
            list_result = await mcp_client.call_tool(
                "list_bookmarks",
                {"channel_id": test_channel["id"]},
            )

            bookmarks = to_dict(list_result.data)
            assert len(bookmarks) >= 1
            assert any(b["id"] == bookmark_id for b in bookmarks)
        finally:
            if bookmark_id:
                await cleanup_bookmark(mcp_client, test_channel["id"], bookmark_id)

    async def test_update_bookmark_display_name(self, mcp_client, test_channel):
        """update_bookmark: updates display_name."""
        bookmark_id = None

        try:
            # Create
            create_result = await mcp_client.call_tool(
                "create_bookmark",
                {
                    "channel_id": test_channel["id"],
                    "display_name": "Original Name",
                    "bookmark_type": "link",
                    "link_url": "https://example.com",
                },
            )
            bookmark_id = to_dict(create_result.data)["id"]

            # Update
            update_result = await mcp_client.call_tool(
                "update_bookmark",
                {
                    "channel_id": test_channel["id"],
                    "bookmark_id": bookmark_id,
                    "display_name": "Updated Name",
                },
            )

            bookmark = to_dict(update_result.data)
            assert bookmark["display_name"] == "Updated Name"
        finally:
            if bookmark_id:
                await cleanup_bookmark(mcp_client, test_channel["id"], bookmark_id)

    async def test_delete_bookmark(self, mcp_client, test_channel):
        """delete_bookmark: soft deletes bookmark (sets delete_at)."""
        # Create
        create_result = await mcp_client.call_tool(
            "create_bookmark",
            {
                "channel_id": test_channel["id"],
                "display_name": "To Delete",
                "bookmark_type": "link",
                "link_url": "https://example.com",
            },
        )
        bookmark_id = to_dict(create_result.data)["id"]

        # Delete
        delete_result = await mcp_client.call_tool(
            "delete_bookmark",
            {
                "channel_id": test_channel["id"],
                "bookmark_id": bookmark_id,
            },
        )

        bookmark = to_dict(delete_result.data)
        assert bookmark["delete_at"] > 0


class TestBookmarkValidation:
    """Bookmark validation through MCP protocol."""

    async def test_create_link_bookmark_without_url(self, mcp_client, test_channel):
        """create_bookmark: ValidationError when type=link but no link_url."""
        with pytest.raises(Exception, match=r"link_url.*required"):
            await mcp_client.call_tool(
                "create_bookmark",
                {
                    "channel_id": test_channel["id"],
                    "display_name": "No URL",
                    "bookmark_type": "link",
                },
            )

    async def test_create_file_bookmark_without_file_id(self, mcp_client, test_channel):
        """create_bookmark: ValidationError when type=file but no file_id."""
        with pytest.raises(Exception, match=r"file_id.*required"):
            await mcp_client.call_tool(
                "create_bookmark",
                {
                    "channel_id": test_channel["id"],
                    "display_name": "No File",
                    "bookmark_type": "file",
                },
            )

    async def test_create_bookmark_empty_display_name(self, mcp_client, test_channel):
        """create_bookmark: ValidationError for empty display_name."""
        with pytest.raises(Exception, match=r"validation|display_name|empty|min"):
            await mcp_client.call_tool(
                "create_bookmark",
                {
                    "channel_id": test_channel["id"],
                    "display_name": "",
                    "bookmark_type": "link",
                    "link_url": "https://example.com",
                },
            )


class TestBookmarkPermissions:
    """Bookmark permission boundaries through MCP protocol."""

    async def test_list_bookmarks_invalid_channel(self, mcp_client):
        """list_bookmarks: 404 for non-existent channel."""
        fake_id = "a" * 26
        with pytest.raises(Exception, match=r"404|not found"):
            await mcp_client.call_tool(
                "list_bookmarks",
                {"channel_id": fake_id},
            )

    async def test_delete_bookmark_not_found(self, mcp_client, test_channel):
        """delete_bookmark: 404 for non-existent bookmark."""
        fake_id = "a" * 26
        with pytest.raises(Exception, match=r"404|not found"):
            await mcp_client.call_tool(
                "delete_bookmark",
                {
                    "channel_id": test_channel["id"],
                    "bookmark_id": fake_id,
                },
            )
