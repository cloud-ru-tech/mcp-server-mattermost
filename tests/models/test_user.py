"""Tests for user response models."""

from mcp_server_mattermost.models.user import User, UserStatus


def test_user_parses_minimal():
    """Test User with minimal required fields (create_at/update_at optional with defaults per Go omitempty)."""
    data = {
        "id": "user123",
        "delete_at": 0,
        "username": "john.doe",
        "first_name": "",
        "last_name": "",
        "nickname": "",
        "email": "",
        "auth_service": "",
        "roles": "",
        "locale": "en",
    }

    user = User(**data)
    assert user.id == "user123"
    assert user.username == "john.doe"
    assert user.first_name == ""
    assert user.create_at == 0  # Default since omitempty in Go


def test_user_parses_full():
    """Test User with all fields."""
    data = {
        "id": "user123",
        "create_at": 1706400000000,
        "update_at": 1706400000000,
        "delete_at": 0,
        "username": "john.doe",
        "first_name": "John",
        "last_name": "Doe",
        "nickname": "JD",
        "email": "john@example.com",
        "email_verified": True,
        "auth_service": "gitlab",
        "roles": "system_user",
        "locale": "en",
        "last_password_update": 1706400000000,
        "last_picture_update": 1706400000000,
        "mfa_active": False,
        "position": "Engineer",  # Extra field
    }

    user = User(**data)
    assert user.first_name == "John"
    assert user.email_verified is True
    assert user.__pydantic_extra__["position"] == "Engineer"


def test_user_status_parses():
    """Test UserStatus model."""
    data = {
        "user_id": "user123",
        "status": "online",
        "manual": False,
        "last_activity_at": 1706400000000,
    }

    status = UserStatus(**data)
    assert status.user_id == "user123"
    assert status.status == "online"
    assert status.manual is False
