"""Tests for Pydantic models and validators."""

import pytest
from pydantic import BaseModel, ValidationError


class TestMattermostIdValidation:
    """Tests for Mattermost ID validation."""

    def test_valid_26_char_alphanumeric_id(self):
        """Valid 26-character alphanumeric ID should pass validation."""
        from mcp_server_mattermost.models.common import MattermostId

        class TestModel(BaseModel):
            id: MattermostId

        # Valid ID: 26 alphanumeric characters
        model = TestModel(id="abcdefghijklmnopqrstuvwxyz")
        assert model.id == "abcdefghijklmnopqrstuvwxyz"

    def test_valid_mixed_case_id(self):
        """Mixed case alphanumeric ID should pass validation."""
        from mcp_server_mattermost.models.common import MattermostId

        class TestModel(BaseModel):
            id: MattermostId

        model = TestModel(id="AbCdEfGhIjKlMnOpQrStUvWxYz")
        assert model.id == "AbCdEfGhIjKlMnOpQrStUvWxYz"

    def test_valid_numeric_id(self):
        """Numeric-only 26-char ID should pass validation."""
        from mcp_server_mattermost.models.common import MattermostId

        class TestModel(BaseModel):
            id: MattermostId

        model = TestModel(id="12345678901234567890123456")
        assert model.id == "12345678901234567890123456"

    def test_invalid_too_short(self):
        """ID shorter than 26 characters should fail validation."""
        from mcp_server_mattermost.models.common import MattermostId

        class TestModel(BaseModel):
            id: MattermostId

        with pytest.raises(ValidationError) as exc_info:
            TestModel(id="abc123")
        assert "Invalid Mattermost ID format" in str(exc_info.value)

    def test_invalid_too_long(self):
        """ID longer than 26 characters should fail validation."""
        from mcp_server_mattermost.models.common import MattermostId

        class TestModel(BaseModel):
            id: MattermostId

        with pytest.raises(ValidationError) as exc_info:
            TestModel(id="abcdefghijklmnopqrstuvwxyz123")
        assert "Invalid Mattermost ID format" in str(exc_info.value)

    def test_invalid_special_characters(self):
        """ID with special characters should fail validation."""
        from mcp_server_mattermost.models.common import MattermostId

        class TestModel(BaseModel):
            id: MattermostId

        with pytest.raises(ValidationError) as exc_info:
            TestModel(id="abcdefghijklmnopqrstuv-xyz")
        assert "Invalid Mattermost ID format" in str(exc_info.value)

    def test_invalid_spaces(self):
        """ID with spaces should fail validation."""
        from mcp_server_mattermost.models.common import MattermostId

        class TestModel(BaseModel):
            id: MattermostId

        with pytest.raises(ValidationError) as exc_info:
            TestModel(id="abcdefghijklmnopqrstuv xyz")
        assert "Invalid Mattermost ID format" in str(exc_info.value)

    def test_invalid_empty_string(self):
        """Empty string should fail validation."""
        from mcp_server_mattermost.models.common import MattermostId

        class TestModel(BaseModel):
            id: MattermostId

        with pytest.raises(ValidationError) as exc_info:
            TestModel(id="")
        assert "Invalid Mattermost ID format" in str(exc_info.value)


class TestSemanticIdTypes:
    """Tests for semantic ID type aliases."""

    def test_channel_id_validates(self):
        """ChannelId should validate as MattermostId."""
        from mcp_server_mattermost.models.common import ChannelId

        class TestModel(BaseModel):
            channel_id: ChannelId

        model = TestModel(channel_id="abcdefghijklmnopqrstuvwxyz")
        assert model.channel_id == "abcdefghijklmnopqrstuvwxyz"

    def test_channel_id_rejects_invalid(self):
        """ChannelId should reject invalid IDs."""
        from mcp_server_mattermost.models.common import ChannelId

        class TestModel(BaseModel):
            channel_id: ChannelId

        with pytest.raises(ValidationError):
            TestModel(channel_id="invalid")

    def test_user_id_validates(self):
        """UserId should validate as MattermostId."""
        from mcp_server_mattermost.models.common import UserId

        class TestModel(BaseModel):
            user_id: UserId

        model = TestModel(user_id="12345678901234567890123456")
        assert model.user_id == "12345678901234567890123456"

    def test_team_id_validates(self):
        """TeamId should validate as MattermostId."""
        from mcp_server_mattermost.models.common import TeamId

        class TestModel(BaseModel):
            team_id: TeamId

        model = TestModel(team_id="AbCdEfGhIjKlMnOpQrStUvWxYz")
        assert model.team_id == "AbCdEfGhIjKlMnOpQrStUvWxYz"

    def test_post_id_validates(self):
        """PostId should validate as MattermostId."""
        from mcp_server_mattermost.models.common import PostId

        class TestModel(BaseModel):
            post_id: PostId

        model = TestModel(post_id="aaaaaaaaaaaaaaaaaaaaaaaa11")
        assert model.post_id == "aaaaaaaaaaaaaaaaaaaaaaaa11"

    def test_file_id_validates(self):
        """FileId should validate as MattermostId."""
        from mcp_server_mattermost.models.common import FileId

        class TestModel(BaseModel):
            file_id: FileId

        model = TestModel(file_id="ZZZZZZZZZZZZZZZZZZZZZZZZ99")
        assert model.file_id == "ZZZZZZZZZZZZZZZZZZZZZZZZ99"


class TestBookmarkIdValidation:
    """Tests for BookmarkId validation."""

    def test_valid_bookmark_id(self):
        """Valid 26-char alphanumeric ID should pass validation."""
        from mcp_server_mattermost.models.common import BookmarkId

        class TestModel(BaseModel):
            id: BookmarkId

        model = TestModel(id="abcdefghijklmnopqrstuvwxyz")
        assert model.id == "abcdefghijklmnopqrstuvwxyz"

    def test_invalid_bookmark_id(self):
        """Invalid ID should fail validation."""
        from mcp_server_mattermost.models.common import BookmarkId

        class TestModel(BaseModel):
            id: BookmarkId

        with pytest.raises(ValidationError) as exc_info:
            TestModel(id="abc123")
        assert "Invalid Mattermost ID format" in str(exc_info.value)


class TestChannelType:
    """Tests for ChannelType validation."""

    def test_public_channel_type(self):
        """'O' (public) should be valid channel type."""
        from mcp_server_mattermost.models.common import ChannelType

        class TestModel(BaseModel):
            type: ChannelType

        model = TestModel(type="O")
        assert model.type == "O"

    def test_private_channel_type(self):
        """'P' (private) should be valid channel type."""
        from mcp_server_mattermost.models.common import ChannelType

        class TestModel(BaseModel):
            type: ChannelType

        model = TestModel(type="P")
        assert model.type == "P"

    def test_direct_message_type(self):
        """'D' (direct message) should be valid channel type."""
        from mcp_server_mattermost.models.common import ChannelType

        class TestModel(BaseModel):
            type: ChannelType

        model = TestModel(type="D")
        assert model.type == "D"

    def test_group_message_type(self):
        """'G' (group message) should be valid channel type."""
        from mcp_server_mattermost.models.common import ChannelType

        class TestModel(BaseModel):
            type: ChannelType

        model = TestModel(type="G")
        assert model.type == "G"

    def test_invalid_channel_type(self):
        """Invalid channel type should fail validation."""
        from mcp_server_mattermost.models.common import ChannelType

        class TestModel(BaseModel):
            type: ChannelType

        with pytest.raises(ValidationError):
            TestModel(type="X")

    def test_lowercase_channel_type_invalid(self):
        """Lowercase channel type should fail validation."""
        from mcp_server_mattermost.models.common import ChannelType

        class TestModel(BaseModel):
            type: ChannelType

        with pytest.raises(ValidationError):
            TestModel(type="o")


class TestEmojiName:
    """Tests for EmojiName validation."""

    def test_simple_emoji_name(self):
        """Simple emoji name should be valid."""
        from mcp_server_mattermost.models.common import EmojiName

        class TestModel(BaseModel):
            emoji: EmojiName

        model = TestModel(emoji="thumbsup")
        assert model.emoji == "thumbsup"

    def test_emoji_with_underscore(self):
        """Emoji name with underscore should be valid."""
        from mcp_server_mattermost.models.common import EmojiName

        class TestModel(BaseModel):
            emoji: EmojiName

        model = TestModel(emoji="thumbs_up")
        assert model.emoji == "thumbs_up"

    def test_emoji_with_numbers(self):
        """Emoji name with numbers should be valid."""
        from mcp_server_mattermost.models.common import EmojiName

        class TestModel(BaseModel):
            emoji: EmojiName

        model = TestModel(emoji="100")
        assert model.emoji == "100"

    def test_emoji_with_plus(self):
        """Emoji name with plus should be valid."""
        from mcp_server_mattermost.models.common import EmojiName

        class TestModel(BaseModel):
            emoji: EmojiName

        model = TestModel(emoji="+1")
        assert model.emoji == "+1"

    def test_emoji_with_minus(self):
        """Emoji name with minus should be valid."""
        from mcp_server_mattermost.models.common import EmojiName

        class TestModel(BaseModel):
            emoji: EmojiName

        model = TestModel(emoji="-1")
        assert model.emoji == "-1"

    def test_empty_emoji_invalid(self):
        """Empty emoji name should be invalid."""
        from mcp_server_mattermost.models.common import EmojiName

        class TestModel(BaseModel):
            emoji: EmojiName

        with pytest.raises(ValidationError):
            TestModel(emoji="")

    def test_emoji_with_colons_invalid(self):
        """Emoji name with colons should be invalid."""
        from mcp_server_mattermost.models.common import EmojiName

        class TestModel(BaseModel):
            emoji: EmojiName

        with pytest.raises(ValidationError):
            TestModel(emoji=":thumbsup:")

    def test_emoji_too_long_invalid(self):
        """Emoji name over 64 chars should be invalid."""
        from mcp_server_mattermost.models.common import EmojiName

        class TestModel(BaseModel):
            emoji: EmojiName

        with pytest.raises(ValidationError):
            TestModel(emoji="a" * 65)


class TestUsername:
    """Tests for Username validation."""

    def test_simple_username(self):
        """Simple username should be valid."""
        from mcp_server_mattermost.models.common import Username

        class TestModel(BaseModel):
            username: Username

        model = TestModel(username="john")
        assert model.username == "john"

    def test_username_with_numbers(self):
        """Username with numbers should be valid."""
        from mcp_server_mattermost.models.common import Username

        class TestModel(BaseModel):
            username: Username

        model = TestModel(username="john123")
        assert model.username == "john123"

    def test_username_with_dots(self):
        """Username with dots should be valid."""
        from mcp_server_mattermost.models.common import Username

        class TestModel(BaseModel):
            username: Username

        model = TestModel(username="john.doe")
        assert model.username == "john.doe"

    def test_username_with_underscore(self):
        """Username with underscore should be valid."""
        from mcp_server_mattermost.models.common import Username

        class TestModel(BaseModel):
            username: Username

        model = TestModel(username="john_doe")
        assert model.username == "john_doe"

    def test_username_with_hyphen(self):
        """Username with hyphen should be valid."""
        from mcp_server_mattermost.models.common import Username

        class TestModel(BaseModel):
            username: Username

        model = TestModel(username="john-doe")
        assert model.username == "john-doe"

    def test_empty_username_invalid(self):
        """Empty username should be invalid."""
        from mcp_server_mattermost.models.common import Username

        class TestModel(BaseModel):
            username: Username

        with pytest.raises(ValidationError):
            TestModel(username="")

    def test_username_starting_with_number_invalid(self):
        """Username starting with number should be invalid."""
        from mcp_server_mattermost.models.common import Username

        class TestModel(BaseModel):
            username: Username

        with pytest.raises(ValidationError):
            TestModel(username="123john")

    def test_username_too_long_invalid(self):
        """Username over 64 chars should be invalid."""
        from mcp_server_mattermost.models.common import Username

        class TestModel(BaseModel):
            username: Username

        with pytest.raises(ValidationError):
            TestModel(username="a" * 65)


class TestChannelName:
    """Tests for ChannelName validation."""

    def test_simple_channel_name(self):
        """Simple channel name should be valid."""
        from mcp_server_mattermost.models.common import ChannelName

        class TestModel(BaseModel):
            name: ChannelName

        model = TestModel(name="general")
        assert model.name == "general"

    def test_channel_name_with_numbers(self):
        """Channel name with numbers should be valid."""
        from mcp_server_mattermost.models.common import ChannelName

        class TestModel(BaseModel):
            name: ChannelName

        model = TestModel(name="team123")
        assert model.name == "team123"

    def test_channel_name_with_underscore(self):
        """Channel name with underscore should be valid."""
        from mcp_server_mattermost.models.common import ChannelName

        class TestModel(BaseModel):
            name: ChannelName

        model = TestModel(name="team_chat")
        assert model.name == "team_chat"

    def test_channel_name_with_hyphen(self):
        """Channel name with hyphen should be valid."""
        from mcp_server_mattermost.models.common import ChannelName

        class TestModel(BaseModel):
            name: ChannelName

        model = TestModel(name="team-chat")
        assert model.name == "team-chat"

    def test_channel_name_starting_with_number(self):
        """Channel name starting with number should be valid."""
        from mcp_server_mattermost.models.common import ChannelName

        class TestModel(BaseModel):
            name: ChannelName

        model = TestModel(name="123channel")
        assert model.name == "123channel"

    def test_single_char_channel_name_invalid(self):
        """Single character channel name should be invalid (min 2)."""
        from mcp_server_mattermost.models.common import ChannelName

        class TestModel(BaseModel):
            name: ChannelName

        with pytest.raises(ValidationError):
            TestModel(name="a")

    def test_empty_channel_name_invalid(self):
        """Empty channel name should be invalid."""
        from mcp_server_mattermost.models.common import ChannelName

        class TestModel(BaseModel):
            name: ChannelName

        with pytest.raises(ValidationError):
            TestModel(name="")

    def test_channel_name_with_spaces_invalid(self):
        """Channel name with spaces should be invalid."""
        from mcp_server_mattermost.models.common import ChannelName

        class TestModel(BaseModel):
            name: ChannelName

        with pytest.raises(ValidationError):
            TestModel(name="team chat")

    def test_channel_name_too_long_invalid(self):
        """Channel name over 64 chars should be invalid."""
        from mcp_server_mattermost.models.common import ChannelName

        class TestModel(BaseModel):
            name: ChannelName

        with pytest.raises(ValidationError):
            TestModel(name="a" * 65)

    def test_channel_name_uppercase_invalid(self):
        """Channel name with uppercase letters should be invalid."""
        from mcp_server_mattermost.models.common import ChannelName

        class TestModel(BaseModel):
            name: ChannelName

        with pytest.raises(ValidationError):
            TestModel(name="General")


class TestChannelBookmarkModel:
    """Tests for ChannelBookmark response model."""

    def test_required_fields(self):
        """All required fields must be present."""
        from mcp_server_mattermost.models import ChannelBookmark

        bookmark = ChannelBookmark(
            id="bm12345678901234567890123",
            create_at=1234567890,
            update_at=1234567890,
            delete_at=0,
            channel_id="ch12345678901234567890123",
            owner_id="us12345678901234567890123",
            file_id="",
            display_name="Test Bookmark",
            sort_order=0,
            type="link",
        )
        assert bookmark.id == "bm12345678901234567890123"
        assert bookmark.type == "link"

    def test_optional_fields_default_none(self):
        """Optional fields default to None."""
        from mcp_server_mattermost.models import ChannelBookmark

        bookmark = ChannelBookmark(
            id="bm12345678901234567890123",
            create_at=1234567890,
            update_at=1234567890,
            delete_at=0,
            channel_id="ch12345678901234567890123",
            owner_id="us12345678901234567890123",
            file_id="",
            display_name="Test",
            sort_order=0,
            type="link",
        )
        assert bookmark.link_url is None
        assert bookmark.image_url is None
        assert bookmark.emoji is None
        assert bookmark.file_info is None

    def test_bookmark_with_optional_fields(self):
        """Optional fields can be set."""
        from mcp_server_mattermost.models import ChannelBookmark

        bookmark = ChannelBookmark(
            id="bm12345678901234567890123",
            create_at=1234567890,
            update_at=1234567890,
            delete_at=0,
            channel_id="ch12345678901234567890123",
            owner_id="us12345678901234567890123",
            file_id="",
            display_name="Test",
            sort_order=0,
            type="link",
            link_url="https://example.com",
            emoji="bookmark",
        )
        assert bookmark.link_url == "https://example.com"
        assert bookmark.emoji == "bookmark"


class TestModelsExports:
    """Tests for models package exports."""

    def test_all_types_exported(self):
        """All types should be importable from models package."""
        from mcp_server_mattermost.models import (
            ChannelId,
            ChannelName,
            ChannelType,
            EmojiName,
            FileId,
            MattermostId,
            PostId,
            TeamId,
            UserId,
            Username,
            validate_mattermost_id,
        )

        # Just verify imports work
        assert MattermostId is not None
        assert ChannelId is not None
        assert UserId is not None
        assert TeamId is not None
        assert PostId is not None
        assert FileId is not None
        assert ChannelType is not None
        assert EmojiName is not None
        assert Username is not None
        assert ChannelName is not None
        assert validate_mattermost_id is not None

    def test_validate_mattermost_id_function_works(self):
        """validate_mattermost_id should work standalone."""
        from mcp_server_mattermost.models import validate_mattermost_id

        # Valid ID
        result = validate_mattermost_id("abcdefghijklmnopqrstuvwxyz")
        assert result == "abcdefghijklmnopqrstuvwxyz"

        # Invalid ID
        with pytest.raises(ValueError):
            validate_mattermost_id("invalid")
