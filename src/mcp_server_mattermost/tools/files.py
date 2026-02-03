"""File operations tools."""

from typing import Annotated

from fastmcp.dependencies import Depends
from pydantic import Field

from mcp_server_mattermost.client import MattermostClient
from mcp_server_mattermost.enums import ToolTag
from mcp_server_mattermost.models import ChannelId, FileId, FileInfo, FileLink, FileUploadResponse
from mcp_server_mattermost.server import get_client, mcp


@mcp.tool(
    annotations={"destructiveHint": False},
    tags={ToolTag.MATTERMOST, ToolTag.FILE},
)
async def upload_file(
    channel_id: ChannelId,
    file_path: Annotated[str, Field(description="Local path to the file to upload")],
    filename: Annotated[str | None, Field(description="Override filename")] = None,
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> FileUploadResponse:
    """Upload a file to a channel.

    The file will be attached to messages in the specified channel.
    Returns file ID that can be used when posting messages with file_ids parameter.
    """
    data = await client.upload_file(
        channel_id=channel_id,
        file_path=file_path,
        filename=filename,
    )
    return FileUploadResponse(**data)


@mcp.tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.FILE},
)
async def get_file_info(
    file_id: FileId,
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> FileInfo:
    """Get metadata about an uploaded file.

    Returns file name, size, type, and upload information.
    Use to check file details before downloading or sharing.
    """
    data = await client.get_file_info(file_id=file_id)
    return FileInfo(**data)


@mcp.tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.FILE},
)
async def get_file_link(
    file_id: FileId,
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> FileLink:
    """Get a public link to download a file.

    Link can be shared with users who don't have Mattermost access.
    Link may expire based on server settings.
    """
    data = await client.get_file_link(file_id=file_id)
    return FileLink(**data)
