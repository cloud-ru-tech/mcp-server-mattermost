"""Tests for capability metadata on all tools."""

import pytest
from fastmcp import Client

from mcp_server_mattermost.enums import Capability


# Expected capabilities for every tool (source of truth from design doc)
EXPECTED_CAPABILITIES: dict[str, Capability] = {
    # channels.py
    "list_channels": Capability.READ,
    "get_channel": Capability.READ,
    "get_channel_by_name": Capability.READ,
    "create_channel": Capability.CREATE,
    "join_channel": Capability.WRITE,
    "leave_channel": Capability.WRITE,
    "get_channel_members": Capability.READ,
    "add_user_to_channel": Capability.WRITE,
    "create_direct_channel": Capability.CREATE,
    # messages.py
    "post_message": Capability.WRITE,
    "get_channel_messages": Capability.READ,
    "search_messages": Capability.READ,
    "update_message": Capability.WRITE,
    "delete_message": Capability.DELETE,
    # posts.py
    "add_reaction": Capability.WRITE,
    "remove_reaction": Capability.WRITE,
    "get_reactions": Capability.READ,
    "pin_message": Capability.WRITE,
    "unpin_message": Capability.WRITE,
    "get_thread": Capability.READ,
    # users.py
    "get_me": Capability.READ,
    "get_user": Capability.READ,
    "get_user_by_username": Capability.READ,
    "search_users": Capability.READ,
    "get_user_status": Capability.READ,
    # teams.py
    "list_teams": Capability.READ,
    "get_team": Capability.READ,
    "get_team_members": Capability.READ,
    # files.py
    "upload_file": Capability.WRITE,
    "get_file_info": Capability.READ,
    "get_file_link": Capability.READ,
    # bookmarks.py
    "list_bookmarks": Capability.READ,
    "create_bookmark": Capability.WRITE,
    "update_bookmark": Capability.WRITE,
    "delete_bookmark": Capability.DELETE,
    "update_bookmark_sort_order": Capability.WRITE,
}


@pytest.fixture
async def all_tools(mock_settings):
    """Get all registered FastMCP tools."""
    from mcp_server_mattermost.server import mcp

    tools = await mcp.list_tools()
    return {t.name: t for t in tools}


class TestCapabilityPresence:
    """Every tool must have a capability in meta."""

    def test_all_tools_have_capability(self, all_tools):
        """Every registered tool must have meta.capability."""
        missing = []
        for name, tool in all_tools.items():
            if not tool.meta or "capability" not in tool.meta:
                missing.append(name)
        assert not missing, f"Tools missing capability meta: {missing}"

    def test_capability_values_are_valid(self, all_tools):
        """Every capability value must be a valid Capability enum member."""
        valid = {c.value for c in Capability}
        invalid = []
        for name, tool in all_tools.items():
            cap = (tool.meta or {}).get("capability")
            if cap not in valid:
                invalid.append(f"{name}: {cap!r}")
        assert not invalid, f"Tools with invalid capability: {invalid}"

    def test_no_unexpected_tools(self, all_tools):
        """Catch new tools that are not in EXPECTED_CAPABILITIES."""
        unexpected = set(all_tools.keys()) - set(EXPECTED_CAPABILITIES.keys())
        assert not unexpected, (
            f"New tools not in EXPECTED_CAPABILITIES: {unexpected}. Add them to the dict in test_capability_meta.py."
        )


class TestCapabilityClassification:
    """Each tool has the correct capability."""

    @pytest.mark.parametrize(
        ("tool_name", "expected_cap"),
        list(EXPECTED_CAPABILITIES.items()),
        ids=list(EXPECTED_CAPABILITIES.keys()),
    )
    def test_tool_has_expected_capability(self, all_tools, tool_name, expected_cap):
        """Tool capability matches design classification."""
        tool = all_tools[tool_name]
        actual = (tool.meta or {}).get("capability")
        assert actual == expected_cap, f"{tool_name}: expected capability={expected_cap!r}, got {actual!r}"


class TestCapabilityAnnotationConsistency:
    """Capability must be consistent with annotations."""

    @pytest.mark.parametrize(
        ("tool_name", "expected_cap"),
        list(EXPECTED_CAPABILITIES.items()),
        ids=list(EXPECTED_CAPABILITIES.keys()),
    )
    def test_capability_matches_annotations(self, all_tools, tool_name, expected_cap):
        """Capability and annotations must not contradict each other."""
        tool = all_tools[tool_name]
        ann = tool.annotations or {}
        # annotations is ToolAnnotations object, access via attributes
        read_only = getattr(ann, "readOnlyHint", None)
        destructive = getattr(ann, "destructiveHint", None)

        if expected_cap == Capability.READ:
            assert read_only is True, f"{tool_name}: capability=read but readOnlyHint={read_only}"
        elif expected_cap in (Capability.WRITE, Capability.CREATE):
            assert read_only is not True, f"{tool_name}: capability={expected_cap} but readOnlyHint=True"
            assert destructive is False, f"{tool_name}: capability={expected_cap} but destructiveHint={destructive}"
        elif expected_cap == Capability.DELETE:
            assert read_only is not True, f"{tool_name}: capability=delete but readOnlyHint=True"
            # delete tools use default annotations (destructiveHint defaults to true)


class TestCapabilityWireFormat:
    """Capability must be visible through MCP protocol (tools/list)."""

    @pytest.fixture
    async def wire_tools(self, mock_settings):
        """Get tools via MCP protocol (in-memory transport)."""
        from mcp_server_mattermost.server import mcp

        async with Client(mcp) as client:
            tools = await client.list_tools()
            return {t.name: t for t in tools}

    @pytest.mark.asyncio
    async def test_all_tools_expose_capability_via_protocol(self, wire_tools):
        """Every tool must expose capability in meta through MCP wire format."""
        valid = {c.value for c in Capability}
        missing = []
        invalid = []
        for name, tool in wire_tools.items():
            cap = (tool.meta or {}).get("capability")
            if cap is None:
                missing.append(name)
            elif cap not in valid:
                invalid.append(f"{name}: {cap!r}")
        assert not missing, f"Tools missing capability in wire format: {missing}"
        assert not invalid, f"Tools with invalid capability in wire format: {invalid}"

    @pytest.mark.asyncio
    async def test_wire_capabilities_match_expected(self, wire_tools):
        """Wire format capabilities must match EXPECTED_CAPABILITIES."""
        mismatches = []
        for name, expected_cap in EXPECTED_CAPABILITIES.items():
            tool = wire_tools.get(name)
            if tool is None:
                mismatches.append(f"{name}: not found in wire format")
                continue
            actual = (tool.meta or {}).get("capability")
            if actual != expected_cap.value:
                mismatches.append(f"{name}: expected {expected_cap.value!r}, got {actual!r}")
        assert not mismatches, f"Wire format mismatches: {mismatches}"


class TestCapabilityCounts:
    """Sanity checks on capability distribution."""

    def test_expected_tool_count(self):
        """Total tool count matches expectations."""
        assert len(EXPECTED_CAPABILITIES) == 36

    def test_capability_distribution(self):
        """Capability distribution matches design."""
        counts: dict[Capability, int] = {}
        for cap in EXPECTED_CAPABILITIES.values():
            counts[cap] = counts.get(cap, 0) + 1
        assert counts[Capability.READ] == 19
        assert counts[Capability.WRITE] == 13
        assert counts[Capability.CREATE] == 2
        assert counts[Capability.DELETE] == 2
