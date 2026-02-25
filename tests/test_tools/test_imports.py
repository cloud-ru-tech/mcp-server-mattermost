"""Test that all tool modules can be imported."""


def test_tool_modules_importable() -> None:
    """Verify each tool module can be imported directly."""
    from mcp_server_mattermost.tools import bookmarks, channels, files, messages, posts, teams, users

    modules = [bookmarks, channels, files, messages, posts, teams, users]
    assert all(mod is not None for mod in modules)


def test_tool_modules_have_tool_functions() -> None:
    """Verify each tool module contains @tool-decorated functions."""
    from mcp_server_mattermost.tools import bookmarks, channels, files, messages, posts, teams, users

    for mod in [bookmarks, channels, files, messages, posts, teams, users]:
        tool_funcs = [
            name
            for name in dir(mod)
            if not name.startswith("_") and callable(getattr(mod, name)) and hasattr(getattr(mod, name), "__fastmcp__")
        ]
        assert len(tool_funcs) > 0, f"{mod.__name__} has no @tool-decorated functions"
