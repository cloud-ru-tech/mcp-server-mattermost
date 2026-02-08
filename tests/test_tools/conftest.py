"""Shared fixtures for tool tests."""

from unittest.mock import AsyncMock

import pytest

from mcp_server_mattermost.exceptions import AuthenticationError, NotFoundError, RateLimitError


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create mock MattermostClient."""
    return AsyncMock()


@pytest.fixture
def mock_client_auth_error() -> AsyncMock:
    """Create mock client that raises AuthenticationError."""
    client = AsyncMock()
    client.get_channels.side_effect = AuthenticationError()
    client.get_channel.side_effect = AuthenticationError()
    client.create_post.side_effect = AuthenticationError()
    client.get_me.side_effect = AuthenticationError()
    client.get_bookmarks.side_effect = AuthenticationError()
    return client


@pytest.fixture
def mock_client_not_found() -> AsyncMock:
    """Create mock client that raises NotFoundError."""
    client = AsyncMock()
    client.get_channel.side_effect = NotFoundError("Channel not found")
    client.get_user.side_effect = NotFoundError("User not found")
    client.get_post.side_effect = NotFoundError("Post not found")
    client.get_team.side_effect = NotFoundError("Team not found")
    client.get_bookmarks.side_effect = NotFoundError("Bookmark not found")
    client.delete_bookmark.side_effect = NotFoundError("Bookmark not found")
    return client


@pytest.fixture
def mock_client_rate_limited() -> AsyncMock:
    """Create mock client that raises RateLimitError."""
    client = AsyncMock()
    client.get_channels.side_effect = RateLimitError(retry_after=30)
    client.search_posts.side_effect = RateLimitError(retry_after=30)
    return client


def make_post_data(
    post_id: str = "ps1234567890123456789012",
    message: str = "Hello, World!",
    **overrides,
) -> dict:
    """Create full post mock data.

    Most Post fields are required (no omitempty per Mattermost Go source).
    """
    return {
        "id": post_id,
        "create_at": 1706400000000,
        "update_at": 1706400000000,
        "delete_at": 0,
        "edit_at": 0,
        "user_id": "us1234567890123456789012",
        "channel_id": "ch1234567890123456789012",
        "root_id": "",
        "original_id": "",
        "message": message,
        "type": "",
        "hashtags": "",
        "file_ids": [],
        "pending_post_id": "",
        "is_pinned": False,
        **overrides,
    }


def make_post_list_data(
    posts: dict | None = None,
    order: list | None = None,
    **overrides,
) -> dict:
    """Create full post list mock data."""
    if posts is None:
        posts = {}
    if order is None:
        order = []
    return {
        "posts": posts,
        "order": order,
        "next_post_id": "",
        "prev_post_id": "",
        **overrides,
    }


def make_reaction_data(
    post_id: str = "ps1234567890123456789012",
    emoji_name: str = "thumbsup",
    **overrides,
) -> dict:
    """Create full reaction mock data.

    All Reaction fields are required per Mattermost Go source.
    """
    return {
        "user_id": "us1234567890123456789012",
        "post_id": post_id,
        "emoji_name": emoji_name,
        "create_at": 1706400000000,
        **overrides,
    }


def make_bookmark_data(
    bookmark_id: str = "bk1234567890123456789012",
    display_name: str = "Test Bookmark",
    bookmark_type: str = "link",
    **overrides,
) -> dict:
    """Create full bookmark mock data.

    All ChannelBookmark required fields per Mattermost Go source.
    """
    return {
        "id": bookmark_id,
        "create_at": 1706400000000,
        "update_at": 1706400000000,
        "delete_at": 0,
        "channel_id": "ch1234567890123456789012",
        "owner_id": "us1234567890123456789012",
        "file_id": "",
        "display_name": display_name,
        "sort_order": 0,
        "type": bookmark_type,
        **overrides,
    }
