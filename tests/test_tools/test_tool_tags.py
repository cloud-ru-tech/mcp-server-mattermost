"""Comprehensive tests for tool tags across all modules."""

import pytest

from mcp_server_mattermost.server import mcp
from mcp_server_mattermost.tools import bookmarks, channels, files, messages, posts, teams, users  # noqa: F401


# Tool-to-module mapping for categorization
_TOOL_TO_MODULE: dict[str, str] = {}
for _tool in (
    "list_channels",
    "get_channel",
    "get_channel_by_name",
    "create_channel",
    "join_channel",
    "leave_channel",
    "get_channel_members",
    "add_user_to_channel",
    "create_direct_channel",
):
    _TOOL_TO_MODULE[_tool] = "channels"
for _tool in ("post_message", "get_channel_messages", "search_messages", "update_message", "delete_message"):
    _TOOL_TO_MODULE[_tool] = "messages"
for _tool in ("add_reaction", "remove_reaction", "get_reactions", "pin_message", "unpin_message", "get_thread"):
    _TOOL_TO_MODULE[_tool] = "posts"
for _tool in ("get_me", "get_user", "get_user_by_username", "search_users", "get_user_status"):
    _TOOL_TO_MODULE[_tool] = "users"
for _tool in ("list_teams", "get_team", "get_team_members"):
    _TOOL_TO_MODULE[_tool] = "teams"
for _tool in ("upload_file", "get_file_info", "get_file_link"):
    _TOOL_TO_MODULE[_tool] = "files"
for _tool in (
    "list_bookmarks",
    "create_bookmark",
    "update_bookmark",
    "delete_bookmark",
    "update_bookmark_sort_order",
):
    _TOOL_TO_MODULE[_tool] = "bookmarks"


def get_all_tools():
    """Collect all registered MCP tools from the server's tool manager."""
    tool_manager = mcp._tool_manager
    tools = []
    for name, tool in tool_manager._tools.items():
        module_name = _TOOL_TO_MODULE.get(name, "unknown")
        tools.append((module_name, name, tool))
    return tools


class TestAllToolsHaveMattermostTag:
    """Verify all tools include the MATTERMOST tag."""

    @pytest.mark.parametrize(("module_name", "tool_name", "tool"), get_all_tools())
    def test_tool_has_mattermost_tag(self, module_name, tool_name, tool):
        assert "mattermost" in tool.tags, f"{module_name}.{tool_name} missing MATTERMOST tag"


class TestToolTagConsistency:
    """Verify tools have appropriate category tags."""

    @pytest.mark.parametrize(("module_name", "tool_name", "tool"), get_all_tools())
    def test_tool_has_category_tag(self, module_name, tool_name, tool):
        module_to_tag = {
            "bookmarks": "bookmark",
            "channels": "channel",
            "messages": "message",
            "posts": "post",
            "users": "user",
            "teams": "team",
            "files": "file",
        }

        expected_tag = module_to_tag.get(module_name)

        if expected_tag:
            assert expected_tag in tool.tags, f"{module_name}.{tool_name} missing '{expected_tag}' tag"


class TestToolCount:
    """Verify expected number of tools are registered."""

    def test_total_tool_count(self):
        """Ensure we have the expected number of tools registered."""
        tool_manager = mcp._tool_manager
        assert len(tool_manager._tools) == 36, (
            f"Expected 36 tools, got {len(tool_manager._tools)}: {list(tool_manager._tools.keys())}"
        )
