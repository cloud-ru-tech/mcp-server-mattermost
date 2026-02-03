# tests/integration/test_channels.py
"""Integration tests for channel tools via MCP protocol."""

import time

import pytest

from tests.integration.utils import cleanup_channel, make_test_name, to_dict


class TestChannelHappyPath:
    """Basic successful channel operations through MCP protocol."""

    async def test_list_channels_includes_town_square(self, mcp_client, team):
        """list_channels: returns public channels including town-square."""
        result = await mcp_client.call_tool(
            "list_channels",
            {"team_id": team["id"]},
        )

        channels = to_dict(result)
        assert len(channels) >= 1, f"Expected at least 1 channel, got {len(channels)}"
        channel_names = [ch["name"] for ch in channels]
        assert "town-square" in channel_names, f"town-square not in {channel_names}"

    async def test_get_channel_by_id(self, mcp_client, test_channel):
        """get_channel: returns channel by ID."""
        result = await mcp_client.call_tool(
            "get_channel",
            {"channel_id": test_channel["id"]},
        )

        channel = to_dict(result)
        assert channel["id"] == test_channel["id"]
        assert channel["name"] == test_channel["name"]

    async def test_get_channel_by_name(self, mcp_client, team, test_channel):
        """get_channel_by_name: returns channel by name."""
        result = await mcp_client.call_tool(
            "get_channel_by_name",
            {"team_id": team["id"], "channel_name": test_channel["name"]},
        )

        channel = to_dict(result)
        assert channel["id"] == test_channel["id"]

    async def test_create_public_channel(self, mcp_client, team):
        """create_channel: creates public channel (type=O)."""
        name = make_test_name()
        channel_id = None

        try:
            result = await mcp_client.call_tool(
                "create_channel",
                {
                    "team_id": team["id"],
                    "name": name,
                    "display_name": f"Test {name}",
                    "channel_type": "O",
                },
            )

            channel = to_dict(result)
            channel_id = channel["id"]
            assert channel["name"] == name
            assert channel["type"] == "O"
        finally:
            if channel_id:
                await cleanup_channel(channel_id)

    async def test_create_private_channel(self, mcp_client, team):
        """create_channel: creates private channel (type=P)."""
        name = make_test_name()
        channel_id = None

        try:
            result = await mcp_client.call_tool(
                "create_channel",
                {
                    "team_id": team["id"],
                    "name": name,
                    "display_name": f"Private {name}",
                    "channel_type": "P",
                },
            )

            channel = to_dict(result)
            channel_id = channel["id"]
            assert channel["name"] == name
            assert channel["type"] == "P"
        finally:
            if channel_id:
                await cleanup_channel(channel_id)

    async def test_get_channel_members(self, mcp_client, test_channel, bot_user):
        """get_channel_members: returns members including creator."""
        result = await mcp_client.call_tool(
            "get_channel_members",
            {"channel_id": test_channel["id"]},
        )

        members = to_dict(result)
        assert len(members) >= 1
        member_ids = [m["user_id"] for m in members]
        assert bot_user["id"] in member_ids

    async def test_join_channel_idempotent(self, mcp_client, test_channel):
        """join_channel: idempotent (no error if already member)."""
        result = await mcp_client.call_tool(
            "join_channel",
            {"channel_id": test_channel["id"]},
        )

        member = to_dict(result)
        assert "channel_id" in member

    async def test_create_direct_channel(self, mcp_client, bot_user, team):
        """create_direct_channel: creates DM between two users."""
        result = await mcp_client.call_tool(
            "create_direct_channel",
            {
                "user_id_1": bot_user["id"],
                "user_id_2": bot_user["id"],
            },
        )

        channel = to_dict(result)
        assert channel["type"] == "D"

    async def test_create_direct_channel_idempotent(self, mcp_client, bot_user):
        """create_direct_channel: returns same channel if already exists."""
        result1 = await mcp_client.call_tool(
            "create_direct_channel",
            {"user_id_1": bot_user["id"], "user_id_2": bot_user["id"]},
        )

        result2 = await mcp_client.call_tool(
            "create_direct_channel",
            {"user_id_1": bot_user["id"], "user_id_2": bot_user["id"]},
        )

        assert to_dict(result1.data)["id"] == to_dict(result2.data)["id"]


class TestChannelNameValidation:
    """Channel name validation through MCP protocol."""

    @pytest.mark.parametrize(
        ("name", "expected_error"),
        [
            ("", r"validation|empty|required"),
            ("a", r"validation|2 char|too short"),
            ("a" * 65, r"validation|64|too long"),
            ("HasUpperCase", r"validation|lowercase"),
            ("_startsUnderscore", r"validation|underscore|start"),
            ("-startsHyphen", r"validation|hyphen|start"),
            ("has space", r"validation|space"),
            ("special!@#$%", r"validation|character"),
        ],
    )
    async def test_create_channel_invalid_name(self, mcp_client, team, name, expected_error):
        """create_channel: ValidationError for invalid channel name."""
        with pytest.raises(Exception, match=expected_error):
            await mcp_client.call_tool(
                "create_channel",
                {
                    "team_id": team["id"],
                    "name": name,
                    "display_name": "Test Display",
                    "channel_type": "O",
                },
            )

    async def test_create_channel_name_starts_with_digit(self, mcp_client, team):
        """create_channel: accepts name starting with digit."""
        name = f"1test{int(time.time() * 1000)}"
        result = await mcp_client.call_tool(
            "create_channel",
            {
                "team_id": team["id"],
                "name": name,
                "display_name": "Digit Start Test",
                "channel_type": "O",
            },
        )
        channel = to_dict(result)
        try:
            assert channel["name"] == name
        finally:
            await cleanup_channel(channel["id"])

    async def test_create_channel_name_max_length(self, mcp_client, team):
        """create_channel: accepts name at max length (64 chars)."""
        # make_test_name adds "-" + 13-digit timestamp, so prefix can be up to 50 chars
        name = make_test_name(prefix="a" * 50)  # 50 + 1 + 13 = 64 chars max
        result = await mcp_client.call_tool(
            "create_channel",
            {
                "team_id": team["id"],
                "name": name,
                "display_name": "Max Length Test",
                "channel_type": "O",
            },
        )
        channel = to_dict(result)
        try:
            assert len(channel["name"]) <= 64
        finally:
            await cleanup_channel(channel["id"])


class TestChannelDisplayNameValidation:
    """Channel display_name validation through MCP protocol."""

    @pytest.mark.parametrize(
        ("display_name", "expected_error"),
        [
            ("", r"validation|empty|required"),
            ("a" * 65, r"validation|64|too long"),
        ],
    )
    async def test_create_channel_invalid_display_name(self, mcp_client, team, display_name, expected_error):
        """create_channel: ValidationError for invalid display_name."""
        with pytest.raises(Exception, match=expected_error):
            await mcp_client.call_tool(
                "create_channel",
                {
                    "team_id": team["id"],
                    "name": make_test_name(),
                    "display_name": display_name,
                    "channel_type": "O",
                },
            )

    @pytest.mark.parametrize(
        "display_name",
        [
            "A",  # single char
            "Тест Unicode",  # Cyrillic
            "Test 🚀 Emoji",  # emoji
            "Test!@#$%^&*()",  # special chars
        ],
    )
    async def test_create_channel_valid_display_name(self, mcp_client, team, display_name):
        """create_channel: accepts various valid display_name formats."""
        name = make_test_name()
        result = await mcp_client.call_tool(
            "create_channel",
            {
                "team_id": team["id"],
                "name": name,
                "display_name": display_name,
                "channel_type": "O",
            },
        )
        channel = to_dict(result)
        try:
            assert channel["display_name"] == display_name
        finally:
            await cleanup_channel(channel["id"])


class TestChannelTypeValidation:
    """Channel type validation through MCP protocol."""

    @pytest.mark.parametrize(
        ("channel_type", "expected_error"),
        [
            ("X", r"validation|type|invalid"),
            ("public", r"validation|type"),
            ("o", r"validation|type|lowercase"),
        ],
    )
    async def test_create_channel_invalid_type(self, mcp_client, team, channel_type, expected_error):
        """create_channel: ValidationError for invalid channel type."""
        with pytest.raises(Exception, match=expected_error):
            await mcp_client.call_tool(
                "create_channel",
                {
                    "team_id": team["id"],
                    "name": make_test_name(),
                    "display_name": "Type Test",
                    "channel_type": channel_type,
                },
            )


class TestChannelPagination:
    """Channel listing pagination through MCP protocol."""

    async def test_list_channels_per_page_1(self, mcp_client, team):
        """list_channels: returns 1 item with per_page=1."""
        result = await mcp_client.call_tool(
            "list_channels",
            {"team_id": team["id"], "per_page": 1},
        )
        channels = to_dict(result)
        assert len(channels) == 1

    async def test_list_channels_page_beyond_data(self, mcp_client, team):
        """list_channels: returns empty array for page beyond data."""
        result = await mcp_client.call_tool(
            "list_channels",
            {"team_id": team["id"], "page": 9999},
        )
        channels = to_dict(result)
        assert channels == []

    @pytest.mark.parametrize(
        ("per_page", "expected_error"),
        [
            (0, r"validation|per_page|0|greater"),
            (201, r"validation|per_page|200|max"),
        ],
    )
    async def test_list_channels_invalid_per_page(self, mcp_client, team, per_page, expected_error):
        """list_channels: ValidationError for invalid per_page."""
        with pytest.raises(Exception, match=expected_error):
            await mcp_client.call_tool(
                "list_channels",
                {"team_id": team["id"], "per_page": per_page},
            )

    async def test_list_channels_negative_page(self, mcp_client, team):
        """list_channels: ValidationError for negative page."""
        with pytest.raises(Exception, match=r"validation|page|negative"):
            await mcp_client.call_tool(
                "list_channels",
                {"team_id": team["id"], "page": -1},
            )


class TestChannelPermissions:
    """Channel permission boundaries through MCP protocol."""

    async def test_get_channel_not_found(self, mcp_client):
        """get_channel: 404 for non-existent ID."""
        fake_id = "a" * 26
        with pytest.raises(Exception, match=r"404|not found"):
            await mcp_client.call_tool("get_channel", {"channel_id": fake_id})

    async def test_create_direct_channel_invalid_user(self, mcp_client, bot_user):
        """create_direct_channel: 404 for non-existent user ID."""
        fake_id = "a" * 26
        with pytest.raises(Exception, match=r"404|not found|invalid"):
            await mcp_client.call_tool(
                "create_direct_channel",
                {"user_id_1": bot_user["id"], "user_id_2": fake_id},
            )
