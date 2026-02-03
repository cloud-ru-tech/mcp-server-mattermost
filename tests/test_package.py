def test_version_is_string():
    from mcp_server_mattermost import __version__

    assert isinstance(__version__, str)
    assert __version__


def test_main_is_callable():
    from mcp_server_mattermost import main

    assert callable(main)
