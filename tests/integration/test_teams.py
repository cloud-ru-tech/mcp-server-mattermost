"""Integration tests for team tools via MCP protocol."""

from tests.integration.utils import to_dict


class TestTeamHappyPath:
    """Basic successful team operations through MCP protocol."""

    async def test_list_teams_returns_array(self, mcp_client):
        """list_teams: returns array with at least 1 team."""
        result = await mcp_client.call_tool("list_teams", {})

        teams = to_dict(result)
        assert isinstance(teams, list)
        assert len(teams) >= 1
        assert "id" in teams[0]
        assert "name" in teams[0]

    async def test_get_team_by_id(self, mcp_client, team):
        """get_team: returns team by ID."""
        result = await mcp_client.call_tool(
            "get_team",
            {"team_id": team["id"]},
        )

        team_data = to_dict(result)
        assert team_data["id"] == team["id"]
        assert team_data["name"] == team["name"]

    async def test_get_team_members_includes_bot(self, mcp_client, team, bot_user):
        """get_team_members: returns array including bot user."""
        result = await mcp_client.call_tool(
            "get_team_members",
            {"team_id": team["id"]},
        )

        members = to_dict(result)
        assert isinstance(members, list)
        assert len(members) >= 1
        member_user_ids = [m["user_id"] for m in members]
        assert bot_user["id"] in member_user_ids
