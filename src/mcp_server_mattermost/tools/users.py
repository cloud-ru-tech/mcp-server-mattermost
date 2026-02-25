"""User operations tools."""

from typing import Annotated

from fastmcp.dependencies import Depends
from fastmcp.tools import tool
from pydantic import Field

from mcp_server_mattermost.client import MattermostClient
from mcp_server_mattermost.deps import get_client
from mcp_server_mattermost.enums import Capability, ToolTag
from mcp_server_mattermost.models import TeamId, User, UserId, Username, UserStatus


@tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.USER},
    meta={"capability": Capability.READ},
)
async def get_me(
    client: MattermostClient = Depends(get_client),  # noqa: B008
) -> User:
    """Get the current authenticated user's profile.

    Returns user information including username, email, and status.
    Use to get your own user ID for operations like create_direct_channel.
    """
    data = await client.get_me()
    return User(**data)


@tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.USER},
    meta={"capability": Capability.READ},
)
async def get_user(
    user_id: UserId,
    client: MattermostClient = Depends(get_client),  # noqa: B008
) -> User:
    """Get a user's profile by their ID.

    Returns user information including username, email, and status.
    Use when you have the user ID.
    For lookup by @username, use get_user_by_username instead.
    """
    data = await client.get_user(user_id=user_id)
    return User(**data)


@tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.USER},
    meta={"capability": Capability.READ},
)
async def get_user_by_username(
    username: Username,
    client: MattermostClient = Depends(get_client),  # noqa: B008
) -> User:
    """Get a user's profile by their username.

    Returns user information including username, email, and status.
    Use when you know the @username but not the user ID.
    For lookup by ID, use get_user instead.
    """
    data = await client.get_user_by_username(username=username)
    return User(**data)


@tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.USER},
    meta={"capability": Capability.READ},
)
async def search_users(
    term: Annotated[str, Field(min_length=1, max_length=256, description="Search term")],
    team_id: Annotated[TeamId | None, Field(description="Limit search to a specific team")] = None,
    client: MattermostClient = Depends(get_client),  # noqa: B008
) -> list[User]:
    """Search for users by name or username.

    Searches across username, first name, last name, and nickname.
    Use to find users when you don't know their exact username or ID.
    """
    data = await client.search_users(
        term=term,
        team_id=team_id,
    )
    return [User(**item) for item in data]


@tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.USER},
    meta={"capability": Capability.READ},
)
async def get_user_status(
    user_id: UserId,
    client: MattermostClient = Depends(get_client),  # noqa: B008
) -> UserStatus:
    """Get a user's online/offline status.

    Returns: online, away, dnd (do not disturb), or offline.
    Use to check if a user is available before sending a message.
    """
    data = await client.get_user_status(user_id=user_id)
    return UserStatus(**data)
