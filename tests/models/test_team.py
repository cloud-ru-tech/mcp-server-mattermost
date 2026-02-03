"""Tests for team response models."""

from mcp_server_mattermost.models.team import Team, TeamMember


def test_team_parses():
    """Test Team model (all fields required except last_team_icon_update per Go source)."""
    data = {
        "id": "team123",
        "create_at": 1706400000000,
        "update_at": 1706400000000,
        "delete_at": 0,
        "display_name": "Engineering",
        "name": "engineering",
        "description": "",
        "email": "",
        "type": "O",
        "allowed_domains": "",
        "invite_id": "",
        "allow_open_invite": False,
    }

    team = Team(**data)
    assert team.id == "team123"
    assert team.display_name == "Engineering"
    assert team.type == "O"


def test_team_member_parses():
    """Test TeamMember model."""
    data = {
        "team_id": "team123",
        "user_id": "user456",
        "roles": "team_user",
        "delete_at": 0,
        "scheme_user": True,
        "scheme_admin": False,
    }

    member = TeamMember(**data)
    assert member.team_id == "team123"
    assert member.scheme_user is True
    assert member.scheme_admin is False
