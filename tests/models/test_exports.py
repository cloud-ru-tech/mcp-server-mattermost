"""Tests for models module exports."""

from mcp_server_mattermost import models


def test_response_models_exported():
    """Test that all response models are exported."""
    # Base
    assert hasattr(models, "MattermostResponse")

    # Channel
    assert hasattr(models, "Channel")
    assert hasattr(models, "ChannelMember")

    # User
    assert hasattr(models, "User")
    assert hasattr(models, "UserStatus")

    # Post
    assert hasattr(models, "Post")
    assert hasattr(models, "PostList")
    assert hasattr(models, "Reaction")

    # Team
    assert hasattr(models, "Team")
    assert hasattr(models, "TeamMember")

    # File
    assert hasattr(models, "FileInfo")
    assert hasattr(models, "FileUploadResponse")
    assert hasattr(models, "FileLink")


def test_input_types_still_exported():
    """Test that existing input types are still exported."""
    assert hasattr(models, "ChannelId")
    assert hasattr(models, "UserId")
    assert hasattr(models, "TeamId")


def test_all_contains_new_models():
    """Test that __all__ includes new models."""
    assert "MattermostResponse" in models.__all__
    assert "Channel" in models.__all__
    assert "User" in models.__all__
    assert "Post" in models.__all__
