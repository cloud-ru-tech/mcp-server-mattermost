"""File response models."""

from pydantic import Field

from .base import MattermostResponse


class FileInfo(MattermostResponse):
    """Uploaded file metadata.

    Note: Go source uses CreatorId field name, but JSON response uses "user_id".

    See: https://github.com/mattermost/mattermost/blob/master/server/public/model/file_info.go
    """

    id: str = Field(description="Unique file identifier")
    user_id: str = Field(description="Uploader user identifier (CreatorId in Go)")
    post_id: str = Field(default="", description="Associated post ID")
    channel_id: str = Field(description="Channel where file was uploaded")
    create_at: int = Field(description="Upload timestamp in milliseconds")
    update_at: int = Field(description="Last update timestamp")
    delete_at: int = Field(description="Deletion timestamp")
    name: str = Field(description="File name")
    extension: str = Field(description="File extension without dot")
    size: int = Field(description="File size in bytes")
    mime_type: str = Field(description="MIME type")
    width: int = Field(default=0, description="Image width in pixels")
    height: int = Field(default=0, description="Image height in pixels")
    has_preview_image: bool = Field(default=False, description="Has generated preview")


class FileUploadResponse(MattermostResponse):
    """Response from file upload endpoint."""

    file_infos: list[FileInfo] = Field(description="Uploaded file information")
    client_ids: list[str] | None = Field(default=None, description="Client-provided IDs")


class FileLink(MattermostResponse):
    """Public file download link."""

    link: str = Field(description="Public download URL")
