"""Tests for user tools."""

from unittest.mock import AsyncMock

import pytest

from mcp_server_mattermost.exceptions import AuthenticationError, NotFoundError
from mcp_server_mattermost.models import User, UserStatus
from mcp_server_mattermost.tools import users


def make_user_data(
    user_id: str = "us1234567890123456789012",
    username: str = "testuser",
    **overrides,
) -> dict:
    """Create full user mock data.

    Most fields required per Go source. Optional fields have omitempty in Go.
    """
    return {
        "id": user_id,
        "delete_at": 0,
        "username": username,
        "first_name": "",
        "last_name": "",
        "nickname": "",
        "email": "test@example.com",
        "auth_service": "",
        "roles": "system_user",
        "locale": "en",
        "create_at": 1706400000000,
        "update_at": 1706400000000,
        **overrides,
    }


def make_user_status_data(
    user_id: str = "us1234567890123456789012",
    status: str = "online",
    **overrides,
) -> dict:
    """Create full user status mock data.

    All fields required per Go source.
    """
    return {
        "user_id": user_id,
        "status": status,
        "manual": False,
        "last_activity_at": 1706400000000,
        **overrides,
    }


class TestGetMe:
    """Tests for get_me tool."""

    async def test_get_me(self, mock_client: AsyncMock) -> None:
        """Test getting current user returns User model."""
        mock_client.get_me.return_value = make_user_data()

        result = await users.get_me(client=mock_client)

        assert isinstance(result, User)
        assert result.username == "testuser"


class TestGetUser:
    """Tests for get_user tool."""

    async def test_get_user(self, mock_client: AsyncMock) -> None:
        """Test getting user by ID returns User model."""
        mock_client.get_user.return_value = make_user_data()

        result = await users.get_user(
            user_id="us1234567890123456789012",
            client=mock_client,
        )

        assert isinstance(result, User)
        assert result.id == "us1234567890123456789012"


class TestGetUserByUsername:
    """Tests for get_user_by_username tool."""

    async def test_get_user_by_username(self, mock_client: AsyncMock) -> None:
        """Test getting user by username returns User model."""
        mock_client.get_user_by_username.return_value = make_user_data()

        result = await users.get_user_by_username(
            username="testuser",
            client=mock_client,
        )

        assert isinstance(result, User)
        assert result.username == "testuser"


class TestSearchUsers:
    """Tests for search_users tool."""

    async def test_search_users(self, mock_client: AsyncMock) -> None:
        """Test searching users returns list of User models."""
        mock_client.search_users.return_value = [make_user_data()]

        result = await users.search_users(
            term="test",
            client=mock_client,
        )

        assert len(result) == 1
        assert isinstance(result[0], User)

    async def test_search_users_with_team_filter(self, mock_client: AsyncMock) -> None:
        """Test searching users within a team."""
        mock_client.search_users.return_value = []

        await users.search_users(
            term="test",
            team_id="tm1234567890123456789012",
            client=mock_client,
        )

        mock_client.search_users.assert_called_once_with(
            term="test",
            team_id="tm1234567890123456789012",
        )


class TestGetUserStatus:
    """Tests for get_user_status tool."""

    async def test_get_user_status(self, mock_client: AsyncMock) -> None:
        """Test getting user status returns UserStatus model."""
        mock_client.get_user_status.return_value = make_user_status_data()

        result = await users.get_user_status(
            user_id="us1234567890123456789012",
            client=mock_client,
        )

        assert isinstance(result, UserStatus)
        assert result.status == "online"


class TestErrorHandling:
    """Tests for error handling in user tools."""

    async def test_get_me_auth_error(self, mock_client_auth_error: AsyncMock) -> None:
        """Test authentication error propagation."""
        with pytest.raises(AuthenticationError):
            await users.get_me(client=mock_client_auth_error)

    async def test_get_user_not_found(self, mock_client_not_found: AsyncMock) -> None:
        """Test not found error propagation."""
        with pytest.raises(NotFoundError):
            await users.get_user(
                user_id="us1234567890123456789012",
                client=mock_client_not_found,
            )


def test_get_me_has_tags():
    from mcp_server_mattermost.tools.users import get_me

    assert hasattr(get_me, "tags")
    assert "user" in get_me.tags
    assert "mattermost" in get_me.tags
