"""Channel response models."""

from pydantic import Field

from .base import MattermostResponse


class Channel(MattermostResponse):
    """Channel in Mattermost."""

    id: str = Field(description="Unique channel identifier")
    create_at: int = Field(description="Creation timestamp in milliseconds")
    update_at: int = Field(description="Last update timestamp in milliseconds")
    delete_at: int = Field(description="Deletion timestamp (0 if not deleted)")
    team_id: str = Field(description="Team this channel belongs to")
    type: str = Field(description="Channel type: O=public, P=private, D=direct, G=group")
    display_name: str = Field(description="Human-readable channel name")
    name: str = Field(description="URL-friendly channel name")
    header: str = Field(description="Channel header text")
    purpose: str = Field(description="Channel purpose description")
    last_post_at: int = Field(description="Timestamp of last post")
    total_msg_count: int = Field(description="Total message count")
    creator_id: str = Field(description="User ID who created the channel")


class ChannelMember(MattermostResponse):
    """Channel membership information."""

    channel_id: str = Field(description="Channel identifier")
    user_id: str = Field(description="User identifier")
    roles: str = Field(description="Space-separated role names")
    last_viewed_at: int = Field(description="Last viewed timestamp")
    msg_count: int = Field(description="Messages seen count")
    mention_count: int = Field(description="Unread mentions count")
    last_update_at: int = Field(description="Last update timestamp")
