"""Test that all tool modules can be imported."""


def test_tools_package_imports() -> None:
    """Verify tools package imports all modules."""
    from mcp_server_mattermost import tools

    assert hasattr(tools, "bookmarks")
    assert hasattr(tools, "channels")
    assert hasattr(tools, "messages")
    assert hasattr(tools, "posts")
    assert hasattr(tools, "users")
    assert hasattr(tools, "teams")
    assert hasattr(tools, "files")


def test_tools_all_exports() -> None:
    """Verify __all__ contains all modules."""
    from mcp_server_mattermost import tools

    expected = ["bookmarks", "channels", "files", "messages", "posts", "teams", "users"]
    assert sorted(tools.__all__) == expected
