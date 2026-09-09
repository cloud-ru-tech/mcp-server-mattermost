"""Tests for bookmark response models."""

import pytest
from pydantic import ValidationError

from mcp_server_mattermost.models.bookmark import ChannelBookmark
from mcp_server_mattermost.models.file import FileInfo


def test_bookmark_parses_minimal_fields():
    """Test ChannelBookmark with only required fields."""
    data = {
        "id": "bm123",
        "create_at": 1706400000000,
        "update_at": 1706400000000,
        "delete_at": 0,
        "channel_id": "ch456",
        "owner_id": "user789",
        "file_id": "",
        "display_name": "My Bookmark",
        "sort_order": 0,
        "type": "link",
    }

    bookmark = ChannelBookmark(**data)
    assert bookmark.id == "bm123"
    assert bookmark.display_name == "My Bookmark"
    assert bookmark.type == "link"
    assert bookmark.link_url is None


def test_bookmark_parses_link_type():
    """Test ChannelBookmark with link type and URL."""
    data = {
        "id": "bm123",
        "create_at": 1706400000000,
        "update_at": 1706400000000,
        "delete_at": 0,
        "channel_id": "ch456",
        "owner_id": "user789",
        "file_id": "",
        "display_name": "Documentation",
        "sort_order": 1,
        "type": "link",
        "link_url": "https://docs.example.com",
        "emoji": "book",
    }

    bookmark = ChannelBookmark(**data)
    assert bookmark.link_url == "https://docs.example.com"
    assert bookmark.emoji == "book"
    assert bookmark.file_info is None


@pytest.mark.parametrize("key", ["file", "file_info"])
def test_bookmark_parses_file_type(file_bookmark_data, key):
    """Parse the server key and the legacy Python field name into typed metadata."""
    data = file_bookmark_data
    data[key] = data.pop("file")

    bookmark = ChannelBookmark(**data)
    assert isinstance(bookmark.file_info, FileInfo)
    assert bookmark.file_info.id == "fl123456789012345678901234"
    assert bookmark.file_info.name == "doc.pdf"
    assert bookmark.file_info.size == 1024
    assert bookmark.file_info.user_id == ""
    assert bookmark.file_info.create_at == 0
    assert bookmark.file_info.width == 0
    assert "file" not in bookmark.model_extra
    assert bookmark.file_info.model_extra["mini_preview"] is None
    assert bookmark.file_info.model_extra["remote_id"] is None
    assert bookmark.file_info.model_extra["archived"] is False

    serialized = bookmark.model_dump(by_alias=True)
    assert serialized["file"]["id"] == "fl123456789012345678901234"
    assert serialized["file"]["mini_preview"] is None
    assert serialized["file"]["remote_id"] is None
    assert serialized["file"]["archived"] is False
    assert "file_info" not in serialized


@pytest.mark.parametrize("include_null", [False, True])
def test_bookmark_accepts_missing_file_metadata(file_bookmark_data, include_null):
    data = file_bookmark_data
    data.pop("file")
    if include_null:
        data["file"] = None

    bookmark = ChannelBookmark(**data)

    assert bookmark.file_info is None
    assert "file" not in bookmark.model_extra


def test_bookmark_rejects_incomplete_file_metadata(file_bookmark_data):
    file_bookmark_data["file"] = {"id": "file123", "name": "doc.pdf"}

    with pytest.raises(ValidationError, match="user_id"):
        ChannelBookmark(**file_bookmark_data)


def test_bookmark_allows_extra_fields():
    """Test ChannelBookmark preserves extra fields from API."""
    data = {
        "id": "bm123",
        "create_at": 1706400000000,
        "update_at": 1706400000000,
        "delete_at": 0,
        "channel_id": "ch456",
        "owner_id": "user789",
        "file_id": "",
        "display_name": "Test",
        "sort_order": 0,
        "type": "link",
        "new_field_from_api": "future_value",
    }

    bookmark = ChannelBookmark(**data)
    assert bookmark.__pydantic_extra__["new_field_from_api"] == "future_value"


def test_bookmark_generates_json_schema():
    """Test that ChannelBookmark generates proper JSON schema."""
    schema = ChannelBookmark.model_json_schema()

    assert schema["type"] == "object"
    assert "id" in schema["properties"]
    assert "display_name" in schema["properties"]
    assert "type" in schema["properties"]
    assert schema["properties"]["id"]["type"] == "string"
    assert "description" in schema["properties"]["id"]
    assert schema["properties"]["file"]["anyOf"] == [{"$ref": "#/$defs/FileInfo"}, {"type": "null"}]
    assert schema["$defs"]["FileInfo"]["properties"]["size"]["type"] == "integer"
    assert "file" not in schema["required"]
    assert "file_info" not in schema["properties"]


def test_bookmark_requires_all_required_fields():
    """Test that missing required fields raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        ChannelBookmark(id="bm123")  # Missing other required fields

    errors = exc_info.value.errors()
    missing_fields = {e["loc"][0] for e in errors if e["type"] == "missing"}

    # All these fields are required
    assert "create_at" in missing_fields
    assert "channel_id" in missing_fields
    assert "display_name" in missing_fields
