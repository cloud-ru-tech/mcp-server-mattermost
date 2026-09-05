"""File operations tools."""

from typing import Annotated

from fastmcp.dependencies import Depends
from fastmcp.tools import tool
from pydantic import Field

from mcp_server_mattermost.client import MattermostClient
from mcp_server_mattermost.deps import get_client
from mcp_server_mattermost.enums import Capability, ToolTag
from mcp_server_mattermost.models import ChannelId, FileDownloadResponse, FileId, FileInfo, FileLink, FileUploadResponse


@tool(
    annotations={"destructiveHint": False},
    tags={ToolTag.MATTERMOST, ToolTag.FILE},
    meta={"capability": Capability.WRITE},
)
async def upload_file(
    channel_id: ChannelId,
    file_path: Annotated[str, Field(description="Local path to the file to upload")],
    filename: Annotated[str | None, Field(description="Override filename")] = None,
    client: MattermostClient = Depends(get_client),  # noqa: B008
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


@tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.FILE},
    meta={"capability": Capability.READ},
)
async def get_file_info(
    file_id: FileId,
    client: MattermostClient = Depends(get_client),  # noqa: B008
) -> FileInfo:
    """Get metadata about an uploaded file.

    Returns file name, size, type, and upload information.
    Use to check file details before downloading or sharing.
    """
    data = await client.get_file_info(file_id=file_id)
    return FileInfo(**data)


@tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.FILE},
    meta={"capability": Capability.READ},
)
async def get_file_link(
    file_id: FileId,
    client: MattermostClient = Depends(get_client),  # noqa: B008
) -> FileLink:
    """Get a public link to download a file.

    Link can be shared with users who don't have Mattermost access.
    Link may expire based on server settings.
    """
    data = await client.get_file_link(file_id=file_id)
    return FileLink(**data)


@tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.FILE},
    meta={"capability": Capability.READ},
)
async def download_file(
    file_id: FileId,
    destination_dir: Annotated[str, Field(description="Local directory to save the file into (created if missing)")],
    filename: Annotated[str | None, Field(description="Override the saved file name")] = None,
    overwrite: Annotated[bool, Field(description="Replace an existing file with the same name")] = False,  # noqa: FBT002
    client: MattermostClient = Depends(get_client),  # noqa: B008
) -> FileDownloadResponse:
    """Download a file attachment and save it to a local directory.

    Counterpart of upload_file: fetches the content of a file by its ID
    (from a post's file_ids or get_file_info) and writes it to disk.
    Returns the local path so the file can be read or processed further.
    Files larger than 100 MB are refused.
    """
    data = await client.download_file(
        file_id=file_id,
        destination_dir=destination_dir,
        filename=filename,
        overwrite=overwrite,
    )
    return FileDownloadResponse(**data)
