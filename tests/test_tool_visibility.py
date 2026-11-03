"""Tests for MATTERMOST_ALLOWED_TOOLS / MATTERMOST_DENIED_TOOLS visibility filtering."""

import pytest


def _settings(monkeypatch: pytest.MonkeyPatch, **kwargs: str | None):
    monkeypatch.setenv("MATTERMOST_URL", "https://example.invalid")
    monkeypatch.setenv("MATTERMOST_TOKEN", "t")
    from mcp_server_mattermost.config import Settings

    return Settings(**kwargs)


def _transforms(monkeypatch: pytest.MonkeyPatch, **kwargs: str | None):
    settings = _settings(monkeypatch, **kwargs)  # env must be set before server import
    from mcp_server_mattermost.server import tool_visibility_transforms

    return tool_visibility_transforms(settings)


def test_no_lists_no_transforms(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _transforms(monkeypatch) == []


def test_denylist_single_transform(monkeypatch: pytest.MonkeyPatch) -> None:
    transforms = _transforms(monkeypatch, denied_tools="delete_post, delete_channel")
    assert len(transforms) == 1
    assert transforms[0]._enabled is False
    assert transforms[0].names == {"delete_post", "delete_channel"}


def test_allowlist_disables_all_then_enables_named(monkeypatch: pytest.MonkeyPatch) -> None:
    transforms = _transforms(monkeypatch, allowed_tools="get_channel_messages, save_message_draft")
    assert len(transforms) == 2
    assert transforms[0]._enabled is False  # match_all disable
    assert transforms[1]._enabled is True
    assert transforms[1].names == {"get_channel_messages", "save_message_draft"}


def test_both_lists_deny_applied_last(monkeypatch: pytest.MonkeyPatch) -> None:
    """Denylist wins: its transform runs after the allowlist re-enables."""
    transforms = _transforms(monkeypatch, allowed_tools="a,delete_post", denied_tools="delete_post")
    assert len(transforms) == 3
    last = transforms[-1]
    assert last.names == {"delete_post"}
    assert last._enabled is False


def test_whitespace_and_empty_entries_tolerated(monkeypatch: pytest.MonkeyPatch) -> None:
    transforms = _transforms(monkeypatch, allowed_tools=" a , ,b ,, ")
    enabled = transforms[1]
    assert enabled.names == {"a", "b"}
