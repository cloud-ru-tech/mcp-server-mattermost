"""Team operations tools."""

from typing import Annotated

from fastmcp.dependencies import Depends
from pydantic import Field

from mcp_server_mattermost.client import MattermostClient
from mcp_server_mattermost.enums import ToolTag
from mcp_server_mattermost.models import Team, TeamId, TeamMember
from mcp_server_mattermost.server import get_client, mcp


@mcp.tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.TEAM},
)
async def list_teams(
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> list[Team]:
    """List teams the current user belongs to.

    Returns team name, description, and settings.
    Use this to discover available teams before listing channels.
    """
    data = await client.get_teams()
    return [Team(**item) for item in data]


@mcp.tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.TEAM},
)
async def get_team(
    team_id: TeamId,
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> Team:
    """Get team details by ID.

    Returns team name, description, and settings.
    Use when you have the team ID and need detailed information.
    """
    data = await client.get_team(team_id=team_id)
    return Team(**data)


@mcp.tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.TEAM, ToolTag.USER},
)
async def get_team_members(
    team_id: TeamId,
    page: Annotated[int, Field(ge=0, description="Page number (0-indexed)")] = 0,
    per_page: Annotated[int, Field(ge=1, le=200, description="Results per page")] = 60,
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> list[TeamMember]:
    """Get members of a team.

    Returns list of users who belong to the team.
    Use to discover users before sending direct messages or mentions.
    """
    data = await client.get_team_members(
        team_id=team_id,
        page=page,
        per_page=per_page,
    )
    return [TeamMember(**item) for item in data]
