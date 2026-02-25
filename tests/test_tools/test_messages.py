"""Tests for message tools."""

from unittest.mock import AsyncMock

import pytest

from mcp_server_mattermost.exceptions import AuthenticationError, RateLimitError
from mcp_server_mattermost.models import Post, PostList
from mcp_server_mattermost.tools import messages
from tests.test_tools.conftest import make_post_data, make_post_list_data


class TestPostMessage:
    """Tests for post_message tool."""

    async def test_post_message(self, mock_client: AsyncMock) -> None:
        """Test posting a message returns Post model."""
        mock_client.create_post.return_value = make_post_data()

        result = await messages.post_message(
            channel_id="ch1234567890123456789012",
            message="Hello, World!",
            client=mock_client,
        )

        assert isinstance(result, Post)
        assert result.message == "Hello, World!"
        mock_client.create_post.assert_called_once_with(
            channel_id="ch1234567890123456789012",
            message="Hello, World!",
            root_id=None,
            file_ids=None,
            props=None,
        )

    async def test_post_message_with_thread(self, mock_client: AsyncMock) -> None:
        """Test posting a reply in thread returns Post model."""
        mock_client.create_post.return_value = make_post_data(root_id="rt1234567890123456789012")

        result = await messages.post_message(
            channel_id="ch1234567890123456789012",
            message="Reply",
            root_id="rt1234567890123456789012",
            client=mock_client,
        )

        assert isinstance(result, Post)
        assert result.root_id == "rt1234567890123456789012"

    async def test_post_message_with_file_ids(self, mock_client: AsyncMock) -> None:
        """Test posting a message with file attachments returns Post model."""
        mock_client.create_post.return_value = make_post_data(file_ids=["fl1234567890123456789012"])

        result = await messages.post_message(
            channel_id="ch1234567890123456789012",
            message="Check this file",
            file_ids=["fl1234567890123456789012"],
            client=mock_client,
        )

        assert isinstance(result, Post)
        assert result.file_ids == ["fl1234567890123456789012"]
        mock_client.create_post.assert_called_once_with(
            channel_id="ch1234567890123456789012",
            message="Check this file",
            root_id=None,
            file_ids=["fl1234567890123456789012"],
            props=None,
        )


class TestGetChannelMessages:
    """Tests for get_channel_messages tool."""

    async def test_get_channel_messages(self, mock_client: AsyncMock) -> None:
        """Test getting channel messages returns dict with posts and order."""
        messages_data = make_post_list_data(
            posts={"ps1": make_post_data(id="ps1", message="Hello")},
            order=["ps1"],
        )
        mock_client.get_posts.return_value = messages_data

        result = await messages.get_channel_messages(
            channel_id="ch1234567890123456789012",
            page=0,
            per_page=60,
            client=mock_client,
        )

        assert isinstance(result, PostList)
        assert "ps1" in result.posts


class TestSearchMessages:
    """Tests for search_messages tool."""

    async def test_search_messages(self, mock_client: AsyncMock) -> None:
        """Test searching messages returns dict with posts and order."""
        search_data = make_post_list_data()
        mock_client.search_posts.return_value = search_data

        result = await messages.search_messages(
            team_id="tm1234567890123456789012",
            terms="hello",
            client=mock_client,
        )

        assert isinstance(result, PostList)
        assert result.posts == {}


class TestUpdateMessage:
    """Tests for update_message tool."""

    async def test_update_message(self, mock_client: AsyncMock) -> None:
        """Test updating a message returns Post model."""
        mock_client.update_post.return_value = make_post_data(message="Updated message")

        result = await messages.update_message(
            post_id="ps1234567890123456789012",
            message="Updated message",
            client=mock_client,
        )

        assert isinstance(result, Post)
        assert result.message == "Updated message"


class TestDeleteMessage:
    """Tests for delete_message tool."""

    async def test_delete_message(self, mock_client: AsyncMock) -> None:
        """Test deleting a message."""
        mock_client.delete_post.return_value = None

        result = await messages.delete_message(
            post_id="ps1234567890123456789012",
            client=mock_client,
        )

        assert result is None


class TestPostMessageWithAttachments:
    """Tests for post_message with attachments."""

    async def test_post_message_with_simple_attachment(self, mock_client: AsyncMock) -> None:
        """Test posting message with simple attachment."""
        from mcp_server_mattermost.models import Attachment

        mock_client.create_post.return_value = make_post_data()

        result = await messages.post_message(
            channel_id="ch1234567890123456789012",
            message="Status update",
            attachments=[Attachment(color="good", text="All systems operational")],
            client=mock_client,
        )

        assert isinstance(result, Post)
        mock_client.create_post.assert_called_once()
        call_kwargs = mock_client.create_post.call_args.kwargs
        assert call_kwargs["props"] == {"attachments": [{"color": "good", "text": "All systems operational"}]}

    async def test_post_message_with_full_attachment(self, mock_client: AsyncMock) -> None:
        """Test posting message with full attachment including fields."""
        from mcp_server_mattermost.models import Attachment, AttachmentField

        mock_client.create_post.return_value = make_post_data()

        attachment = Attachment(
            color="warning",
            title="Task #123",
            title_link="https://tasks.example.com/123",
            text="Task needs attention",
            fields=[
                AttachmentField(title="Assignee", value="@john", short=True),
                AttachmentField(title="Priority", value="High", short=True),
            ],
            footer="Task Bot",
            ts=1706400000,
        )

        result = await messages.post_message(
            channel_id="ch1234567890123456789012",
            message="Task update",
            attachments=[attachment],
            client=mock_client,
        )

        assert isinstance(result, Post)
        call_kwargs = mock_client.create_post.call_args.kwargs
        props = call_kwargs["props"]
        assert len(props["attachments"]) == 1
        assert props["attachments"][0]["color"] == "warning"
        assert props["attachments"][0]["fields"] == [
            {"title": "Assignee", "value": "@john", "short": True},
            {"title": "Priority", "value": "High", "short": True},
        ]

    async def test_post_message_without_attachments_no_props(self, mock_client: AsyncMock) -> None:
        """Test posting message without attachments does not send props."""
        mock_client.create_post.return_value = make_post_data()

        await messages.post_message(
            channel_id="ch1234567890123456789012",
            message="Simple message",
            client=mock_client,
        )

        call_kwargs = mock_client.create_post.call_args.kwargs
        assert call_kwargs.get("props") is None


class TestUpdateMessageWithAttachments:
    """Tests for update_message with attachments."""

    async def test_update_message_with_attachment(self, mock_client: AsyncMock) -> None:
        """Test updating message with attachment."""
        from mcp_server_mattermost.models import Attachment

        mock_client.update_post.return_value = make_post_data(message="Updated")

        result = await messages.update_message(
            post_id="ps1234567890123456789012",
            message="Updated message",
            attachments=[Attachment(color="danger", text="Alert!")],
            client=mock_client,
        )

        assert isinstance(result, Post)
        call_kwargs = mock_client.update_post.call_args.kwargs
        assert call_kwargs["props"] == {"attachments": [{"color": "danger", "text": "Alert!"}]}

    async def test_update_message_without_attachments_no_props(self, mock_client: AsyncMock) -> None:
        """Test updating message without attachments does not send props."""
        mock_client.update_post.return_value = make_post_data(message="Updated")

        await messages.update_message(
            post_id="ps1234567890123456789012",
            message="Updated message",
            client=mock_client,
        )

        call_kwargs = mock_client.update_post.call_args.kwargs
        assert call_kwargs.get("props") is None


class TestErrorHandling:
    """Tests for error handling in message tools."""

    async def test_post_message_auth_error(self, mock_client_auth_error: AsyncMock) -> None:
        """Test authentication error propagation."""
        with pytest.raises(AuthenticationError):
            await messages.post_message(
                channel_id="ch1234567890123456789012",
                message="Test",
                client=mock_client_auth_error,
            )

    async def test_search_messages_rate_limited(self, mock_client_rate_limited: AsyncMock) -> None:
        """Test rate limit error propagation."""
        with pytest.raises(RateLimitError):
            await messages.search_messages(
                team_id="tm1234567890123456789012",
                terms="test",
                client=mock_client_rate_limited,
            )


def test_post_message_has_tags():
    from mcp_server_mattermost.tools.messages import post_message

    assert hasattr(post_message, "tags")
    assert "message" in post_message.tags
    assert "mattermost" in post_message.tags


def test_search_messages_has_tags():
    from mcp_server_mattermost.tools.messages import search_messages

    assert hasattr(search_messages, "tags")
    assert "message" in search_messages.tags
    assert "mattermost" in search_messages.tags
