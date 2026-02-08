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
