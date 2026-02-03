"""Tests for file response models."""

from mcp_server_mattermost.models.file import FileInfo, FileLink, FileUploadResponse


def test_file_info_parses():
    """Test FileInfo model (most fields required, post_id/width/height/has_preview_image optional)."""
    data = {
        "id": "file123",
        "user_id": "user456",
        "channel_id": "ch789",
        "create_at": 1706400000000,
        "update_at": 1706400000000,
        "delete_at": 0,
        "name": "document.pdf",
        "extension": "pdf",
        "size": 1024000,
        "mime_type": "application/pdf",
    }

    file_info = FileInfo(**data)
    assert file_info.id == "file123"
    assert file_info.name == "document.pdf"
    assert file_info.size == 1024000
    assert file_info.channel_id == "ch789"


def test_file_info_with_image_dimensions():
    """Test FileInfo for image with dimensions."""
    data = {
        "id": "file123",
        "user_id": "user456",
        "channel_id": "ch789",
        "create_at": 1706400000000,
        "update_at": 1706400000000,
        "delete_at": 0,
        "name": "screenshot.png",
        "extension": "png",
        "size": 500000,
        "mime_type": "image/png",
        "width": 1920,
        "height": 1080,
        "has_preview_image": True,
    }

    file_info = FileInfo(**data)
    assert file_info.width == 1920
    assert file_info.height == 1080
    assert file_info.has_preview_image is True


def test_file_upload_response_parses():
    """Test FileUploadResponse with nested FileInfo."""
    data = {
        "file_infos": [
            {
                "id": "file1",
                "user_id": "user1",
                "channel_id": "ch1",
                "create_at": 1706400000000,
                "update_at": 1706400000000,
                "delete_at": 0,
                "name": "file1.txt",
                "extension": "txt",
                "size": 100,
                "mime_type": "text/plain",
            },
        ],
        "client_ids": ["client123"],
    }

    response = FileUploadResponse(**data)
    assert len(response.file_infos) == 1
    assert isinstance(response.file_infos[0], FileInfo)
    assert response.file_infos[0].name == "file1.txt"


def test_file_link_parses():
    """Test FileLink model."""
    data = {"link": "https://mattermost.example.com/api/v4/files/file123"}

    file_link = FileLink(**data)
    assert "file123" in file_link.link
