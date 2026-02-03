"""Channel bookmark management tools."""

from typing import Annotated, Literal

from fastmcp.dependencies import Depends
from pydantic import Field

from mcp_server_mattermost.client import MattermostClient
from mcp_server_mattermost.enums import ToolTag
from mcp_server_mattermost.exceptions import ValidationError
from mcp_server_mattermost.models import ChannelBookmark, ChannelId
from mcp_server_mattermost.models.common import BookmarkId
from mcp_server_mattermost.server import get_client, mcp


@mcp.tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.BOOKMARK, ToolTag.CHANNEL, ToolTag.ENTRY_REQUIRED},
)
async def list_bookmarks(
    channel_id: ChannelId,
    bookmarks_since: Annotated[
        int | None,
        Field(default=None, description="Timestamp to filter bookmarks updated since"),
    ] = None,
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> list[ChannelBookmark]:
    """List all bookmarks in a channel.

    Returns bookmarks in sort order.
    Use to see saved links and files pinned to a channel.
    For searching messages, use search_messages instead.

    Note: Requires Entry, Professional, Enterprise, or Enterprise Advanced edition
    (not available in Team Edition). Minimum version: v10.1.
    """
    data = await client.get_bookmarks(
        channel_id=channel_id,
        bookmarks_since=bookmarks_since,
    )
    return [ChannelBookmark(**item) for item in data]


@mcp.tool(
    annotations={"destructiveHint": False},
    tags={ToolTag.MATTERMOST, ToolTag.BOOKMARK, ToolTag.CHANNEL, ToolTag.ENTRY_REQUIRED},
)
async def create_bookmark(  # noqa: PLR0913
    channel_id: ChannelId,
    display_name: Annotated[str, Field(min_length=1, max_length=255, description="Bookmark display name")],
    bookmark_type: Annotated[Literal["link", "file"], Field(description="Bookmark type: 'link' or 'file'")],
    link_url: Annotated[str | None, Field(default=None, description="URL (required for link type)")] = None,
    file_id: Annotated[str | None, Field(default=None, description="File ID (required for file type)")] = None,
    emoji: Annotated[str | None, Field(default=None, description="Emoji icon")] = None,
    image_url: Annotated[str | None, Field(default=None, description="Preview image URL")] = None,
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> ChannelBookmark:
    """Create a channel bookmark.

    Creates a link bookmark (URL) or file bookmark (attached file).
    For link type, link_url is required.
    For file type, file_id is required (from upload_file).

    Note: Requires Entry, Professional, Enterprise, or Enterprise Advanced edition
    (not available in Team Edition). Minimum version: v10.1.
    """
    if bookmark_type == "link" and not link_url:
        msg = "link_url is required for link bookmarks"
        raise ValidationError(msg)
    if bookmark_type == "file" and not file_id:
        msg = "file_id is required for file bookmarks"
        raise ValidationError(msg)

    data = await client.create_bookmark(
        channel_id=channel_id,
        display_name=display_name,
        bookmark_type=bookmark_type,
        link_url=link_url,
        file_id=file_id,
        emoji=emoji,
        image_url=image_url,
    )
    return ChannelBookmark(**data)


@mcp.tool(
    annotations={"destructiveHint": False, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.BOOKMARK, ToolTag.CHANNEL, ToolTag.ENTRY_REQUIRED},
)
async def update_bookmark(  # noqa: PLR0913
    channel_id: ChannelId,
    bookmark_id: BookmarkId,
    display_name: Annotated[str | None, Field(default=None, description="New display name")] = None,
    link_url: Annotated[str | None, Field(default=None, description="New URL")] = None,
    image_url: Annotated[str | None, Field(default=None, description="New preview image URL")] = None,
    emoji: Annotated[str | None, Field(default=None, description="New emoji icon")] = None,
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> ChannelBookmark:
    """Update a channel bookmark.

    Partially updates bookmark properties.
    Only provided fields are updated; others remain unchanged.

    Note: Requires Entry, Professional, Enterprise, or Enterprise Advanced edition
    (not available in Team Edition). Minimum version: v10.1.
    """
    fields = {}
    if display_name is not None:
        fields["display_name"] = display_name
    if link_url is not None:
        fields["link_url"] = link_url
    if image_url is not None:
        fields["image_url"] = image_url
    if emoji is not None:
        fields["emoji"] = emoji

    data = await client.update_bookmark(
        channel_id=channel_id,
        bookmark_id=bookmark_id,
        **fields,
    )
    return ChannelBookmark(**data)


@mcp.tool(
    tags={ToolTag.MATTERMOST, ToolTag.BOOKMARK, ToolTag.CHANNEL, ToolTag.ENTRY_REQUIRED},
)
async def delete_bookmark(
    channel_id: ChannelId,
    bookmark_id: BookmarkId,
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> ChannelBookmark:
    """Delete a channel bookmark.

    Archives the bookmark (soft delete via delete_at timestamp).
    The bookmark will no longer appear in the channel.

    Note: Requires Entry, Professional, Enterprise, or Enterprise Advanced edition
    (not available in Team Edition). Minimum version: v10.1.
    """
    data = await client.delete_bookmark(
        channel_id=channel_id,
        bookmark_id=bookmark_id,
    )
    return ChannelBookmark(**data)


@mcp.tool(
    annotations={"destructiveHint": False, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.BOOKMARK, ToolTag.CHANNEL, ToolTag.ENTRY_REQUIRED},
)
async def update_bookmark_sort_order(
    channel_id: ChannelId,
    bookmark_id: BookmarkId,
    new_sort_order: Annotated[int, Field(ge=0, description="New position in bookmark list")],
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> list[ChannelBookmark]:
    """Reorder a channel bookmark.

    Moves the bookmark to the specified position.
    Other bookmarks are automatically adjusted.
    Returns all affected bookmarks with updated positions.

    Note: Requires Entry, Professional, Enterprise, or Enterprise Advanced edition
    (not available in Team Edition). Minimum version: v10.1.
    """
    data = await client.update_bookmark_sort_order(
        channel_id=channel_id,
        bookmark_id=bookmark_id,
        new_sort_order=new_sort_order,
    )
    return [ChannelBookmark(**item) for item in data]
