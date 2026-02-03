def test_constants_module_exists():
    from mcp_server_mattermost import constants

    # Empty result messages
    assert hasattr(constants, "NO_CHANNELS_FOUND")
    assert hasattr(constants, "NO_MESSAGES_FOUND")
    assert hasattr(constants, "NO_POSTS_FOUND")
    assert hasattr(constants, "NO_USERS_FOUND")
    assert hasattr(constants, "NO_TEAMS_FOUND")
    assert hasattr(constants, "NO_FILES_FOUND")
    assert hasattr(constants, "NO_REACTIONS_FOUND")

    # Success messages
    assert hasattr(constants, "CHANNEL_CREATED")
    assert hasattr(constants, "CHANNEL_JOINED")
    assert hasattr(constants, "CHANNEL_LEFT")
    assert hasattr(constants, "USER_ADDED_TO_CHANNEL")
    assert hasattr(constants, "MESSAGE_POSTED")
    assert hasattr(constants, "MESSAGE_DELETED")
    assert hasattr(constants, "REACTION_ADDED")
    assert hasattr(constants, "REACTION_REMOVED")
    assert hasattr(constants, "PIN_ADDED")
    assert hasattr(constants, "PIN_REMOVED")
    assert hasattr(constants, "FILE_UPLOADED")


def test_constants_are_strings():
    from mcp_server_mattermost import constants

    assert isinstance(constants.NO_CHANNELS_FOUND, str)
    assert isinstance(constants.NO_MESSAGES_FOUND, str)
    assert isinstance(constants.NO_USERS_FOUND, str)
    assert isinstance(constants.NO_TEAMS_FOUND, str)


def test_constants_not_empty():
    from mcp_server_mattermost import constants

    assert len(constants.NO_CHANNELS_FOUND) > 0
    assert len(constants.NO_MESSAGES_FOUND) > 0
    assert len(constants.NO_USERS_FOUND) > 0
    assert len(constants.NO_TEAMS_FOUND) > 0
