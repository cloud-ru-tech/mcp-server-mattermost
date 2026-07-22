"""Tests for HTTP transport-security guards."""

import pytest

from mcp_server_mattermost.config import AuthMode, Settings
from mcp_server_mattermost.exceptions import ConfigurationError
from mcp_server_mattermost.http_security import (
    enforce_unauthenticated_http_policy,
    is_loopback_host,
    resolve_host_origin_kwargs,
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


def test_stdio_static_token_allowed() -> None:
    assert enforce_unauthenticated_http_policy(_settings(), transport="stdio", host="0.0.0.0") is None  # noqa: S104


def test_http_client_token_allowed() -> None:
    settings = _settings(auth_mode=AuthMode.CLIENT_TOKEN, token=None)
    assert enforce_unauthenticated_http_policy(settings, transport="http", host="0.0.0.0") is None  # noqa: S104


def test_http_static_token_loopback_no_optin_refused() -> None:
    with pytest.raises(ConfigurationError) as exc:
        enforce_unauthenticated_http_policy(_settings(), transport="http", host="127.0.0.1")
    assert "MATTERMOST_ALLOW_UNAUTHENTICATED_HTTP" in str(exc.value)


def test_http_static_token_public_refused_even_with_optin() -> None:
    settings = _settings(allow_unauthenticated_http=True)
    with pytest.raises(ConfigurationError) as exc:
        enforce_unauthenticated_http_policy(settings, transport="http", host="0.0.0.0")  # noqa: S104
    assert "loopback" in str(exc.value).lower()


def test_http_static_token_loopback_optin_warns() -> None:
    settings = _settings(allow_unauthenticated_http=True)
    warning = enforce_unauthenticated_http_policy(settings, transport="http", host="127.0.0.1")
    assert warning is not None
    assert "loopback" in warning.lower()


def test_messages_never_leak_secrets() -> None:
    settings = _settings(allow_unauthenticated_http=True)
    warning = enforce_unauthenticated_http_policy(settings, transport="http", host="127.0.0.1")
    assert warning is not None
    assert "SENTINEL-TOKEN" not in warning
    assert "Authorization" not in warning
    for host in ("127.0.0.1", "0.0.0.0"):  # noqa: S104
        with pytest.raises(ConfigurationError) as exc:
            enforce_unauthenticated_http_policy(_settings(), transport="http", host=host)
        assert "SENTINEL-TOKEN" not in str(exc.value)
        assert "Authorization" not in str(exc.value)


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
