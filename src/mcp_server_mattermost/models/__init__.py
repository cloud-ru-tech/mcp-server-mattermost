"""Pydantic models and type definitions for Mattermost entities."""

from .attachment import Attachment, AttachmentColor, AttachmentField
from .base import MattermostResponse
from .bookmark import ChannelBookmark
from .channel import Channel, ChannelMember
from .common import (
    BookmarkId,
    ChannelId,
    ChannelName,
    ChannelType,
    EmojiName,
    FileId,
    MattermostId,
    PostId,
    TeamId,
    UserId,
    Username,
    validate_mattermost_id,
)
from .file import FileInfo, FileLink, FileUploadResponse
from .post import Post, PostList, Reaction
from .team import Team, TeamMember
from .user import User, UserStatus


__all__ = [
    "Attachment",
    "AttachmentColor",
    "AttachmentField",
    "BookmarkId",
    "Channel",
    "ChannelBookmark",
    "ChannelId",
    "ChannelMember",
    "ChannelName",
    "ChannelType",
    "EmojiName",
    "FileId",
    "FileInfo",
    "FileLink",
    "FileUploadResponse",
    "MattermostId",
    "MattermostResponse",
    "Post",
    "PostId",
    "PostList",
    "Reaction",
    "Team",
    "TeamId",
    "TeamMember",
    "User",
    "UserId",
    "UserStatus",
    "Username",
    "validate_mattermost_id",
]
