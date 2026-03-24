"""Channel management tools."""

from typing import Annotated, Literal

from fastmcp.dependencies import Depends
from fastmcp.tools import tool
from pydantic import Field

from mcp_server_mattermost.client import MattermostClient
from mcp_server_mattermost.deps import get_client
from mcp_server_mattermost.enums import Capability, ToolTag
from mcp_server_mattermost.models import Channel, ChannelId, ChannelMember, ChannelName, ChannelType, TeamId, UserId


@tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.CHANNEL},
    meta={"capability": Capability.READ},
)
async def list_public_channels(
    team_id: TeamId,
    page: Annotated[int, Field(ge=0, description="Page number (0-indexed)")] = 0,
    per_page: Annotated[int, Field(ge=1, le=200, description="Results per page")] = 60,
    client: MattermostClient = Depends(get_client),  # noqa: B008
) -> list[Channel]:
    """List public channels available in a team.

    Returns all public channels for discovery, including ones you haven't joined.
    Results are paginated. Use page/per_page to retrieve all channels.
    Useful for finding channels to join.
    For channels you are already a member of (including private), use list_my_channels.
    """
    data = await client.get_public_channels(
        team_id=team_id,
        page=page,
        per_page=per_page,
    )
    return [Channel(**item) for item in data]


@tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.CHANNEL},
    meta={"capability": Capability.READ},
)
async def list_my_channels(
    team_id: TeamId,
    channel_types: Annotated[
        list[Literal["O", "P", "D", "G"]] | None,
        Field(
            min_length=1,
            description=(
                "Channel types to include: O=public, P=private, "
                "D=direct message, G=group message. "
                "Omit to return all types."
            ),
        ),
    ] = None,
    client: MattermostClient = Depends(get_client),  # noqa: B008
) -> list[Channel]:
    """List channels you are a member of in a team.

    Returns your channels filtered by type. By default returns all types.
    Use channel_types to narrow results: ["O", "P"] for workspace channels
    without DMs, or ["D"] for direct messages only.
    For discovering public channels you haven't joined yet, use list_public_channels.
    """
    data = await client.get_my_channels(team_id=team_id)
    if channel_types is not None:
        data = [ch for ch in data if ch.get("type") in channel_types]
    return [Channel(**item) for item in data]


@tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.CHANNEL},
    meta={"capability": Capability.READ},
)
async def get_channel(
    channel_id: ChannelId,
    client: MattermostClient = Depends(get_client),  # noqa: B008
) -> Channel:
    """Get detailed information about a specific channel.

    Returns channel metadata including name, purpose, header, and member count.
    Use when you have the channel ID.
    For lookup by channel name, use get_channel_by_name instead.
    """
    data = await client.get_channel(channel_id=channel_id)
    return Channel(**data)


@tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.CHANNEL},
    meta={"capability": Capability.READ},
)
async def get_channel_by_name(
    team_id: TeamId,
    channel_name: ChannelName,
    client: MattermostClient = Depends(get_client),  # noqa: B008
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


@tool(
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
    client: MattermostClient = Depends(get_client),  # noqa: B008
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


@tool(
    annotations={"destructiveHint": False, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.CHANNEL},
    meta={"capability": Capability.WRITE},
)
async def join_channel(
    channel_id: ChannelId,
    client: MattermostClient = Depends(get_client),  # noqa: B008
) -> ChannelMember:
    """Join a public channel.

    Adds the authenticated user to the channel.
    Cannot be used to join private channels.
    Joining a channel you're already in has no additional effect.
    """
    data = await client.join_channel(channel_id=channel_id)
    return ChannelMember(**data)


@tool(
    annotations={"destructiveHint": False, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.CHANNEL},
    meta={"capability": Capability.WRITE},
)
async def leave_channel(
    channel_id: ChannelId,
    client: MattermostClient = Depends(get_client),  # noqa: B008
) -> None:
    """Leave a channel.

    Removes the authenticated user from the channel.
    Cannot leave Town Square or other default channels.
    Can rejoin public channels later with join_channel.
    """
    await client.leave_channel(channel_id=channel_id)


@tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.CHANNEL, ToolTag.USER},
    meta={"capability": Capability.READ},
)
async def get_channel_members(
    channel_id: ChannelId,
    page: Annotated[int, Field(ge=0, description="Page number (0-indexed)")] = 0,
    per_page: Annotated[int, Field(ge=1, le=200, description="Results per page")] = 60,
    client: MattermostClient = Depends(get_client),  # noqa: B008
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


@tool(
    annotations={"destructiveHint": False, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.CHANNEL, ToolTag.USER},
    meta={"capability": Capability.WRITE},
)
async def add_user_to_channel(
    channel_id: ChannelId,
    user_id: UserId,
    client: MattermostClient = Depends(get_client),  # noqa: B008
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


@tool(
    annotations={"destructiveHint": False, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.CHANNEL},
    meta={"capability": Capability.CREATE},
)
async def create_direct_channel(
    user_id_1: UserId,
    user_id_2: UserId,
    client: MattermostClient = Depends(get_client),  # noqa: B008
) -> Channel:
    """Create a direct message channel between two users.

    Returns an existing DM channel if one already exists between the users.
    Use this to get a channel ID for sending private messages.
    Then use post_message with the returned channel_id to send messages.
    """
    data = await client.create_direct_channel(user_ids=[user_id_1, user_id_2])
    return Channel(**data)
