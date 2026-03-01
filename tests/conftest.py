"""Pytest configuration and shared fixtures."""

import os

import pytest


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
    """Set env vars with allow_http_client_tokens=True (no MATTERMOST_TOKEN required)."""
    from mcp_server_mattermost.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("MATTERMOST_URL", "http://mattermost.example.com")
    monkeypatch.setenv("MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS", "true")
    yield
    get_settings.cache_clear()
