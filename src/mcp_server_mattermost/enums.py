"""Enumeration types for the MCP server."""

from enum import Enum


class ToolTag(str, Enum):
    """Tags for categorizing MCP tools.

    Used for tool discovery and filtering by clients.
    Each tool can have multiple tags.
    """

    MATTERMOST = "mattermost"
    CHANNEL = "channel"
    MESSAGE = "message"
    POST = "post"
    USER = "user"
    TEAM = "team"
    FILE = "file"
    BOOKMARK = "bookmark"
    ENTRY_REQUIRED = "entry-required"  # Requires Entry, Professional, or Enterprise edition
