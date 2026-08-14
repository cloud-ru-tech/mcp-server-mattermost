"""Tests for post response models."""

from mcp_server_mattermost.models.post import Post, PostList, Reaction


def test_post_parses_minimal():
    """Test Post with all documented fields present."""
    data = {
        "id": "post123",
        "create_at": 1706400000000,
        "update_at": 1706400000000,
        "delete_at": 0,
        "edit_at": 0,
        "user_id": "user456",
        "channel_id": "ch789",
        "root_id": "",
        "original_id": "",
        "message": "Hello world",
        "type": "",
        "hashtags": "",
        "file_ids": [],
        "pending_post_id": "",
        "is_pinned": False,
    }

    post = Post(**data)
    assert post.id == "post123"
    assert post.message == "Hello world"
    assert post.root_id == ""


def test_post_parses_with_thread():
    """Test Post in a thread."""
    data = {
        "id": "post123",
        "create_at": 1706400000000,
        "update_at": 1706400000000,
        "delete_at": 0,
        "edit_at": 0,
        "user_id": "user456",
        "channel_id": "ch789",
        "root_id": "post000",
        "original_id": "",
        "message": "Reply",
        "type": "",
        "hashtags": "",
        "file_ids": ["file1", "file2"],
        "pending_post_id": "",
        "is_pinned": True,
    }

    post = Post(**data)
    assert post.root_id == "post000"
    assert len(post.file_ids) == 2
    assert post.is_pinned is True


def test_post_list_parses():
    """Test PostList with nested Post objects."""
    data = {
        "order": ["post2", "post1"],
        "posts": {
            "post1": {
                "id": "post1",
                "create_at": 1706400000000,
                "update_at": 1706400000000,
                "delete_at": 0,
                "edit_at": 0,
                "user_id": "user1",
                "channel_id": "ch1",
                "root_id": "",
                "original_id": "",
                "message": "First",
                "type": "",
                "hashtags": "",
                "file_ids": [],
                "pending_post_id": "",
                "is_pinned": False,
            },
            "post2": {
                "id": "post2",
                "create_at": 1706400000001,
                "update_at": 1706400000001,
                "delete_at": 0,
                "edit_at": 0,
                "user_id": "user2",
                "channel_id": "ch1",
                "root_id": "",
                "original_id": "",
                "message": "Second",
                "type": "",
                "hashtags": "",
                "file_ids": [],
                "pending_post_id": "",
                "is_pinned": False,
            },
        },
        "next_post_id": "",
        "prev_post_id": "",
    }

    post_list = PostList(**data)
    assert post_list.order == ["post2", "post1"]
    assert isinstance(post_list.posts["post1"], Post)
    assert post_list.posts["post1"].message == "First"
    assert post_list.posts["post2"].message == "Second"


def test_reaction_parses():
    """Test Reaction model."""
    data = {
        "user_id": "user123",
        "post_id": "post456",
        "emoji_name": "thumbsup",
        "create_at": 1706400000000,
    }

    reaction = Reaction(**data)
    assert reaction.emoji_name == "thumbsup"


def test_post_list_truncated_default_false() -> None:
    """truncated defaults to False — most responses are complete."""
    pl = PostList(order=[], posts={})
    assert pl.truncated is False


def test_post_list_truncated_can_be_set() -> None:
    """Tools may set truncated=True after detecting a cap hit."""
    pl = PostList(order=[], posts={}, truncated=True)
    assert pl.truncated is True


def _post_without_file_ids(post_id: str = "post123") -> dict:
    """Build a post payload with no file_ids key."""
    return {
        "id": post_id,
        "create_at": 1706400000000,
        "update_at": 1706400000000,
        "delete_at": 0,
        "edit_at": 0,
        "user_id": "user456",
        "channel_id": "ch789",
        "root_id": "",
        "original_id": "",
        "message": "Hello world",
        "type": "",
        "hashtags": "",
        "pending_post_id": "",
        "is_pinned": False,
    }


def test_post_parses_without_file_ids_key() -> None:
    """file_ids may be absent from the payload (#27)."""
    post = Post(**_post_without_file_ids())

    assert post.file_ids == []


def test_post_list_parses_nested_post_without_file_ids_key() -> None:
    """An absent file_ids key must not break nested parsing either (#27)."""
    post_list = PostList(order=["post1"], posts={"post1": _post_without_file_ids("post1")})

    assert post_list.posts["post1"].file_ids == []


def test_post_file_ids_default_is_not_shared_between_instances() -> None:
    """file_ids uses default_factory, so each Post gets its own list."""
    first = Post(**_post_without_file_ids("post1"))
    second = Post(**_post_without_file_ids("post2"))

    first.file_ids.append("fileX")

    assert second.file_ids == []
