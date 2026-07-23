"""Tests for HTTP transport-security guards."""

import pytest

from mcp_server_mattermost.config import AuthMode, Settings
from mcp_server_mattermost.http_security import (
    is_loopback_host,
    resolve_host_origin_kwargs,
    unauthenticated_http_warning,
)


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {"url": "https://mm.example.com", "token": "SENTINEL-TOKEN"}
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


@pytest.mark.parametrize("host", ["127.0.0.1", "127.0.0.2", "::1", "localhost"])
def test_is_loopback_true(host: str) -> None:
    assert is_loopback_host(host) is True


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "10.0.0.5", "mcp.example.com", ""])  # noqa: S104
def test_is_loopback_false(host: str) -> None:
    assert is_loopback_host(host) is False


def test_stdio_static_token_no_warning() -> None:
    assert unauthenticated_http_warning(_settings(), transport="stdio", host="0.0.0.0") is None  # noqa: S104


def test_http_client_token_no_warning() -> None:
    settings = _settings(auth_mode=AuthMode.CLIENT_TOKEN, token=None)
    assert unauthenticated_http_warning(settings, transport="http", host="0.0.0.0") is None  # noqa: S104


@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost"])
def test_http_static_token_loopback_warns(host: str) -> None:
    warning = unauthenticated_http_warning(_settings(), transport="http", host=host)
    assert warning is not None
    assert "loopback" in warning.lower()


def test_http_static_token_public_warns() -> None:
    """Non-loopback no longer refuses to start — it returns a louder warning instead."""
    warning = unauthenticated_http_warning(_settings(), transport="http", host="0.0.0.0")  # noqa: S104
    assert warning is not None
    assert "0.0.0.0" in warning  # noqa: S104
    assert "client_token" in warning


def test_guard_does_not_reference_removed_env_var() -> None:
    """The MATTERMOST_ALLOW_UNAUTHENTICATED_HTTP opt-in was removed; no message should mention it."""
    for host in ("127.0.0.1", "0.0.0.0"):  # noqa: S104
        warning = unauthenticated_http_warning(_settings(), transport="http", host=host)
        assert warning is not None
        assert "ALLOW_UNAUTHENTICATED_HTTP" not in warning


def test_messages_never_leak_secrets() -> None:
    for host in ("127.0.0.1", "0.0.0.0"):  # noqa: S104
        warning = unauthenticated_http_warning(_settings(), transport="http", host=host)
        assert warning is not None
        assert "SENTINEL-TOKEN" not in warning
        assert "Authorization" not in warning


def test_resolve_host_origin_kwargs_defaults() -> None:
    assert resolve_host_origin_kwargs(_settings()) == {
        "host_origin_protection": "auto",
        "allowed_hosts": None,
        "allowed_origins": None,
    }


def test_resolve_host_origin_kwargs_with_allowlists() -> None:
    settings = _settings(http_allowed_hosts=["a.example"], http_allowed_origins=["https://a.example"])
    kwargs = resolve_host_origin_kwargs(settings)
    assert kwargs["host_origin_protection"] == "auto"
    assert kwargs["allowed_hosts"] == ["a.example"]
    assert kwargs["allowed_origins"] == ["https://a.example"]
