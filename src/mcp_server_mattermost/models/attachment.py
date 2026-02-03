"""Attachment models for rich message formatting."""

import re
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator


# Color validation
ATTACHMENT_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
VALID_COLOR_KEYWORDS = frozenset({"good", "warning", "danger"})


def validate_attachment_color(v: str) -> str:
    """Validate attachment color is keyword or hex."""
    if v in VALID_COLOR_KEYWORDS or ATTACHMENT_COLOR_PATTERN.match(v):
        return v
    msg = f"Invalid color '{v}': must be 'good', 'warning', 'danger', or #RRGGBB hex"
    raise ValueError(msg)


AttachmentColor = Annotated[str, AfterValidator(validate_attachment_color)]


class AttachmentField(BaseModel):
    """Field within attachment for table display.

    Fields are displayed as key-value pairs within the attachment.
    Use short=True to display fields side-by-side.
    """

    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="Field label/header")
    value: str | int = Field(description="Field content (string or number)")
    short: bool = Field(default=False, description="Display inline with other short fields")

    def to_api_dict(self) -> dict[str, Any]:
        """Convert to API-compatible dict."""
        return self.model_dump()


class Attachment(BaseModel):
    """Rich message attachment for formatted content.

    Attachments add structured content to messages with colors, fields,
    author info, and images. Based on Slack attachment format.

    All fields are optional. Use color for visual emphasis,
    fields for structured data, and author_* for attribution.
    """

    model_config = ConfigDict(extra="forbid")

    # Metadata
    id: int | None = Field(default=None, description="Attachment ID (auto-generated)")
    fallback: str | None = Field(default=None, description="Plain-text summary for notifications")

    # Styling
    color: AttachmentColor | None = Field(
        default=None,
        description="Left border color: 'good', 'warning', 'danger', or #RRGGBB hex",
    )

    # Content
    pretext: str | None = Field(default=None, description="Text above attachment")
    text: str | None = Field(default=None, description="Main content (supports Markdown)")

    # Author
    author_name: str | None = Field(default=None, description="Author display name")
    author_link: str | None = Field(default=None, description="Author profile URL (requires author_name)")
    author_icon: str | None = Field(default=None, description="Author avatar URL")

    # Title
    title: str | None = Field(default=None, description="Attachment title")
    title_link: str | None = Field(default=None, description="Title hyperlink URL (requires title)")

    # Fields
    fields: list[AttachmentField] | None = Field(default=None, description="Structured data fields")

    # Images
    image_url: str | None = Field(default=None, description="Main image URL")
    thumb_url: str | None = Field(default=None, description="Thumbnail image URL (75x75)")

    # Footer
    footer: str | None = Field(default=None, description="Footer text (max 300 chars)")
    footer_icon: str | None = Field(default=None, description="Footer icon URL")

    # Timestamp
    ts: str | int | None = Field(default=None, description="Unix timestamp for footer")

    @model_validator(mode="after")
    def validate_link_dependencies(self) -> "Attachment":
        """Validate that links have required parent fields."""
        if self.author_link and not self.author_name:
            msg = "author_link requires author_name to be set"
            raise ValueError(msg)
        if self.title_link and not self.title:
            msg = "title_link requires title to be set"
            raise ValueError(msg)
        return self

    def to_api_dict(self) -> dict[str, Any]:
        """Convert to API-compatible dict, excluding None values."""
        return self.model_dump(exclude_none=True)
