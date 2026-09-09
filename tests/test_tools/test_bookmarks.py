"""Tests for bookmark tools."""

from unittest.mock import AsyncMock

import pytest
import respx
from fastmcp import Client

from mcp_server_mattermost.exceptions import AuthenticationError, NotFoundError, ValidationError
from mcp_server_mattermost.models import ChannelBookmark, FileInfo
from mcp_server_mattermost.tools import bookmarks

from .conftest import make_bookmark_data


class TestListBookmarks:
    """Tests for list_bookmarks tool."""

    async def test_list_bookmarks_returns_file_metadata(self, mock_client, file_bookmark_data):
        mock_client.get_bookmarks.return_value = [file_bookmark_data]

        result = await bookmarks.list_bookmarks(channel_id=file_bookmark_data["channel_id"], client=mock_client)

        assert isinstance(result[0].file_info, FileInfo)
        assert result[0].file_info.name == "doc.pdf"

    async def test_list_bookmarks_returns_bookmarks(self, mock_client: AsyncMock) -> None:
        """Test successful bookmark listing returns ChannelBookmark models."""
        mock_client.get_bookmarks.return_value = [make_bookmark_data()]

        result = await bookmarks.list_bookmarks(
            channel_id="ch1234567890123456789012",
            client=mock_client,
        )

        assert len(result) == 1
        assert isinstance(result[0], ChannelBookmark)
        assert result[0].id == "bk1234567890123456789012"
        assert result[0].display_name == "Test Bookmark"
        mock_client.get_bookmarks.assert_called_once_with(
            channel_id="ch1234567890123456789012",
            bookmarks_since=None,
        )

    async def test_list_bookmarks_empty(self, mock_client: AsyncMock) -> None:
        """Test empty bookmark list."""
        mock_client.get_bookmarks.return_value = []

        result = await bookmarks.list_bookmarks(
            channel_id="ch1234567890123456789012",
            client=mock_client,
        )

        assert result == []

    async def test_list_bookmarks_with_since_filter(self, mock_client: AsyncMock) -> None:
        """Test bookmarks_since parameter is passed through."""
        mock_client.get_bookmarks.return_value = [make_bookmark_data()]

        await bookmarks.list_bookmarks(
            channel_id="ch1234567890123456789012",
            bookmarks_since=1706400000000,
            client=mock_client,
        )

        mock_client.get_bookmarks.assert_called_once_with(
            channel_id="ch1234567890123456789012",
            bookmarks_since=1706400000000,
        )


class TestCreateBookmark:
    """Tests for create_bookmark tool."""

    async def test_create_link_bookmark(self, mock_client: AsyncMock) -> None:
        """Test creating a link bookmark returns ChannelBookmark."""
        mock_client.create_bookmark.return_value = make_bookmark_data(
            link_url="https://example.com",
        )

        result = await bookmarks.create_bookmark(
            channel_id="ch1234567890123456789012",
            display_name="Test Bookmark",
            bookmark_type="link",
            link_url="https://example.com",
            client=mock_client,
        )

        assert isinstance(result, ChannelBookmark)
        assert result.link_url == "https://example.com"
        mock_client.create_bookmark.assert_called_once_with(
            channel_id="ch1234567890123456789012",
            display_name="Test Bookmark",
            bookmark_type="link",
            link_url="https://example.com",
            file_id=None,
            emoji=None,
            image_url=None,
        )

    async def test_create_file_bookmark(self, mock_client: AsyncMock, file_bookmark_data) -> None:
        """Test creating a file bookmark returns ChannelBookmark."""
        mock_client.create_bookmark.return_value = file_bookmark_data

        result = await bookmarks.create_bookmark(
            channel_id=file_bookmark_data["channel_id"],
            display_name="Test File",
            bookmark_type="file",
            file_id=file_bookmark_data["file_id"],
            client=mock_client,
        )

        assert isinstance(result, ChannelBookmark)
        assert result.type == "file"
        assert result.file_id == "fl123456789012345678901234"
        assert isinstance(result.file_info, FileInfo)
        assert result.file_info.name == "doc.pdf"

    async def test_create_link_bookmark_missing_url(self, mock_client: AsyncMock) -> None:
        """Test link bookmark without link_url raises ValidationError."""
        with pytest.raises(ValidationError, match="link_url is required"):
            await bookmarks.create_bookmark(
                channel_id="ch1234567890123456789012",
                display_name="Test Bookmark",
                bookmark_type="link",
                client=mock_client,
            )

    async def test_create_file_bookmark_missing_file_id(self, mock_client: AsyncMock) -> None:
        """Test file bookmark without file_id raises ValidationError."""
        with pytest.raises(ValidationError, match="file_id is required"):
            await bookmarks.create_bookmark(
                channel_id="ch1234567890123456789012",
                display_name="Test File",
                bookmark_type="file",
                client=mock_client,
            )

    async def test_create_bookmark_with_optional_fields(self, mock_client: AsyncMock) -> None:
        """Test optional emoji and image_url are passed through."""
        mock_client.create_bookmark.return_value = make_bookmark_data(
            link_url="https://example.com",
            emoji="bookmark",
            image_url="https://example.com/preview.png",
        )

        await bookmarks.create_bookmark(
            channel_id="ch1234567890123456789012",
            display_name="Test Bookmark",
            bookmark_type="link",
            link_url="https://example.com",
            emoji="bookmark",
            image_url="https://example.com/preview.png",
            client=mock_client,
        )

        mock_client.create_bookmark.assert_called_once_with(
            channel_id="ch1234567890123456789012",
            display_name="Test Bookmark",
            bookmark_type="link",
            link_url="https://example.com",
            file_id=None,
            emoji="bookmark",
            image_url="https://example.com/preview.png",
        )


class TestUpdateBookmark:
    """Tests for update_bookmark tool."""

    async def test_update_bookmark_display_name(self, mock_client: AsyncMock) -> None:
        """Test updating only display_name passes correct fields."""
        mock_client.update_bookmark.return_value = make_bookmark_data(display_name="Updated")

        result = await bookmarks.update_bookmark(
            channel_id="ch1234567890123456789012",
            bookmark_id="bk1234567890123456789012",
            display_name="Updated",
            client=mock_client,
        )

        assert isinstance(result, ChannelBookmark)
        assert result.display_name == "Updated"
        mock_client.update_bookmark.assert_called_once_with(
            channel_id="ch1234567890123456789012",
            bookmark_id="bk1234567890123456789012",
            display_name="Updated",
        )

    async def test_update_bookmark_multiple_fields(self, mock_client: AsyncMock) -> None:
        """Test updating multiple fields at once."""
        mock_client.update_bookmark.return_value = make_bookmark_data(
            display_name="New Name",
            link_url="https://new.com",
            emoji="star",
        )

        await bookmarks.update_bookmark(
            channel_id="ch1234567890123456789012",
            bookmark_id="bk1234567890123456789012",
            display_name="New Name",
            link_url="https://new.com",
            emoji="star",
            client=mock_client,
        )

        mock_client.update_bookmark.assert_called_once_with(
            channel_id="ch1234567890123456789012",
            bookmark_id="bk1234567890123456789012",
            display_name="New Name",
            link_url="https://new.com",
            emoji="star",
        )

    async def test_update_bookmark_no_fields(self, mock_client: AsyncMock) -> None:
        """Test calling update with no optional fields passes empty kwargs."""
        mock_client.update_bookmark.return_value = make_bookmark_data()

        await bookmarks.update_bookmark(
            channel_id="ch1234567890123456789012",
            bookmark_id="bk1234567890123456789012",
            client=mock_client,
        )

        mock_client.update_bookmark.assert_called_once_with(
            channel_id="ch1234567890123456789012",
            bookmark_id="bk1234567890123456789012",
        )


class TestDeleteBookmark:
    """Tests for delete_bookmark tool."""

    async def test_delete_bookmark(self, mock_client: AsyncMock) -> None:
        """Test deleting a bookmark returns ChannelBookmark with delete_at set."""
        mock_client.delete_bookmark.return_value = make_bookmark_data(delete_at=1706400001000)

        result = await bookmarks.delete_bookmark(
            channel_id="ch1234567890123456789012",
            bookmark_id="bk1234567890123456789012",
            client=mock_client,
        )

        assert isinstance(result, ChannelBookmark)
        assert result.delete_at > 0
        mock_client.delete_bookmark.assert_called_once_with(
            channel_id="ch1234567890123456789012",
            bookmark_id="bk1234567890123456789012",
        )


class TestUpdateBookmarkSortOrder:
    """Tests for update_bookmark_sort_order tool."""

    async def test_update_bookmark_sort_order(self, mock_client: AsyncMock) -> None:
        """Test reordering returns list of ChannelBookmark models."""
        mock_client.update_bookmark_sort_order.return_value = [
            make_bookmark_data(bookmark_id="bk1234567890123456789012", sort_order=0),
            make_bookmark_data(bookmark_id="bk2234567890123456789012", sort_order=1),
        ]

        result = await bookmarks.update_bookmark_sort_order(
            channel_id="ch1234567890123456789012",
            bookmark_id="bk1234567890123456789012",
            new_sort_order=0,
            client=mock_client,
        )

        assert len(result) == 2
        assert all(isinstance(b, ChannelBookmark) for b in result)
        mock_client.update_bookmark_sort_order.assert_called_once_with(
            channel_id="ch1234567890123456789012",
            bookmark_id="bk1234567890123456789012",
            new_sort_order=0,
        )


@pytest.mark.parametrize("tool_name", ["list_bookmarks", "create_bookmark"])
@respx.mock
async def test_file_bookmark_mcp_response_and_schema(mock_settings, file_bookmark_data, tool_name):
    """Expose file metadata under the same typed key in MCP results and schemas."""
    from mcp_server_mattermost.server import mcp

    channel_id = file_bookmark_data["channel_id"]
    url = f"https://test.mattermost.com/api/v4/channels/{channel_id}/bookmarks"
    arguments = {"channel_id": channel_id}
    if tool_name == "list_bookmarks":
        respx.get(url).respond(200, json=[file_bookmark_data])
    else:
        respx.post(url).respond(200, json=file_bookmark_data)
        arguments.update(
            display_name="Important Document",
            bookmark_type="file",
            file_id=file_bookmark_data["file_id"],
        )

    async with Client(mcp) as client:
        tool = next(tool for tool in await client.list_tools() if tool.name == tool_name)
        result = await client.call_tool(tool_name, arguments)

    schema = tool.outputSchema
    data = result.structured_content
    if tool_name == "list_bookmarks":
        schema = schema["properties"]["result"]["items"]
        data = data["result"][0]

    assert "file_info" not in data
    assert data["file"]["id"] == "fl123456789012345678901234"
    assert data["file"]["name"] == "doc.pdf"
    assert data["file"]["size"] == 1024
    assert "mini_preview" in data["file"]
    assert "file_info" not in schema["properties"]
    file_schema = next(variant for variant in schema["properties"]["file"]["anyOf"] if variant["type"] == "object")
    assert file_schema["properties"]["name"]["type"] == "string"
    assert file_schema["properties"]["size"]["type"] == "integer"


class TestErrorHandling:
    """Tests for error handling in bookmark tools."""

    async def test_list_bookmarks_auth_error(self, mock_client_auth_error: AsyncMock) -> None:
        """Test authentication error propagation."""
        with pytest.raises(AuthenticationError):
            await bookmarks.list_bookmarks(
                channel_id="ch1234567890123456789012",
                client=mock_client_auth_error,
            )

    async def test_list_bookmarks_not_found(self, mock_client_not_found: AsyncMock) -> None:
        """Test not found error propagation."""
        with pytest.raises(NotFoundError):
            await bookmarks.list_bookmarks(
                channel_id="ch1234567890123456789012",
                client=mock_client_not_found,
            )
