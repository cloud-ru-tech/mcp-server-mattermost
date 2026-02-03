"""Tests for bookmark response models."""

import pytest

from mcp_server_mattermost.models.bookmark import ChannelBookmark


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


def test_bookmark_parses_file_type():
    """Test ChannelBookmark with file type."""
    data = {
        "id": "bm123",
        "create_at": 1706400000000,
        "update_at": 1706400000000,
        "delete_at": 0,
        "channel_id": "ch456",
        "owner_id": "user789",
        "file_id": "file123",
        "display_name": "Important Document",
        "sort_order": 2,
        "type": "file",
        "file_info": {"id": "file123", "name": "doc.pdf"},
    }

    bookmark = ChannelBookmark(**data)
    assert bookmark.file_id == "file123"
    assert bookmark.file_info["id"] == "file123"


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


def test_bookmark_requires_all_required_fields():
    """Test that missing required fields raise ValidationError."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        ChannelBookmark(id="bm123")  # Missing other required fields

    errors = exc_info.value.errors()
    missing_fields = {e["loc"][0] for e in errors if e["type"] == "missing"}

    # All these fields are required
    assert "create_at" in missing_fields
    assert "channel_id" in missing_fields
    assert "display_name" in missing_fields
