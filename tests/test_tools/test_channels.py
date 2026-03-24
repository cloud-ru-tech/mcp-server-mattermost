"""Tests for channel tools."""

from unittest.mock import AsyncMock

import pytest

from mcp_server_mattermost.exceptions import AuthenticationError, NotFoundError
from mcp_server_mattermost.models import Channel, ChannelMember
from mcp_server_mattermost.tools import channels


def make_channel_data(
    channel_id: str = "ch1234567890123456789012",
    name: str = "general",
    **overrides,
) -> dict:
    """Create full channel mock data.

    All fields required per Go source.
    """
    return {
        "id": channel_id,
        "create_at": 1706400000000,
        "update_at": 1706400000000,
        "delete_at": 0,
        "team_id": "tm1234567890123456789012",
        "type": "O",
        "display_name": "General",
        "name": name,
        "header": "",
        "purpose": "",
        "last_post_at": 0,
        "total_msg_count": 0,
        "creator_id": "",
        **overrides,
    }


def make_channel_member_data(
    channel_id: str = "ch1234567890123456789012",
    user_id: str = "us1234567890123456789012",
    **overrides,
) -> dict:
    """Create full channel member mock data.

    All fields required per Go source.
    """
    return {
        "channel_id": channel_id,
        "user_id": user_id,
        "roles": "channel_user",
        "last_viewed_at": 0,
        "msg_count": 0,
        "mention_count": 0,
        "last_update_at": 0,
        **overrides,
    }


class TestListPublicChannels:
    """Tests for list_public_channels tool."""

    async def test_list_public_channels_returns_channels(self, mock_client: AsyncMock) -> None:
        """Test successful channel listing returns Channel models."""
        mock_client.get_public_channels.return_value = [make_channel_data()]

        result = await channels.list_public_channels(
            team_id="tm1234567890123456789012",
            page=0,
            per_page=60,
            client=mock_client,
        )

        assert len(result) == 1
        assert isinstance(result[0], Channel)
        assert result[0].id == "ch1234567890123456789012"
        assert result[0].name == "general"
        mock_client.get_public_channels.assert_called_once_with(
            team_id="tm1234567890123456789012",
            page=0,
            per_page=60,
        )


class TestListMyChannels:
    """Tests for list_my_channels tool."""

    async def test_list_my_channels_returns_all_types(self, mock_client: AsyncMock) -> None:
        """Test returns all channel types when channel_types is None."""
        mock_client.get_my_channels.return_value = [
            make_channel_data(channel_id="ch_o00000000000000000000", name="public", type="O"),
            make_channel_data(channel_id="ch_p00000000000000000000", name="private", type="P"),
            make_channel_data(channel_id="ch_d00000000000000000000", name="dm", type="D"),
            make_channel_data(channel_id="ch_g00000000000000000000", name="group", type="G"),
        ]

        result = await channels.list_my_channels(
            team_id="tm1234567890123456789012",
            client=mock_client,
        )

        assert len(result) == 4
        assert all(isinstance(ch, Channel) for ch in result)
        mock_client.get_my_channels.assert_called_once_with(team_id="tm1234567890123456789012")

    async def test_list_my_channels_filters_by_type(self, mock_client: AsyncMock) -> None:
        """Test filters channels when channel_types is specified."""
        mock_client.get_my_channels.return_value = [
            make_channel_data(channel_id="ch_o00000000000000000000", name="public", type="O"),
            make_channel_data(channel_id="ch_p00000000000000000000", name="private", type="P"),
            make_channel_data(channel_id="ch_d00000000000000000000", name="dm", type="D"),
            make_channel_data(channel_id="ch_g00000000000000000000", name="group", type="G"),
        ]

        result = await channels.list_my_channels(
            team_id="tm1234567890123456789012",
            channel_types=["O", "P"],
            client=mock_client,
        )

        assert len(result) == 2
        types = {ch.type for ch in result}
        assert types == {"O", "P"}

    async def test_list_my_channels_filter_single_type(self, mock_client: AsyncMock) -> None:
        """Test filters to a single channel type."""
        mock_client.get_my_channels.return_value = [
            make_channel_data(channel_id="ch_o00000000000000000000", name="public", type="O"),
            make_channel_data(channel_id="ch_p00000000000000000000", name="private", type="P"),
            make_channel_data(channel_id="ch_d00000000000000000000", name="dm", type="D"),
            make_channel_data(channel_id="ch_g00000000000000000000", name="group", type="G"),
        ]

        result = await channels.list_my_channels(
            team_id="tm1234567890123456789012",
            channel_types=["D"],
            client=mock_client,
        )

        assert len(result) == 1
        assert result[0].type == "D"

    async def test_list_my_channels_empty_result(self, mock_client: AsyncMock) -> None:
        """Test empty list when no channels."""
        mock_client.get_my_channels.return_value = []

        result = await channels.list_my_channels(
            team_id="tm1234567890123456789012",
            client=mock_client,
        )

        assert result == []


class TestGetChannel:
    """Tests for get_channel tool."""

    async def test_get_channel_by_id(self, mock_client: AsyncMock) -> None:
        """Test getting channel by ID returns Channel model."""
        mock_client.get_channel.return_value = make_channel_data()

        result = await channels.get_channel(
            channel_id="ch1234567890123456789012",
            client=mock_client,
        )

        assert isinstance(result, Channel)
        assert result.name == "general"
        mock_client.get_channel.assert_called_once_with(channel_id="ch1234567890123456789012")


class TestGetChannelByName:
    """Tests for get_channel_by_name tool."""

    async def test_get_channel_by_name(self, mock_client: AsyncMock) -> None:
        """Test getting channel by name returns Channel model."""
        mock_client.get_channel_by_name.return_value = make_channel_data()

        result = await channels.get_channel_by_name(
            team_id="tm1234567890123456789012",
            channel_name="general",
            client=mock_client,
        )

        assert isinstance(result, Channel)
        assert result.id == "ch1234567890123456789012"


class TestCreateChannel:
    """Tests for create_channel tool."""

    async def test_create_public_channel(self, mock_client: AsyncMock) -> None:
        """Test creating a public channel returns Channel model."""
        mock_client.create_channel.return_value = make_channel_data(name="new-channel", type="O")

        result = await channels.create_channel(
            team_id="tm1234567890123456789012",
            name="new-channel",
            display_name="New Channel",
            channel_type="O",
            purpose="Test purpose",
            header="Test header",
            client=mock_client,
        )

        assert isinstance(result, Channel)
        assert result.type == "O"


class TestJoinChannel:
    """Tests for join_channel tool."""

    async def test_join_channel(self, mock_client: AsyncMock) -> None:
        """Test joining a channel returns ChannelMember model."""
        mock_client.join_channel.return_value = make_channel_member_data()

        result = await channels.join_channel(
            channel_id="ch1234567890123456789012",
            client=mock_client,
        )

        assert isinstance(result, ChannelMember)
        assert result.channel_id == "ch1234567890123456789012"


class TestLeaveChannel:
    """Tests for leave_channel tool."""

    async def test_leave_channel(self, mock_client: AsyncMock) -> None:
        """Test leaving a channel."""
        mock_client.leave_channel.return_value = None

        result = await channels.leave_channel(
            channel_id="ch1234567890123456789012",
            client=mock_client,
        )

        assert result is None


class TestGetChannelMembers:
    """Tests for get_channel_members tool."""

    async def test_get_channel_members(self, mock_client: AsyncMock) -> None:
        """Test getting channel members returns ChannelMember models."""
        mock_client.get_channel_members.return_value = [make_channel_member_data()]

        result = await channels.get_channel_members(
            channel_id="ch1234567890123456789012",
            page=0,
            per_page=60,
            client=mock_client,
        )

        assert len(result) == 1
        assert isinstance(result[0], ChannelMember)


class TestAddUserToChannel:
    """Tests for add_user_to_channel tool."""

    async def test_add_user_to_channel(self, mock_client: AsyncMock) -> None:
        """Test adding user to channel returns ChannelMember model."""
        mock_client.add_user_to_channel.return_value = make_channel_member_data()

        result = await channels.add_user_to_channel(
            channel_id="ch1234567890123456789012",
            user_id="us1234567890123456789012",
            client=mock_client,
        )

        assert isinstance(result, ChannelMember)
        assert result.user_id == "us1234567890123456789012"


class TestCreateDirectChannel:
    """Tests for create_direct_channel tool."""

    async def test_create_direct_channel(self, mock_client: AsyncMock) -> None:
        """Test creating a direct message channel returns Channel model."""
        mock_client.create_direct_channel.return_value = make_channel_data(
            id="dm1234567890123456789012",
            type="D",
        )

        result = await channels.create_direct_channel(
            user_id_1="us1234567890123456789012",
            user_id_2="us2234567890123456789012",
            client=mock_client,
        )

        assert isinstance(result, Channel)
        assert result.type == "D"
        mock_client.create_direct_channel.assert_called_once_with(
            user_ids=["us1234567890123456789012", "us2234567890123456789012"],
        )


class TestErrorHandling:
    """Tests for error handling in channel tools."""

    async def test_list_public_channels_auth_error(self, mock_client_auth_error: AsyncMock) -> None:
        """Test authentication error propagation."""
        with pytest.raises(AuthenticationError):
            await channels.list_public_channels(
                team_id="tm1234567890123456789012",
                client=mock_client_auth_error,
            )

    async def test_get_channel_not_found(self, mock_client_not_found: AsyncMock) -> None:
        """Test not found error propagation."""
        with pytest.raises(NotFoundError):
            await channels.get_channel(
                channel_id="ch1234567890123456789012",
                client=mock_client_not_found,
            )
