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


class ChannelWithUnreads(Channel):
    """Channel enriched with unread counters and the read marker for the authenticated user.

    Two counter pairs cover both Mattermost reading modes:

    - ``unread_msg_count`` / ``mention_count`` use non-root semantics — replies
      inside threads count as channel messages. They match the channel unread
      badge when Collapsed Reply Threads (CRT) is disabled.
    - ``unread_msg_count_root`` / ``mention_count_root`` count only root posts,
      ignoring thread replies. They match the channel unread badge when CRT is
      enabled.

    ``last_viewed_at`` is the user's last-read marker for this channel — the
    timestamp through which the user has read posts.

    Channels without a membership record report 0 for all four counters and
    ``last_viewed_at``.
    """

    unread_msg_count: int = Field(description="Unread messages, including replies in threads")
    mention_count: int = Field(description="Unread @-mentions, including those in thread replies")
    unread_msg_count_root: int = Field(description="Unread root messages, excluding replies in threads")
    mention_count_root: int = Field(description="Unread @-mentions in root messages, excluding thread replies")
    last_viewed_at: int = Field(
        description=(
            "User's last-read marker for this channel (Unix ms). Through this timestamp "
            "the user has read the channel. 0 when no membership record exists."
        )
    )


class ChannelMember(MattermostResponse):
    """Channel membership information.

    `msg_count` / `mention_count` use non-root semantics (replies inside threads count
    as channel messages); `msg_count_root` / `mention_count_root` count only top-level
    posts. Both pairs are returned by Mattermost and consumed by
    `client.get_my_channels_with_unreads` to compute the per-channel unread counters.
    """

    channel_id: str = Field(description="Channel identifier")
    user_id: str = Field(description="User identifier")
    roles: str = Field(description="Space-separated role names")
    last_viewed_at: int = Field(description="Last viewed timestamp")
    msg_count: int = Field(description="Messages seen count, including replies in threads")
    mention_count: int = Field(description="Unread @-mentions count, including thread replies")
    msg_count_root: int = Field(description="Root messages seen count, excluding thread replies")
    mention_count_root: int = Field(description="Unread root @-mentions count, excluding thread replies")
    last_update_at: int = Field(description="Last update timestamp")
