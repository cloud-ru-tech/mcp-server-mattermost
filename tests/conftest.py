"""Pytest configuration and shared fixtures."""

import os

import pytest


@pytest.fixture
def file_bookmark_data():
    """Bookmark JSON from the shape of Mattermost's ToChannelBookmarkWithFileInfo.

    The list projection leaves file ownership and timestamps at their Go zero values.
    See server/public/model/channel_bookmark.go and server/public/model/file_info.go.
    """
    return {
        "id": "bk123456789012345678901234",
        "create_at": 1706400000000,
        "update_at": 1706400000000,
        "delete_at": 0,
        "channel_id": "ch123456789012345678901234",
        "owner_id": "us123456789012345678901234",
        "file_id": "fl123456789012345678901234",
        "display_name": "Important Document",
        "sort_order": 2,
        "type": "file",
        "file": {
            "id": "fl123456789012345678901234",
            "user_id": "",
            "channel_id": "",
            "create_at": 0,
            "update_at": 0,
            "delete_at": 0,
            "name": "doc.pdf",
            "extension": "pdf",
            "size": 1024,
            "mime_type": "application/pdf",
            "mini_preview": None,
            "remote_id": None,
            "archived": False,
        },
    }


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in list(os.environ.keys()):
        if key.startswith("MATTERMOST_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def mock_settings(monkeypatch):
    from mcp_server_mattermost.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("MATTERMOST_URL", "https://test.mattermost.com")
    monkeypatch.setenv("MATTERMOST_TOKEN", "test-token-12345")
    yield
    get_settings.cache_clear()


@pytest.fixture
def mock_settings_allow_http(monkeypatch):
    """Set env vars with auth_mode=client_token (no MATTERMOST_TOKEN required)."""
    from mcp_server_mattermost.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("MATTERMOST_URL", "http://mattermost.example.com")
    monkeypatch.setenv("MATTERMOST_AUTH_MODE", "client_token")
    yield
    get_settings.cache_clear()
