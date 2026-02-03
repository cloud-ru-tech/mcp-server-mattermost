"""Post response models."""

from pydantic import Field

from .base import MattermostResponse


class Post(MattermostResponse):
    """Message/post in Mattermost."""

    id: str = Field(description="Unique post identifier")
    create_at: int = Field(description="Creation timestamp in milliseconds")
    update_at: int = Field(description="Last update timestamp in milliseconds")
    delete_at: int = Field(description="Deletion timestamp (0 if not deleted)")
    edit_at: int = Field(description="Last edit timestamp")
    user_id: str = Field(description="Author user identifier")
    channel_id: str = Field(description="Channel where posted")
    root_id: str = Field(description="Root post ID if in thread")
    original_id: str = Field(description="Original post ID if edited")
    message: str = Field(description="Post content (supports Markdown)")
    type: str = Field(description="Post type (empty for regular posts)")
    hashtags: str = Field(description="Space-separated hashtags")
    file_ids: list[str] = Field(description="Attached file IDs")
    pending_post_id: str = Field(description="Client-side pending ID")
    is_pinned: bool = Field(description="Whether post is pinned")


class PostList(MattermostResponse):
    """Response from get_posts and search_posts endpoints.

    Posts are returned as a dict keyed by ID for fast lookup.
    Use `order` to iterate in display order (newest first).
    """

    order: list[str] = Field(description="Post IDs in display order")
    posts: dict[str, Post] = Field(description="Map of post ID to Post object")
    next_post_id: str = Field(default="", description="Next post ID for pagination")
    prev_post_id: str = Field(default="", description="Previous post ID for pagination")


class Reaction(MattermostResponse):
    """Emoji reaction on a post."""

    user_id: str = Field(description="User who reacted")
    post_id: str = Field(description="Post that was reacted to")
    emoji_name: str = Field(description="Emoji name without colons")
    create_at: int = Field(description="Reaction timestamp")
