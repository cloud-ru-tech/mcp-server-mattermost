"""Channel bookmark response models."""

from pydantic import Field

from .base import MattermostResponse


class ChannelBookmark(MattermostResponse):
    """Channel bookmark.

    See: https://github.com/mattermost/mattermost/blob/master/server/public/model/channel_bookmark.go
    """

    id: str = Field(description="Unique bookmark identifier")
    create_at: int = Field(description="Creation timestamp in milliseconds")
    update_at: int = Field(description="Last update timestamp in milliseconds")
    delete_at: int = Field(description="Deletion timestamp (0 if not deleted)")
    channel_id: str = Field(description="Channel this bookmark belongs to")
    owner_id: str = Field(description="User ID who created the bookmark")
    file_id: str = Field(description="File ID for file bookmarks (empty for links)")
    display_name: str = Field(description="Bookmark display name")
    sort_order: int = Field(description="Position in bookmark list")
    type: str = Field(description="Bookmark type: 'link' or 'file'")

    link_url: str | None = Field(default=None, description="URL for link bookmarks")
    image_url: str | None = Field(default=None, description="Preview image URL")
    emoji: str | None = Field(default=None, description="Emoji icon")
    original_id: str | None = Field(default=None, description="Original bookmark ID if copied")
    parent_id: str | None = Field(default=None, description="Parent bookmark ID")
    file_info: dict[str, object] | None = Field(default=None, description="File metadata for file bookmarks")
