"""Tests for file tools."""

from unittest.mock import AsyncMock

from mcp_server_mattermost.models import FileInfo, FileLink, FileUploadResponse
from mcp_server_mattermost.tools import files


def make_file_info_data(
    file_id: str = "fl1234567890123456789012",
    name: str = "test.txt",
    **overrides,
) -> dict:
    """Create full file info mock data.

    Most fields required per Go source. Optional fields have omitempty in Go.
    """
    return {
        "id": file_id,
        "user_id": "us1234567890123456789012",
        "channel_id": "ch1234567890123456789012",
        "create_at": 1706400000000,
        "update_at": 1706400000000,
        "delete_at": 0,
        "name": name,
        "extension": "txt",
        "size": 1234,
        "mime_type": "text/plain",
        "post_id": "",
        "width": 0,
        "height": 0,
        "has_preview_image": False,
        **overrides,
    }


class TestUploadFile:
    """Tests for upload_file tool."""

    async def test_upload_file(self, mock_client: AsyncMock) -> None:
        """Test uploading a file returns FileUploadResponse model."""
        mock_client.upload_file.return_value = {"file_infos": [make_file_info_data()], "client_ids": []}

        result = await files.upload_file(
            channel_id="ch1234567890123456789012",
            file_path="/path/to/test.txt",
            client=mock_client,
        )

        assert isinstance(result, FileUploadResponse)
        assert len(result.file_infos) == 1
        assert isinstance(result.file_infos[0], FileInfo)

    async def test_upload_file_with_custom_name(self, mock_client: AsyncMock) -> None:
        """Test uploading a file with custom filename."""
        mock_client.upload_file.return_value = {
            "file_infos": [make_file_info_data(name="custom.txt")],
            "client_ids": [],
        }

        await files.upload_file(
            channel_id="ch1234567890123456789012",
            file_path="/path/to/test.txt",
            filename="custom.txt",
            client=mock_client,
        )

        mock_client.upload_file.assert_called_once_with(
            channel_id="ch1234567890123456789012",
            file_path="/path/to/test.txt",
            filename="custom.txt",
        )


class TestGetFileInfo:
    """Tests for get_file_info tool."""

    async def test_get_file_info(self, mock_client: AsyncMock) -> None:
        """Test getting file info returns FileInfo model."""
        mock_client.get_file_info.return_value = make_file_info_data(size=1234)

        result = await files.get_file_info(
            file_id="fl1234567890123456789012",
            client=mock_client,
        )

        assert isinstance(result, FileInfo)
        assert result.name == "test.txt"


class TestGetFileLink:
    """Tests for get_file_link tool."""

    async def test_get_file_link(self, mock_client: AsyncMock) -> None:
        """Test getting file download link returns FileLink model."""
        mock_client.get_file_link.return_value = {
            "link": "https://mattermost.example.com/files/fl1234567890123456789012",
        }

        result = await files.get_file_link(
            file_id="fl1234567890123456789012",
            client=mock_client,
        )

        assert isinstance(result, FileLink)
        assert "fl1234567890123456789012" in result.link
