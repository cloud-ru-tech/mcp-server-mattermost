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


class Capability(str, Enum):
    """Capability labels for agent-based tool filtering.

    Exposed via meta={"capability": value} on each tool.
    Agents use this to select tools matching their access level.

    Profiles are defined client-side, not server-side. Example:
        reader:  {Capability.READ}
        writer:  {Capability.READ, Capability.WRITE}
        manager: {Capability.READ, Capability.WRITE, Capability.CREATE}
        admin:   {Capability.READ, Capability.WRITE, Capability.CREATE, Capability.DELETE}
    """

    READ = "read"
    WRITE = "write"
    CREATE = "create"
    DELETE = "delete"
