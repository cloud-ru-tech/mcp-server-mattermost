"""Comprehensive tests for tool tags across all modules."""

import pytest


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

_MODULE_TO_TAG: dict[str, str] = {
    "bookmarks": "bookmark",
    "channels": "channel",
    "messages": "message",
    "posts": "post",
    "users": "user",
    "teams": "team",
    "files": "file",
}


@pytest.fixture
async def all_tools(mock_settings):
    from mcp_server_mattermost.server import mcp

    tools = await mcp.list_tools()
    return {t.name: t for t in tools}


class TestAllToolsHaveMattermostTag:
    """Verify all tools include the MATTERMOST tag."""

    @pytest.mark.parametrize("tool_name", list(_TOOL_TO_MODULE.keys()))
    async def test_tool_has_mattermost_tag(self, all_tools, tool_name):
        tool = all_tools[tool_name]
        module_name = _TOOL_TO_MODULE[tool_name]
        assert "mattermost" in tool.tags, f"{module_name}.{tool_name} missing MATTERMOST tag"


class TestToolTagConsistency:
    """Verify tools have appropriate category tags."""

    @pytest.mark.parametrize("tool_name", list(_TOOL_TO_MODULE.keys()))
    async def test_tool_has_category_tag(self, all_tools, tool_name):
        tool = all_tools[tool_name]
        module_name = _TOOL_TO_MODULE[tool_name]
        expected_tag = _MODULE_TO_TAG.get(module_name)
        if expected_tag:
            assert expected_tag in tool.tags, f"{module_name}.{tool_name} missing '{expected_tag}' tag"


class TestToolCount:
    """Verify expected number of tools are registered."""

    async def test_total_tool_count(self, all_tools):
        assert len(all_tools) == 36, f"Expected 36 tools, got {len(all_tools)}: {list(all_tools.keys())}"

    async def test_no_unexpected_tools(self, all_tools):
        """Catch new tools not in _TOOL_TO_MODULE."""
        unexpected = set(all_tools.keys()) - set(_TOOL_TO_MODULE.keys())
        assert not unexpected, (
            f"New tools not in _TOOL_TO_MODULE: {unexpected}. Add them to the mapping in test_tool_tags.py."
        )
