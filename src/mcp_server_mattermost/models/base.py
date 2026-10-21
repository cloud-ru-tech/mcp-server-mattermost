"""Base classes for Mattermost API response models."""

from pydantic import BaseModel, ConfigDict


class MattermostResponse(BaseModel):
    """Base class for all Mattermost API response models.

    Uses extra="allow" to preserve unknown fields from API
    while providing typed access to documented fields.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        # FastMCP 4 emits field names unless a model opts into aliases; keep the
        # Mattermost wire names (e.g. ``file``) in tool results and output schemas.
        serialize_by_alias=True,
    )
