"""File operations tools."""

from typing import Annotated, Literal

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
    file_path: Annotated[str, Field(description="Local path to the file to upload; a leading '~' is expanded")],
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
    # A read on the Mattermost side, but a write on the host's: it creates directories
    # and puts a file on local disk. ``capability`` is the project's access-control axis
    # (docs/building-agents.md), so WRITE is what keeps this out of a reader profile.
    # The tool keeps FastMCP's destructive default because overwrite=True can discard
    # an existing file's contents irreversibly.
    tags={ToolTag.MATTERMOST, ToolTag.FILE},
    meta={"capability": Capability.WRITE},
)
async def download_file(  # noqa: PLR0913 — retain overwrite compatibility alongside the conflict policy
    file_id: FileId,
    destination_dir: Annotated[
        str,
        Field(description="Local directory to save the file into (created if missing); a leading '~' is expanded"),
    ],
    filename: Annotated[str | None, Field(description="Override the saved file name")] = None,
    overwrite: Annotated[bool, Field(description="Replace an existing file with the same name")] = False,  # noqa: FBT002
    client: MattermostClient = Depends(get_client),  # noqa: B008
    *,
    on_conflict: Annotated[
        Literal["error", "rename", "overwrite"] | None,
        Field(description="Name conflict policy; null uses overwrite. rename keeps all files with numbered names"),
    ] = None,
) -> FileDownloadResponse:
    """Download a file attachment and save it to a local directory.

    Counterpart of upload_file: fetches the content of a file by its ID
    (from a post's file_ids or get_file_info) and writes it to disk.
    Returns the local path so the file can be read or processed further.
    Use on_conflict="rename" to save all same-named attachments without replacing any.
    Always use the returned path; parallel calls may assign numbers in any order.
    Each repeated call in rename mode saves another copy. overwrite=True cannot
    be combined with on_conflict="error" or "rename".
    Files larger than 100 MB are refused.
    """
    data = await client.download_file(
        file_id=file_id,
        destination_dir=destination_dir,
        filename=filename,
        overwrite=overwrite,
        on_conflict=on_conflict,
    )
    return FileDownloadResponse(**data)
