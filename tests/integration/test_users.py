"""Integration tests for user tools via MCP protocol."""

import pytest

from tests.integration.utils import to_dict


class TestUserHappyPath:
    """Basic successful user operations through MCP protocol."""

    async def test_get_me_returns_bot_user(self, mcp_client, bot_user):
        """get_me: returns bot user with expected fields."""
        result = await mcp_client.call_tool("get_me", {})

        user = to_dict(result)
        assert "id" in user, f"Response missing 'id': {user}"
        assert "username" in user, f"Response missing 'username': {user}"
        assert user["id"] == bot_user["id"]
        assert user["username"] == bot_user["username"]
        assert "is_bot" in user or user.get("username", "").endswith("-bot")

    async def test_get_user_by_id(self, mcp_client, bot_user):
        """get_user: returns user by valid ID."""
        result = await mcp_client.call_tool(
            "get_user",
            {"user_id": bot_user["id"]},
        )

        user = to_dict(result)
        assert user["id"] == bot_user["id"]

    async def test_get_user_by_username(self, mcp_client, bot_user):
        """get_user_by_username: returns user by username."""
        result = await mcp_client.call_tool(
            "get_user_by_username",
            {"username": bot_user["username"]},
        )

        user = to_dict(result)
        assert user["username"] == bot_user["username"]

    async def test_search_users_finds_bot(self, mcp_client, bot_user):
        """search_users: finds user by partial name."""
        search_term = bot_user["username"][:5]

        result = await mcp_client.call_tool(
            "search_users",
            {"term": search_term},
        )

        users = to_dict(result)
        assert any(u["id"] == bot_user["id"] for u in users)

    async def test_search_users_empty_for_nonexistent(self, mcp_client):
        """search_users: returns empty for non-matching term."""
        result = await mcp_client.call_tool(
            "search_users",
            {"term": "nonexistent-user-xyz-12345"},
        )

        users = to_dict(result)
        assert len(users) == 0

    async def test_get_user_status(self, mcp_client, bot_user):
        """get_user_status: returns status (online/away/offline/dnd)."""
        result = await mcp_client.call_tool(
            "get_user_status",
            {"user_id": bot_user["id"]},
        )

        status = to_dict(result)
        assert "status" in status
        assert status["status"] in ("online", "away", "offline", "dnd")


class TestUserValidation:
    """User input validation through MCP protocol."""

    @pytest.mark.parametrize(
        ("user_id", "expected_error"),
        [
            ("short", r"validation|26 char"),  # < 26 chars
            ("abc!@#$%^&*()123456789012345", r"validation|alphanumeric"),  # special chars
        ],
    )
    async def test_get_user_invalid_id(self, mcp_client, user_id, expected_error):
        """get_user: ValidationError for invalid ID format."""
        with pytest.raises(Exception, match=expected_error):
            await mcp_client.call_tool("get_user", {"user_id": user_id})

    async def test_get_user_not_found(self, mcp_client):
        """get_user: 404 for non-existent valid ID."""
        fake_id = "a" * 26
        with pytest.raises(Exception, match=r"404|not found"):
            await mcp_client.call_tool("get_user", {"user_id": fake_id})

    @pytest.mark.parametrize(
        ("username", "expected_error"),
        [
            ("", r"validation|empty"),
            ("1startsWithDigit", r"validation|digit"),
            ("has@symbol", r"validation|@"),
            ("_startsUnderscore", r"validation|underscore"),
            ("a" * 65, r"validation|64"),
        ],
    )
    async def test_get_user_by_username_invalid(self, mcp_client, username, expected_error):
        """get_user_by_username: ValidationError for invalid username."""
        with pytest.raises(Exception, match=expected_error):
            await mcp_client.call_tool("get_user_by_username", {"username": username})

    async def test_get_user_by_username_valid_special_chars(self, mcp_client):
        """get_user_by_username: accepts dots, underscores, hyphens in middle."""
        try:
            await mcp_client.call_tool("get_user_by_username", {"username": "valid.user-name_test"})
        except Exception as e:  # noqa: BLE001
            assert "validation" not in str(e).lower()  # noqa: PT017

    @pytest.mark.parametrize(
        ("term", "expected_error"),
        [
            ("", r"validation|empty"),
            ("a" * 257, r"validation|256"),
        ],
    )
    async def test_search_users_invalid_term(self, mcp_client, term, expected_error):
        """search_users: ValidationError for invalid search term."""
        with pytest.raises(Exception, match=expected_error):
            await mcp_client.call_tool("search_users", {"term": term})

    async def test_search_users_unicode(self, mcp_client):
        """search_users: accepts Unicode search term."""
        result = await mcp_client.call_tool("search_users", {"term": "тест"})
        assert result is not None
