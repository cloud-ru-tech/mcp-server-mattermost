"""Channel management tools."""

from typing import Annotated

from fastmcp.dependencies import Depends
from pydantic import Field

from mcp_server_mattermost.client import MattermostClient
from mcp_server_mattermost.enums import Capability, ToolTag
from mcp_server_mattermost.models import Channel, ChannelId, ChannelMember, ChannelName, ChannelType, TeamId, UserId
from mcp_server_mattermost.server import get_client, mcp


@mcp.tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.CHANNEL},
    meta={"capability": Capability.READ},
)
async def list_channels(
    team_id: TeamId,
    page: Annotated[int, Field(ge=0, description="Page number (0-indexed)")] = 0,
    per_page: Annotated[int, Field(ge=1, le=200, description="Results per page")] = 60,
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> list[Channel]:
    """List public and private channels in a team.

    Returns channels that the authenticated user has access to.
    Use this to discover available channels for posting messages.
    """
    data = await client.get_channels(
        team_id=team_id,
        page=page,
        per_page=per_page,
    )
    return [Channel(**item) for item in data]


@mcp.tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.CHANNEL},
    meta={"capability": Capability.READ},
)
async def get_channel(
    channel_id: ChannelId,
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> Channel:
    """Get detailed information about a specific channel.

    Returns channel metadata including name, purpose, header, and member count.
    Use when you have the channel ID.
    For lookup by channel name, use get_channel_by_name instead.
    """
    data = await client.get_channel(channel_id=channel_id)
    return Channel(**data)


@mcp.tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.CHANNEL},
    meta={"capability": Capability.READ},
)
async def get_channel_by_name(
    team_id: TeamId,
    channel_name: ChannelName,
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> Channel:
    """Get a channel by its name within a team.

    Returns channel metadata including name, purpose, header, and member count.
    Use when you know the channel name but not the ID.
    For lookup by ID, use get_channel instead.
    """
    data = await client.get_channel_by_name(
        team_id=team_id,
        name=channel_name,
    )
    return Channel(**data)


@mcp.tool(
    annotations={"destructiveHint": False},
    tags={ToolTag.MATTERMOST, ToolTag.CHANNEL},
    meta={"capability": Capability.CREATE},
)
async def create_channel(  # noqa: PLR0913
    team_id: TeamId,
    name: ChannelName,
    display_name: Annotated[str, Field(min_length=1, max_length=64, description="Human-readable channel name")],
    channel_type: ChannelType = "O",
    purpose: Annotated[str, Field(max_length=250, description="Channel purpose")] = "",
    header: Annotated[str, Field(max_length=1024, description="Channel header")] = "",
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> Channel:
    """Create a new channel in a team.

    Creates either a public (O) or private (P) channel.
    The authenticated user becomes the channel admin.
    Each call creates a new channel; use get_channel_by_name to check if it exists.
    """
    data = await client.create_channel(
        team_id=team_id,
        name=name,
        display_name=display_name,
        channel_type=channel_type,
        purpose=purpose,
        header=header,
    )
    return Channel(**data)


@mcp.tool(
    annotations={"destructiveHint": False, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.CHANNEL},
    meta={"capability": Capability.WRITE},
)
async def join_channel(
    channel_id: ChannelId,
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> ChannelMember:
    """Join a public channel.

    Adds the authenticated user to the channel.
    Cannot be used to join private channels.
    Joining a channel you're already in has no additional effect.
    """
    data = await client.join_channel(channel_id=channel_id)
    return ChannelMember(**data)


@mcp.tool(
    annotations={"destructiveHint": False, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.CHANNEL},
    meta={"capability": Capability.WRITE},
)
async def leave_channel(
    channel_id: ChannelId,
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> None:
    """Leave a channel.

    Removes the authenticated user from the channel.
    Cannot leave Town Square or other default channels.
    Can rejoin public channels later with join_channel.
    """
    await client.leave_channel(channel_id=channel_id)


@mcp.tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.CHANNEL, ToolTag.USER},
    meta={"capability": Capability.READ},
)
async def get_channel_members(
    channel_id: ChannelId,
    page: Annotated[int, Field(ge=0, description="Page number (0-indexed)")] = 0,
    per_page: Annotated[int, Field(ge=1, le=200, description="Results per page")] = 60,
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> list[ChannelMember]:
    """Get members of a channel.

    Returns list of users who are members of the channel.
    Use to see who can receive messages in a channel.
    """
    data = await client.get_channel_members(
        channel_id=channel_id,
        page=page,
        per_page=per_page,
    )
    return [ChannelMember(**item) for item in data]


@mcp.tool(
    annotations={"destructiveHint": False, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.CHANNEL, ToolTag.USER},
    meta={"capability": Capability.WRITE},
)
async def add_user_to_channel(
    channel_id: ChannelId,
    user_id: UserId,
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> ChannelMember:
    """Add a user to a channel.

    Requires permission to manage channel members.
    Adding a user who is already in the channel has no additional effect.
    """
    data = await client.add_user_to_channel(
        channel_id=channel_id,
        user_id=user_id,
    )
    return ChannelMember(**data)


@mcp.tool(
    annotations={"destructiveHint": False, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.CHANNEL},
    meta={"capability": Capability.CREATE},
)
async def create_direct_channel(
    user_id_1: UserId,
    user_id_2: UserId,
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> Channel:
    """Create a direct message channel between two users.

    Returns an existing DM channel if one already exists between the users.
    Use this to get a channel ID for sending private messages.
    Then use post_message with the returned channel_id to send messages.
    """
    data = await client.create_direct_channel(user_ids=[user_id_1, user_id_2])
    return Channel(**data)
