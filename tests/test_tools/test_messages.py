"""Tests for message tools."""

from unittest.mock import AsyncMock

import httpx
import pytest
import respx

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
        assert result.truncated is False


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


class TestGetChannelMessagesValidation:
    """Tests for get_channel_messages mode-exclusivity validation."""

    async def test_rejects_unread_only_with_since(self, mock_settings) -> None:
        """unread_only=True with since=... must raise — modes are mutually exclusive."""
        from fastmcp import Client

        from mcp_server_mattermost.server import mcp

        async with Client(mcp) as client:
            with pytest.raises(Exception) as exc_info:
                await client.call_tool(
                    "get_channel_messages",
                    {"channel_id": "ch123456789012345678901234", "unread_only": True, "since": 1716620000000},
                )
        msg = str(exc_info.value).lower()
        assert "mutually exclusive" in msg or "cannot use both" in msg

    async def test_rejects_unread_only_with_pagination(self, mock_settings) -> None:
        """unread_only=True with non-default page must raise."""
        from fastmcp import Client

        from mcp_server_mattermost.server import mcp

        async with Client(mcp) as client:
            with pytest.raises(Exception) as exc_info:
                await client.call_tool(
                    "get_channel_messages",
                    {"channel_id": "ch123456789012345678901234", "unread_only": True, "page": 2},
                )
        msg = str(exc_info.value).lower()
        assert "page" in msg or "mutually exclusive" in msg or "pagination" in msg

    async def test_rejects_since_in_seconds(self, mock_settings) -> None:
        """since must be Unix milliseconds — values below 10^12 are rejected."""
        from fastmcp import Client

        from mcp_server_mattermost.server import mcp

        async with Client(mcp) as client:
            with pytest.raises(Exception):  # noqa: B017
                await client.call_tool(
                    "get_channel_messages",
                    {"channel_id": "ch123456789012345678901234", "since": 1716620000},  # seconds not ms
                )

    async def test_rejects_collapsed_threads_with_default_mode(self, mock_settings) -> None:
        """collapsed_threads=True without unread_only or since must raise."""
        from fastmcp import Client

        from mcp_server_mattermost.server import mcp

        async with Client(mcp) as client:
            with pytest.raises(Exception) as exc_info:
                await client.call_tool(
                    "get_channel_messages",
                    {"channel_id": "ch123456789012345678901234", "collapsed_threads": True},
                )
        msg = str(exc_info.value).lower()
        assert "collapsed_threads" in msg or "crt" in msg

    @pytest.mark.asyncio
    async def test_rejects_limit_after_zero(self, mock_settings) -> None:
        """limit_after=0 must be rejected at validation; Mattermost API returns HTTP 400 for it."""
        from fastmcp import Client

        from mcp_server_mattermost.server import mcp

        async with Client(mcp) as client:
            with pytest.raises(Exception) as exc_info:
                await client.call_tool(
                    "get_channel_messages",
                    {
                        "channel_id": "ch123456789012345678901234",
                        "unread_only": True,
                        "limit_after": 0,
                    },
                )
        msg = str(exc_info.value).lower()
        assert "limit_after" in msg or "greater" in msg or "ge" in msg


def _post_fixture(**overrides) -> dict:  # type: ignore[type-arg]
    base = {
        "id": "p",
        "create_at": 1,
        "update_at": 1,
        "delete_at": 0,
        "edit_at": 0,
        "user_id": "u",
        "channel_id": "ch",
        "root_id": "",
        "original_id": "",
        "message": "hi",
        "type": "",
        "hashtags": "",
        "file_ids": [],
        "pending_post_id": "",
        "is_pinned": False,
    }
    base.update(overrides)
    return base


class TestGetChannelMessagesRouting:
    """Tests for get_channel_messages routing and truncation detection."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_unread_mode_calls_posts_unread(self, mock_settings) -> None:
        """unread_only=True must hit /users/me/channels/{id}/posts/unread."""
        from fastmcp import Client

        from mcp_server_mattermost.server import mcp

        route = respx.get(
            "https://test.mattermost.com/api/v4/users/me/channels/ch123456789012345678901234/posts/unread"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "order": ["p1"],
                    "posts": {"p1": _post_fixture(id="p1", channel_id="ch123456789012345678901234")},
                },
            )
        )
        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_channel_messages",
                {"channel_id": "ch123456789012345678901234", "unread_only": True, "limit_after": 100},
            )
        assert route.called
        assert result.structured_content["order"] == ["p1"]
        assert result.structured_content["truncated"] is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_since_mode_calls_posts_with_since_param(self, mock_settings) -> None:
        """since=<ms> must hit /channels/{id}/posts with since query param."""
        from fastmcp import Client

        from mcp_server_mattermost.server import mcp

        route = respx.get("https://test.mattermost.com/api/v4/channels/ch123456789012345678901234/posts").mock(
            return_value=httpx.Response(200, json={"order": [], "posts": {}})
        )
        async with Client(mcp) as client:
            await client.call_tool(
                "get_channel_messages",
                {"channel_id": "ch123456789012345678901234", "since": 1716620000000},
            )
        assert route.called
        assert route.calls[0].request.url.params["since"] == "1716620000000"

    @pytest.mark.asyncio
    @respx.mock
    async def test_default_mode_calls_posts_with_pagination(self, mock_settings) -> None:
        """Default mode preserves existing pagination behavior."""
        from fastmcp import Client

        from mcp_server_mattermost.server import mcp

        route = respx.get("https://test.mattermost.com/api/v4/channels/ch123456789012345678901234/posts").mock(
            return_value=httpx.Response(200, json={"order": [], "posts": {}})
        )
        async with Client(mcp) as client:
            await client.call_tool("get_channel_messages", {"channel_id": "ch123456789012345678901234"})
        assert route.called
        assert route.calls[0].request.url.params["per_page"] == "60"

    @pytest.mark.asyncio
    @respx.mock
    async def test_truncated_when_unread_hits_cap(self, mock_settings) -> None:
        """truncated=True when len(order) >= limit_before + limit_after."""
        from fastmcp import Client

        from mcp_server_mattermost.server import mcp

        posts = {f"p{i}": _post_fixture(id=f"p{i}", channel_id="ch123456789012345678901234") for i in range(2)}
        respx.get("https://test.mattermost.com/api/v4/users/me/channels/ch123456789012345678901234/posts/unread").mock(
            return_value=httpx.Response(200, json={"order": list(posts), "posts": posts})
        )
        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_channel_messages",
                {"channel_id": "ch123456789012345678901234", "unread_only": True, "limit_after": 2},
            )
        assert result.structured_content["truncated"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_truncated_when_since_hits_1000(self, mock_settings) -> None:
        """truncated=True when since-mode response has exactly 1000 posts in order."""
        from fastmcp import Client

        from mcp_server_mattermost.server import mcp

        posts = {f"p{i}": _post_fixture(id=f"p{i}", channel_id="ch123456789012345678901234") for i in range(1000)}
        respx.get("https://test.mattermost.com/api/v4/channels/ch123456789012345678901234/posts").mock(
            return_value=httpx.Response(200, json={"order": list(posts), "posts": posts})
        )
        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_channel_messages",
                {"channel_id": "ch123456789012345678901234", "since": 1716620000000},
            )
        assert result.structured_content["truncated"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_truncated_when_default_hits_per_page(self, mock_settings) -> None:
        """truncated=True when default-mode response has len(order) >= per_page."""
        from fastmcp import Client

        from mcp_server_mattermost.server import mcp

        posts = {f"p{i}": _post_fixture(id=f"p{i}", channel_id="ch123456789012345678901234") for i in range(3)}
        respx.get("https://test.mattermost.com/api/v4/channels/ch123456789012345678901234/posts").mock(
            return_value=httpx.Response(200, json={"order": list(posts), "posts": posts})
        )
        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_channel_messages",
                {"channel_id": "ch123456789012345678901234", "per_page": 3},
            )
        assert result.structured_content["truncated"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_since_thread_context_does_not_falsely_truncate(self, mock_settings) -> None:
        """truncated must check len(order) not len(posts).

        950 posts in order + 50 context roots in posts (not in order) = len(posts)=1000
        but len(order)=950 < 1000 -> NOT truncated.
        """
        from fastmcp import Client

        from mcp_server_mattermost.server import mcp

        order = [f"p{i}" for i in range(950)]
        posts = {p: _post_fixture(id=p, channel_id="ch123456789012345678901234") for p in order}
        for i in range(50):
            ctx = f"ctx{i}"
            posts[ctx] = _post_fixture(id=ctx, channel_id="ch123456789012345678901234")
        respx.get("https://test.mattermost.com/api/v4/channels/ch123456789012345678901234/posts").mock(
            return_value=httpx.Response(200, json={"order": order, "posts": posts})
        )
        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_channel_messages",
                {"channel_id": "ch123456789012345678901234", "since": 1716620000000},
            )
        assert result.structured_content["truncated"] is False
