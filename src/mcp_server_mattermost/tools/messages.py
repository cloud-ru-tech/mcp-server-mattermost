"""Message operations tools."""

from typing import Annotated

from fastmcp.dependencies import Depends
from fastmcp.tools import tool
from pydantic import Field

from mcp_server_mattermost.client import MattermostClient
from mcp_server_mattermost.deps import get_client
from mcp_server_mattermost.enums import Capability, ToolTag
from mcp_server_mattermost.models import Attachment, ChannelId, FileId, Post, PostId, PostList, TeamId


@tool(
    annotations={"destructiveHint": False},
    tags={ToolTag.MATTERMOST, ToolTag.MESSAGE},
    meta={"capability": Capability.WRITE},
)
async def post_message(  # noqa: PLR0913
    channel_id: ChannelId,
    message: Annotated[str, Field(min_length=1, max_length=16383, description="Message content (supports Markdown)")],
    root_id: Annotated[PostId | None, Field(description="Root post ID for threading")] = None,
    file_ids: Annotated[list[FileId] | None, Field(description="File IDs to attach (from upload_file)")] = None,
    attachments: Annotated[
        list[Attachment] | None, Field(description="Rich message attachments with colors, fields, images")
    ] = None,
    client: MattermostClient = Depends(get_client),  # noqa: B008
) -> Post:
    """Post a message to a Mattermost channel.

    Send text messages with Markdown support.
    Use root_id to reply in a thread.
    Use file_ids to attach uploaded files.
    Use attachments for rich formatted content.
    To read all messages in a thread, use get_thread.

    Attachment examples:
    - Status alert: {"color": "danger", "title": "Build Failed", "text": "Tests failed on main"}
    - Success notification: {"color": "good", "title": "Deployed", "text": "v1.2.3 is live"}
    - With fields: {"title": "Ticket", "fields": [{"title": "Status", "value": "Open", "short": true}]}
    """
    props = None
    if attachments:
        props = {"attachments": [a.to_api_dict() for a in attachments]}

    data = await client.create_post(
        channel_id=channel_id,
        message=message,
        root_id=root_id,
        file_ids=file_ids,
        props=props,
    )
    return Post(**data)


@tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.MESSAGE, ToolTag.CHANNEL},
    meta={"capability": Capability.READ},
)
async def get_channel_messages(
    channel_id: ChannelId,
    page: Annotated[int, Field(ge=0, description="Page number (0-indexed)")] = 0,
    per_page: Annotated[int, Field(ge=1, le=200, description="Results per page")] = 60,
    client: MattermostClient = Depends(get_client),  # noqa: B008
) -> PostList:
    """Get recent messages from a channel.

    Returns messages in reverse chronological order (newest first).
    Use for reading channel conversation history.
    For searching messages by keywords across channels, use search_messages instead.
    """
    data = await client.get_posts(
        channel_id=channel_id,
        page=page,
        per_page=per_page,
    )
    return PostList(**data)


@tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.MESSAGE},
    meta={"capability": Capability.READ},
)
async def search_messages(
    team_id: TeamId,
    terms: Annotated[str, Field(min_length=1, max_length=512, description="Search terms (Mattermost syntax)")],
    is_or_search: Annotated[bool, Field(description="Use OR instead of AND for multiple terms")] = False,  # noqa: FBT002
    client: MattermostClient = Depends(get_client),  # noqa: B008
) -> PostList:
    """Search for messages matching specific criteria across channels.

    Searches message content within a team.
    For simply reading recent channel messages, use get_channel_messages instead.

    Search syntax examples:
    - Simple text: "deployment error"
    - From user: "from:username bug"
    - In channel: "in:channel-name release"
    - Date range: "after:2024-01-01 before:2024-02-01"
    - Combined: "from:alice in:dev-ops deployment failed"
    """
    data = await client.search_posts(
        team_id=team_id,
        terms=terms,
        is_or_search=is_or_search,
    )
    return PostList(**data)


@tool(
    annotations={"destructiveHint": False},
    tags={ToolTag.MATTERMOST, ToolTag.MESSAGE},
    meta={"capability": Capability.WRITE},
)
async def update_message(
    post_id: PostId,
    message: Annotated[str, Field(min_length=1, max_length=16383, description="New message content")],
    attachments: Annotated[
        list[Attachment] | None, Field(description="Rich message attachments with colors, fields, images")
    ] = None,
    client: MattermostClient = Depends(get_client),  # noqa: B008
) -> Post:
    """Edit an existing message.

    Can only edit your own messages (unless admin).
    The message will show as edited.
    Original content is replaced; edit history is not preserved.

    Attachment examples:
    - Status alert: {"color": "danger", "title": "Build Failed", "text": "Tests failed on main"}
    - With fields: {"title": "Ticket", "fields": [{"title": "Status", "value": "Open", "short": true}]}
    """
    props = None
    if attachments:
        props = {"attachments": [a.to_api_dict() for a in attachments]}

    data = await client.update_post(
        post_id=post_id,
        message=message,
        props=props,
    )
    return Post(**data)


@tool(
    tags={ToolTag.MATTERMOST, ToolTag.MESSAGE},
    meta={"capability": Capability.DELETE},
)
async def delete_message(
    post_id: PostId,
    client: MattermostClient = Depends(get_client),  # noqa: B008
) -> None:
    """Delete a message permanently.

    Can only delete your own messages (unless admin).
    Deleted messages cannot be recovered.
    All reactions and thread context will be lost.
    """
    await client.delete_post(post_id=post_id)
