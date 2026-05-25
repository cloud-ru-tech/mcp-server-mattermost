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


_DEFAULT_PER_PAGE = 60


def _validate_get_channel_messages_mode(
    unread_only: bool,  # noqa: FBT001
    since: int | None,
    page: int,
    per_page: int,
) -> None:
    """Raise ValueError if multiple read modes are combined.

    Three modes are supported and mutually exclusive:
      - unread_only=True            -> /posts/unread
      - since=<ms>                  -> /posts?since=
      - default (page/per_page)     -> /posts?page=&per_page=
    """
    if unread_only and since is not None:
        msg = "unread_only=True and since=... are mutually exclusive — pick one mode"
        raise ValueError(msg)
    pagination_explicit = page != 0 or per_page != _DEFAULT_PER_PAGE
    if (unread_only or since is not None) and pagination_explicit:
        msg = (
            "page/per_page cannot be combined with unread_only or since — pagination is only meaningful in default mode"
        )
        raise ValueError(msg)


@tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.MESSAGE, ToolTag.CHANNEL},
    meta={"capability": Capability.READ},
)
async def get_channel_messages(  # noqa: PLR0913
    channel_id: ChannelId,
    unread_only: Annotated[  # noqa: FBT002
        bool,
        Field(description="Return only the user's unread window via /posts/unread"),
    ] = False,
    since: Annotated[
        int | None,
        Field(
            ge=1_000_000_000_000,
            description=(
                "Unix timestamp in milliseconds (>= 10^12, i.e. >= 2001-01-01); return "
                "posts modified after this time. Mutually exclusive with unread_only and "
                "pagination. Use ChannelWithUnreads.last_viewed_at from list_my_channels."
            ),
        ),
    ] = None,
    page: Annotated[int, Field(ge=0, description="Page number (0-indexed)")] = 0,
    per_page: Annotated[int, Field(ge=1, le=200, description="Results per page")] = _DEFAULT_PER_PAGE,
    limit_before: Annotated[  # noqa: ARG001
        int,
        Field(
            ge=0,
            le=200,
            description="In unread_only mode: read context posts before the first unread (max 200)",
        ),
    ] = 0,
    limit_after: Annotated[  # noqa: ARG001
        int,
        Field(
            ge=0,
            le=200,
            description="In unread_only mode: unread posts to return (max 200)",
        ),
    ] = _DEFAULT_PER_PAGE,
    collapsed_threads: Annotated[  # noqa: FBT002, ARG001
        bool,
        Field(
            description=(
                "Set True only if the user has CRT (Collapsed Reply Threads) enabled. "
                "Team default is CRT off — leave False unless you know otherwise."
            ),
        ),
    ] = False,
    client: MattermostClient = Depends(get_client),  # noqa: B008
) -> PostList:
    """Get messages from a channel — recent, unread window, or modified since a timestamp.

    Three mutually-exclusive modes:

    - **Default (page/per_page):** last ``per_page`` messages, reverse-chronological.
      Suitable for "show me recent messages".
    - **``unread_only=True``:** the user's unread window via ``/posts/unread``.
      Returns up to ``limit_after`` unread posts plus ``limit_before`` context posts.
      Deterministic ordering; edits of older posts do not appear. Preferred mode for
      "show me what's new".
    - **``since=<ms>``:** posts with ``update_at > since`` via ``?since=``. Includes
      edits of older posts and thread replies. Use for incremental sync where the agent
      tracks its own watermark. Server hard-caps at 1000 posts without a deterministic
      order — check ``truncated`` on the response.

    Returns messages in reverse chronological order.
    For searching messages by keywords across channels, use search_messages instead.
    To read all messages in a thread, use get_thread.

    Notes for agents:
        - When CRT is OFF (team default), ``unread_msg_count`` from list_my_channels
          covers both root posts and thread replies; this tool's response in any mode
          also covers both.
        - When CRT is ON, ``unread_msg_count`` in list_my_channels excludes thread
          replies. Pass ``collapsed_threads=True`` and fetch full threads via get_thread
          when needed.
        - In ``since`` mode, edits of older posts (``create_at <= since AND
          update_at > since``) appear in the response. Filter by ``create_at > since``
          if you only want newly-created messages.
        - If ``response.truncated`` is True, more posts exist beyond this batch.
          In ``since`` mode, switch to ``unread_only=True`` for deterministic results.
    """
    _validate_get_channel_messages_mode(unread_only=unread_only, since=since, page=page, per_page=per_page)
    # Routing to unread_only / since branches is implemented in Task 5.
    data = await client.get_posts(channel_id=channel_id, page=page, per_page=per_page)
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
