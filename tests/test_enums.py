from enum import Enum


def test_tool_tags_enum_exists():
    from mcp_server_mattermost.enums import ToolTag

    assert issubclass(ToolTag, Enum)


def test_tool_tags_values():
    from mcp_server_mattermost.enums import ToolTag

    assert ToolTag.MATTERMOST.value == "mattermost"
    assert ToolTag.CHANNEL.value == "channel"
    assert ToolTag.MESSAGE.value == "message"
    assert ToolTag.USER.value == "user"
    assert ToolTag.TEAM.value == "team"
    assert ToolTag.FILE.value == "file"
    assert ToolTag.POST.value == "post"


def test_bookmark_tag_exists():
    """BOOKMARK tag should exist in ToolTag enum."""
    from mcp_server_mattermost.enums import ToolTag

    assert hasattr(ToolTag, "BOOKMARK")
    assert ToolTag.BOOKMARK.value == "bookmark"


def test_tool_tags_are_strings():
    from mcp_server_mattermost.enums import ToolTag

    # ToolTag should be usable as string (str, Enum)
    assert isinstance(ToolTag.MATTERMOST, str)
    assert ToolTag.MATTERMOST == "mattermost"
