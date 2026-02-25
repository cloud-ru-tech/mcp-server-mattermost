"""Tests for team tools."""

from unittest.mock import AsyncMock

import pytest

from mcp_server_mattermost.exceptions import NotFoundError
from mcp_server_mattermost.models import Team, TeamMember
from mcp_server_mattermost.tools import teams


def make_team_data(
    team_id: str = "tm1234567890123456789012",
    name: str = "myteam",
    **overrides,
) -> dict:
    """Create full team mock data.

    All fields required except last_team_icon_update per Go source.
    """
    return {
        "id": team_id,
        "create_at": 1706400000000,
        "update_at": 1706400000000,
        "delete_at": 0,
        "display_name": "My Team",
        "name": name,
        "description": "",
        "email": "",
        "type": "O",
        "allowed_domains": "",
        "invite_id": "",
        "allow_open_invite": False,
        **overrides,
    }


def make_team_member_data(
    team_id: str = "tm1234567890123456789012",
    user_id: str = "us1234567890123456789012",
    **overrides,
) -> dict:
    """Create full team member mock data.

    All fields required per Go source.
    """
    return {
        "team_id": team_id,
        "user_id": user_id,
        "roles": "team_user",
        "delete_at": 0,
        "scheme_user": True,
        "scheme_admin": False,
        **overrides,
    }


class TestListTeams:
    """Tests for list_teams tool."""

    async def test_list_teams(self, mock_client: AsyncMock) -> None:
        """Test listing teams returns list of Team models."""
        mock_client.get_teams.return_value = [make_team_data()]

        result = await teams.list_teams(client=mock_client)

        assert len(result) == 1
        assert isinstance(result[0], Team)
        assert result[0].name == "myteam"


class TestGetTeam:
    """Tests for get_team tool."""

    async def test_get_team(self, mock_client: AsyncMock) -> None:
        """Test getting team by ID returns Team model."""
        mock_client.get_team.return_value = make_team_data()

        result = await teams.get_team(
            team_id="tm1234567890123456789012",
            client=mock_client,
        )

        assert isinstance(result, Team)
        assert result.name == "myteam"


class TestGetTeamMembers:
    """Tests for get_team_members tool."""

    async def test_get_team_members(self, mock_client: AsyncMock) -> None:
        """Test getting team members returns list of TeamMember models."""
        mock_client.get_team_members.return_value = [make_team_member_data()]

        result = await teams.get_team_members(
            team_id="tm1234567890123456789012",
            page=0,
            per_page=60,
            client=mock_client,
        )

        assert len(result) == 1
        assert isinstance(result[0], TeamMember)


class TestErrorHandling:
    """Tests for error handling in team tools."""

    async def test_get_team_not_found(self, mock_client_not_found: AsyncMock) -> None:
        """Test not found error propagation."""
        with pytest.raises(NotFoundError):
            await teams.get_team(
                team_id="tm1234567890123456789012",
                client=mock_client_not_found,
            )
