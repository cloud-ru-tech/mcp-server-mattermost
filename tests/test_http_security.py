"""Tests for HTTP transport-security posture and advisories."""

import fastmcp
import pytest
from fastmcp.server.http import _is_loopback_host as fastmcp_is_loopback_host

from mcp_server_mattermost.config import AuthMode, HostOriginProtection, Settings
from mcp_server_mattermost.http_security import (
    apply_http_security_settings,
    effective_protection,
    host_origin_posture,
    inert_allowlist_warning,
    is_loopback_host,
    unauthenticated_http_warning,
)


@pytest.fixture(autouse=True)
def _isolate_fastmcp_settings(monkeypatch):
    """Keep writes to FastMCP's global settings from leaking between tests."""
    monkeypatch.setattr(fastmcp.settings, "http_host_origin_protection", False)
    monkeypatch.setattr(fastmcp.settings, "http_allowed_hosts", None)
    monkeypatch.setattr(fastmcp.settings, "http_allowed_origins", None)


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


@pytest.mark.parametrize(
    "host",
    ["127.0.0.1", "[::1]", "LocalHost", "127.0.0.1 ", "127.0.0.1:8000", "[::1]:8000", "0.0.0.0", "example.com", ""],  # noqa: S104
)
def test_is_loopback_matches_fastmcp(host: str) -> None:
    """Our classification drives the warnings; FastMCP's drives the actual guard.

    They must agree, or the warnings describe a posture the server is not applying.
    """
    assert is_loopback_host(host) is fastmcp_is_loopback_host(host)


class TestUnauthenticatedWarning:
    def test_stdio_static_token_no_warning(self) -> None:
        assert unauthenticated_http_warning(_settings(), transport="stdio", host="0.0.0.0") is None  # noqa: S104

    def test_http_client_token_no_warning(self) -> None:
        settings = _settings(auth_mode=AuthMode.CLIENT_TOKEN, token=None)
        assert unauthenticated_http_warning(settings, transport="http", host="0.0.0.0") is None  # noqa: S104

    @pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost"])
    def test_http_static_token_loopback_warns(self, host: str) -> None:
        warning = unauthenticated_http_warning(_settings(), transport="http", host=host)
        assert warning is not None
        assert "loopback" in warning.lower()

    def test_http_static_token_public_warns(self) -> None:
        warning = unauthenticated_http_warning(_settings(), transport="http", host="0.0.0.0")  # noqa: S104
        assert warning is not None
        assert "0.0.0.0" in warning  # noqa: S104
        assert "client_token" in warning

    def test_guard_does_not_reference_removed_env_var(self) -> None:
        for host in ("127.0.0.1", "0.0.0.0"):  # noqa: S104
            warning = unauthenticated_http_warning(_settings(), transport="http", host=host)
            assert warning is not None
            assert "ALLOW_UNAUTHENTICATED_HTTP" not in warning

    def test_messages_never_leak_secrets(self) -> None:
        for host in ("127.0.0.1", "0.0.0.0"):  # noqa: S104
            warning = unauthenticated_http_warning(_settings(), transport="http", host=host)
            assert warning is not None
            assert "SENTINEL-TOKEN" not in warning
            assert "Authorization" not in warning


class TestApplyHttpSecuritySettings:
    def test_unset_leaves_fastmcp_settings_alone(self) -> None:
        """An operator's own FASTMCP_HTTP_HOST_ORIGIN_PROTECTION must survive."""
        fastmcp.settings.http_host_origin_protection = True
        apply_http_security_settings(_settings())
        assert fastmcp.settings.http_host_origin_protection is True
        assert effective_protection() is HostOriginProtection.STRICT

    @pytest.mark.parametrize(
        ("configured", "expected"),
        [("off", False), ("auto", "auto"), ("strict", True)],
    )
    def test_configured_level_is_written(self, configured: str, expected: object) -> None:
        apply_http_security_settings(_settings(http_host_origin_protection=configured))
        assert fastmcp.settings.http_host_origin_protection == expected

    def test_off_overrides_fastmcp_env_var(self) -> None:
        fastmcp.settings.http_host_origin_protection = "auto"
        apply_http_security_settings(_settings(http_host_origin_protection="off"))
        assert fastmcp.settings.http_host_origin_protection is False

    def test_allowlists_are_written(self) -> None:
        settings = _settings(
            http_allowed_hosts=["a.example"],
            http_allowed_origins=["https://a.example"],
        )
        apply_http_security_settings(settings)
        assert fastmcp.settings.http_allowed_hosts == ["a.example"]
        assert fastmcp.settings.http_allowed_origins == ["https://a.example"]

    def test_absent_allowlists_leave_fastmcp_settings_alone(self) -> None:
        fastmcp.settings.http_allowed_hosts = ["preset.example"]
        apply_http_security_settings(_settings())
        assert fastmcp.settings.http_allowed_hosts == ["preset.example"]


class TestPosture:
    def test_off_by_default(self) -> None:
        posture = host_origin_posture(_settings(), host="127.0.0.1")
        assert "OFF" in posture
        assert "MATTERMOST_HTTP_HOST_ORIGIN_PROTECTION" in posture

    def test_off_announces_the_coming_default_change(self) -> None:
        """Operators who read neither the changelog nor the tracker still get warned in time."""
        assert "1.0.0" in host_origin_posture(_settings(), host="127.0.0.1")

    def test_loopback_bind_reports_unconditional_validation(self) -> None:
        settings = _settings(http_host_origin_protection="auto")
        apply_http_security_settings(settings)
        posture = host_origin_posture(settings, host="127.0.0.1")
        assert "mode=auto" in posture
        assert "every connection" in posture
        assert "MATTERMOST_HTTP_ALLOWED_HOSTS" in posture

    def test_non_loopback_bind_reports_per_arrival_rule(self) -> None:
        settings = _settings(http_host_origin_protection="auto")
        apply_http_security_settings(settings)
        posture = host_origin_posture(settings, host="0.0.0.0")  # noqa: S104
        assert "mode=auto" in posture
        assert "arrives on" in posture

    def test_strict_reported(self) -> None:
        settings = _settings(http_host_origin_protection="strict")
        apply_http_security_settings(settings)
        assert "mode=strict" in host_origin_posture(settings, host="0.0.0.0")  # noqa: S104

    def test_absent_allowlist_is_distinguishable_from_empty(self) -> None:
        """``None`` and ``[]`` mean opposite things to FastMCP, so they must not print alike."""
        settings = _settings(http_host_origin_protection="auto")
        apply_http_security_settings(settings)
        assert "allowed_hosts=None" in host_origin_posture(settings, host="0.0.0.0")  # noqa: S104

    def test_configured_allowlists_reported(self) -> None:
        settings = _settings(
            http_host_origin_protection="auto",
            http_allowed_hosts=["a.example", "b.example"],
            http_allowed_origins=["https://a.example"],
        )
        apply_http_security_settings(settings)
        posture = host_origin_posture(settings, host="0.0.0.0")  # noqa: S104
        assert "allowed_hosts=['a.example', 'b.example']" in posture
        assert "allowed_origins=['https://a.example']" in posture

    def test_never_leaks_secrets(self) -> None:
        posture = host_origin_posture(_settings(), host="127.0.0.1")
        assert "SENTINEL-TOKEN" not in posture
        assert "Authorization" not in posture


class TestInertAllowlistWarning:
    def test_warns_when_allowlist_set_but_protection_off(self) -> None:
        settings = _settings(http_allowed_hosts=["a.example"])
        apply_http_security_settings(settings)
        warning = inert_allowlist_warning(settings)
        assert warning is not None
        assert "no effect" in warning

    def test_silent_when_protection_enabled(self) -> None:
        settings = _settings(http_host_origin_protection="auto", http_allowed_hosts=["a.example"])
        apply_http_security_settings(settings)
        assert inert_allowlist_warning(settings) is None

    def test_silent_without_allowlists(self) -> None:
        assert inert_allowlist_warning(_settings()) is None
