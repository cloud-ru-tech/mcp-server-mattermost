"""Tests for forward compatibility with unknown API fields."""

from mcp_server_mattermost.models import Channel, Post, User
from tests.test_tools.conftest import make_post_data


def make_channel_data(**overrides) -> dict:
    """Create channel data with all required fields."""
    return {
        "id": "ch1234567890123456789012",
        "create_at": 1706400000000,
        "update_at": 1706400000000,
        "delete_at": 0,
        "team_id": "tm1234567890123456789012",
        "type": "O",
        "display_name": "General",
        "name": "general",
        "header": "",
        "purpose": "",
        "last_post_at": 0,
        "total_msg_count": 0,
        "extra_update_at": 0,
        "creator_id": "",
        "scheme_id": "",
        "group_constrained": False,
        "shared": False,
        **overrides,
    }


def make_user_data(**overrides) -> dict:
    """Create user data with all required fields."""
    return {
        "id": "us1234567890123456789012",
        "delete_at": 0,
        "username": "testuser",
        "auth_service": "",
        "email": "test@example.com",
        "nickname": "",
        "first_name": "",
        "last_name": "",
        "position": "",
        "roles": "system_user",
        "locale": "en",
        **overrides,
    }


class TestForwardCompatibility:
    """Test that models preserve unknown fields from future API versions."""

    def test_channel_preserves_unknown_fields(self) -> None:
        """Test Channel model accepts and preserves unknown API fields."""
        data = make_channel_data(
            future_field="some_value",
            another_new_field=12345,
        )

        channel = Channel(**data)

        assert channel.id == "ch1234567890123456789012"
        assert channel.__pydantic_extra__["future_field"] == "some_value"
        assert channel.__pydantic_extra__["another_new_field"] == 12345

    def test_post_preserves_unknown_fields(self) -> None:
        """Test Post model accepts and preserves unknown API fields."""
        data = make_post_data(
            new_api_field="new_value",
            priority_field={"urgent": True},
        )

        post = Post(**data)

        assert post.message == "Hello, World!"
        assert post.__pydantic_extra__["new_api_field"] == "new_value"
        assert post.__pydantic_extra__["priority_field"] == {"urgent": True}

    def test_user_preserves_unknown_fields(self) -> None:
        """Test User model accepts and preserves unknown API fields."""
        data = make_user_data(
            custom_status={"emoji": "smile", "text": "Working"},
        )

        user = User(**data)

        assert user.username == "testuser"
        assert user.__pydantic_extra__["custom_status"]["emoji"] == "smile"

    def test_extra_fields_included_in_model_dump(self) -> None:
        """Test that model_dump() includes extra fields for serialization."""
        data = make_channel_data(experimental_feature=True)

        channel = Channel(**data)
        dumped = channel.model_dump()

        assert dumped["experimental_feature"] is True
        assert dumped["id"] == "ch1234567890123456789012"
