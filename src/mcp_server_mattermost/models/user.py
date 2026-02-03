"""User response models."""

from pydantic import Field

from .base import MattermostResponse


class User(MattermostResponse):
    """User profile in Mattermost."""

    id: str = Field(description="Unique user identifier")
    create_at: int = Field(default=0, description="Creation timestamp in milliseconds")
    update_at: int = Field(default=0, description="Last update timestamp in milliseconds")
    delete_at: int = Field(description="Deletion timestamp (0 if active)")
    username: str = Field(description="Unique username")
    first_name: str = Field(description="First name")
    last_name: str = Field(description="Last name")
    nickname: str = Field(description="Nickname")
    email: str = Field(description="Email address")
    email_verified: bool = Field(default=False, description="Email verification status")
    auth_service: str = Field(description="Authentication service")
    roles: str = Field(description="Space-separated system roles")
    locale: str = Field(description="User locale preference")
    last_password_update: int = Field(default=0, description="Last password change timestamp")
    last_picture_update: int = Field(default=0, description="Last avatar update timestamp")
    mfa_active: bool = Field(default=False, description="Multi-factor auth enabled")


class UserStatus(MattermostResponse):
    """User online status."""

    user_id: str = Field(description="User identifier")
    status: str = Field(description="Status: online, away, dnd, offline")
    manual: bool = Field(description="Manually set status")
    last_activity_at: int = Field(description="Last activity timestamp")
