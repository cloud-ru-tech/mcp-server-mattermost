"""Common types and validators for Mattermost entities."""

import re
from typing import Annotated, Literal

from pydantic import AfterValidator, Field


MATTERMOST_ID_PATTERN = re.compile(r"^[a-zA-Z0-9]{26}$")


def validate_mattermost_id(v: str) -> str:
    """Validate Mattermost entity ID format.

    Mattermost uses 26-character alphanumeric IDs for all entities
    (channels, users, teams, posts, files).

    Args:
        v: String to validate

    Returns:
        The validated string

    Raises:
        ValueError: If format is invalid
    """
    if not MATTERMOST_ID_PATTERN.match(v):
        msg = f"Invalid Mattermost ID format: '{v}'. Must be exactly 26 alphanumeric characters."
        raise ValueError(msg)
    return v


_EXAMPLE_ID = "o5w8h47pdfbzjc4d8w7dhnhren"


def _id_desc(entity: str) -> str:
    """Generate description for Mattermost ID fields."""
    return f"26-character {entity} identifier (e.g., '{_EXAMPLE_ID}')"


MattermostId = Annotated[str, AfterValidator(validate_mattermost_id)]

ChannelId = Annotated[MattermostId, Field(description=_id_desc("channel"))]

UserId = Annotated[MattermostId, Field(description=_id_desc("user"))]

TeamId = Annotated[MattermostId, Field(description=_id_desc("team"))]

PostId = Annotated[MattermostId, Field(description=_id_desc("post/message"))]

FileId = Annotated[MattermostId, Field(description=_id_desc("file"))]

BookmarkId = Annotated[MattermostId, Field(description=_id_desc("bookmark"))]

ChannelType = Annotated[
    Literal["O", "P", "D", "G"],
    Field(
        description="Channel type: O=public, P=private, D=direct message, G=group message",
    ),
]

EmojiName = Annotated[
    str,
    Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_+-]+$",
        description="Emoji name without colons (e.g., 'thumbsup', 'smile')",
    ),
]

Username = Annotated[
    str,
    Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z][a-zA-Z0-9._-]*$",
        description="Mattermost username",
    ),
]

ChannelName = Annotated[
    str,
    Field(
        min_length=2,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9_-]*$",
        description="Channel name (lowercase, no spaces)",
    ),
]
