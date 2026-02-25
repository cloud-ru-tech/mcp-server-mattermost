"""Tests for post tools (reactions, pins, threads)."""

from unittest.mock import AsyncMock

from mcp_server_mattermost.models import Post, PostList, Reaction
from mcp_server_mattermost.tools import posts
from tests.test_tools.conftest import make_post_data, make_post_list_data, make_reaction_data


class TestAddReaction:
    """Tests for add_reaction tool."""

    async def test_add_reaction(self, mock_client: AsyncMock) -> None:
        """Test adding a reaction returns Reaction model."""
        mock_client.add_reaction.return_value = make_reaction_data()

        result = await posts.add_reaction(
            post_id="ps1234567890123456789012",
            emoji_name="thumbsup",
            client=mock_client,
        )

        assert isinstance(result, Reaction)
        assert result.emoji_name == "thumbsup"


class TestRemoveReaction:
    """Tests for remove_reaction tool."""

    async def test_remove_reaction(self, mock_client: AsyncMock) -> None:
        """Test removing a reaction."""
        mock_client.remove_reaction.return_value = None

        result = await posts.remove_reaction(
            post_id="ps1234567890123456789012",
            emoji_name="thumbsup",
            client=mock_client,
        )

        assert result is None


class TestGetReactions:
    """Tests for get_reactions tool."""

    async def test_get_reactions(self, mock_client: AsyncMock) -> None:
        """Test getting reactions returns list of Reaction models."""
        mock_client.get_reactions.return_value = [make_reaction_data()]

        result = await posts.get_reactions(
            post_id="ps1234567890123456789012",
            client=mock_client,
        )

        assert len(result) == 1
        assert isinstance(result[0], Reaction)


class TestPinMessage:
    """Tests for pin_message tool."""

    async def test_pin_message(self, mock_client: AsyncMock) -> None:
        """Test pinning a message returns Post model."""
        mock_client.pin_post.return_value = {"status": "OK"}
        mock_client.get_post.return_value = make_post_data(is_pinned=True)

        result = await posts.pin_message(
            post_id="ps1234567890123456789012",
            client=mock_client,
        )

        assert isinstance(result, Post)
        assert result.is_pinned is True
        mock_client.pin_post.assert_called_once()
        mock_client.get_post.assert_called_once()


class TestUnpinMessage:
    """Tests for unpin_message tool."""

    async def test_unpin_message(self, mock_client: AsyncMock) -> None:
        """Test unpinning a message returns Post model."""
        mock_client.unpin_post.return_value = {"status": "OK"}
        mock_client.get_post.return_value = make_post_data(is_pinned=False)

        result = await posts.unpin_message(
            post_id="ps1234567890123456789012",
            client=mock_client,
        )

        assert isinstance(result, Post)
        assert result.is_pinned is False
        mock_client.unpin_post.assert_called_once()
        mock_client.get_post.assert_called_once()


class TestGetThread:
    """Tests for get_thread tool."""

    async def test_get_thread(self, mock_client: AsyncMock) -> None:
        """Test getting a thread returns dict with posts and order."""
        thread_data = make_post_list_data(
            posts={
                "ps1": make_post_data(id="ps1", message="Root"),
                "ps2": make_post_data(id="ps2", message="Reply"),
            },
            order=["ps1", "ps2"],
        )
        mock_client.get_thread.return_value = thread_data

        result = await posts.get_thread(
            post_id="ps1234567890123456789012",
            client=mock_client,
        )

        assert isinstance(result, PostList)
        assert len(result.posts) == 2
        assert len(result.order) == 2
