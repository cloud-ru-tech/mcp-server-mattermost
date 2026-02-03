"""Tests for channel response models."""

from mcp_server_mattermost.models.channel import Channel, ChannelMember


def test_channel_parses_minimal_fields():
    """Test Channel with only required fields (all fields required per Go source)."""
    data = {
        "id": "ch123",
        "create_at": 1706400000000,
        "update_at": 1706400000000,
        "delete_at": 0,
        "team_id": "team456",
        "type": "O",
        "display_name": "General",
        "name": "general",
        "header": "",
        "purpose": "",
        "last_post_at": 0,
        "total_msg_count": 0,
        "creator_id": "",
    }

    channel = Channel(**data)
    assert channel.id == "ch123"
    assert channel.name == "general"
    assert channel.type == "O"
    assert channel.header == ""


def test_channel_parses_full_response():
    """Test Channel with all fields including extras."""
    data = {
        "id": "ch123",
        "create_at": 1706400000000,
        "update_at": 1706400000000,
        "delete_at": 0,
        "team_id": "team456",
        "type": "P",
        "display_name": "Private Channel",
        "name": "private-channel",
        "header": "Channel header",
        "purpose": "Channel purpose",
        "last_post_at": 1706400000000,
        "total_msg_count": 42,
        "creator_id": "user789",
        "extra_update_at": 1706400000000,  # Extra field
        "scheme_id": "scheme123",  # Extra field
    }

    channel = Channel(**data)
    assert channel.id == "ch123"
    assert channel.header == "Channel header"
    assert channel.total_msg_count == 42
    assert channel.__pydantic_extra__["extra_update_at"] == 1706400000000


def test_channel_member_parses():
    """Test ChannelMember model."""
    data = {
        "channel_id": "ch123",
        "user_id": "user456",
        "roles": "channel_user",
        "last_viewed_at": 1706400000000,
        "msg_count": 10,
        "mention_count": 2,
        "last_update_at": 1706400000000,
    }

    member = ChannelMember(**data)
    assert member.channel_id == "ch123"
    assert member.user_id == "user456"
    assert member.mention_count == 2


def test_channel_generates_json_schema():
    """Test that Channel generates proper JSON schema for outputSchema."""
    schema = Channel.model_json_schema()

    assert schema["type"] == "object"
    assert "id" in schema["properties"]
    assert "name" in schema["properties"]
    assert schema["properties"]["id"]["type"] == "string"
    assert "description" in schema["properties"]["id"]
