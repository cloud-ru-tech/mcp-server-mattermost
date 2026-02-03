"""Tests for Attachment models."""

import pytest
from pydantic import ValidationError


class TestAttachmentField:
    """Tests for AttachmentField model."""

    def test_field_with_string_value(self):
        """AttachmentField accepts string value."""
        from mcp_server_mattermost.models import AttachmentField

        field = AttachmentField(title="Status", value="Active")
        assert field.title == "Status"
        assert field.value == "Active"
        assert field.short is False

    def test_field_with_int_value(self):
        """AttachmentField accepts int value."""
        from mcp_server_mattermost.models import AttachmentField

        field = AttachmentField(title="Count", value=42, short=True)
        assert field.value == 42
        assert field.short is True

    def test_field_rejects_invalid_value_type(self):
        """AttachmentField rejects non-string/int values."""
        from mcp_server_mattermost.models import AttachmentField

        with pytest.raises(ValidationError):
            AttachmentField(title="Bad", value=["list"])


class TestAttachmentColor:
    """Tests for Attachment color validation."""

    def test_valid_color_keyword_good(self):
        """Color 'good' is valid."""
        from mcp_server_mattermost.models import Attachment

        attachment = Attachment(color="good", text="Success")
        assert attachment.color == "good"

    def test_valid_color_keyword_warning(self):
        """Color 'warning' is valid."""
        from mcp_server_mattermost.models import Attachment

        attachment = Attachment(color="warning")
        assert attachment.color == "warning"

    def test_valid_color_keyword_danger(self):
        """Color 'danger' is valid."""
        from mcp_server_mattermost.models import Attachment

        attachment = Attachment(color="danger")
        assert attachment.color == "danger"

    def test_valid_color_hex(self):
        """Hex color #RRGGBB is valid."""
        from mcp_server_mattermost.models import Attachment

        attachment = Attachment(color="#FF5733")
        assert attachment.color == "#FF5733"

    def test_valid_color_hex_lowercase(self):
        """Hex color lowercase is valid."""
        from mcp_server_mattermost.models import Attachment

        attachment = Attachment(color="#ff5733")
        assert attachment.color == "#ff5733"

    def test_invalid_color_rejects_random_string(self):
        """Invalid color string is rejected."""
        from mcp_server_mattermost.models import Attachment

        with pytest.raises(ValidationError) as exc_info:
            Attachment(color="red")
        assert "color" in str(exc_info.value).lower()

    def test_invalid_color_rejects_short_hex(self):
        """Short hex color #RGB is rejected."""
        from mcp_server_mattermost.models import Attachment

        with pytest.raises(ValidationError):
            Attachment(color="#F00")

    def test_invalid_color_rejects_hex_without_hash(self):
        """Hex color without # is rejected."""
        from mcp_server_mattermost.models import Attachment

        with pytest.raises(ValidationError):
            Attachment(color="FF5733")


class TestAttachmentCrossFieldValidation:
    """Tests for cross-field validation rules."""

    def test_author_link_requires_author_name(self):
        """author_link without author_name is rejected."""
        from mcp_server_mattermost.models import Attachment

        with pytest.raises(ValidationError) as exc_info:
            Attachment(author_link="https://example.com")
        assert "author_name" in str(exc_info.value).lower()

    def test_author_link_with_author_name_valid(self):
        """author_link with author_name is valid."""
        from mcp_server_mattermost.models import Attachment

        attachment = Attachment(
            author_name="John Doe",
            author_link="https://example.com/john",
        )
        assert attachment.author_link == "https://example.com/john"

    def test_title_link_requires_title(self):
        """title_link without title is rejected."""
        from mcp_server_mattermost.models import Attachment

        with pytest.raises(ValidationError) as exc_info:
            Attachment(title_link="https://example.com/task")
        assert "title" in str(exc_info.value).lower()

    def test_title_link_with_title_valid(self):
        """title_link with title is valid."""
        from mcp_server_mattermost.models import Attachment

        attachment = Attachment(
            title="Task #123",
            title_link="https://example.com/task/123",
        )
        assert attachment.title_link == "https://example.com/task/123"


class TestAttachmentSerialization:
    """Tests for Attachment serialization."""

    def test_to_api_dict_excludes_none(self):
        """to_api_dict() excludes None values."""
        from mcp_server_mattermost.models import Attachment

        attachment = Attachment(color="good", text="Hello")
        result = attachment.to_api_dict()

        assert result == {"color": "good", "text": "Hello"}
        assert "fallback" not in result
        assert "pretext" not in result

    def test_to_api_dict_includes_all_set_fields(self):
        """to_api_dict() includes all explicitly set fields."""
        from mcp_server_mattermost.models import Attachment, AttachmentField

        attachment = Attachment(
            color="warning",
            title="Alert",
            text="Something happened",
            fields=[AttachmentField(title="Priority", value="High", short=True)],
            footer="Bot",
            ts=1706400000,
        )
        result = attachment.to_api_dict()

        assert result["color"] == "warning"
        assert result["title"] == "Alert"
        assert result["text"] == "Something happened"
        assert result["fields"] == [{"title": "Priority", "value": "High", "short": True}]
        assert result["footer"] == "Bot"
        assert result["ts"] == 1706400000
