"""Team response models."""

from pydantic import Field

from .base import MattermostResponse


class Team(MattermostResponse):
    """Team in Mattermost."""

    id: str = Field(description="Unique team identifier")
    create_at: int = Field(description="Creation timestamp in milliseconds")
    update_at: int = Field(description="Last update timestamp in milliseconds")
    delete_at: int = Field(description="Deletion timestamp (0 if active)")
    display_name: str = Field(description="Human-readable team name")
    name: str = Field(description="URL-friendly team name")
    description: str = Field(description="Team description")
    email: str = Field(description="Team contact email")
    type: str = Field(description="Team type: O=open, I=invite-only")
    allowed_domains: str = Field(description="Allowed email domains")
    invite_id: str = Field(description="Invite link identifier")
    allow_open_invite: bool = Field(description="Allow public joining")


class TeamMember(MattermostResponse):
    """Team membership information."""

    team_id: str = Field(description="Team identifier")
    user_id: str = Field(description="User identifier")
    roles: str = Field(description="Space-separated role names")
    delete_at: int = Field(description="Deletion timestamp")
    scheme_user: bool = Field(description="Has default user role")
    scheme_admin: bool = Field(description="Has default admin role")
