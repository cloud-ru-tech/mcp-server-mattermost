"""Tests for Host/Origin guard rejection logging.

These drive the real ``HostOriginGuardMiddleware`` rather than a stub, so a reworded FastMCP
guard response — which would silently stop the logging — fails here instead of in production.
"""

import fastmcp
import pytest
from starlette.testclient import TestClient

from mcp_server_mattermost.http_guard_log import GuardRejectionLoggingMiddleware
from mcp_server_mattermost.http_security import apply_http_security_settings


LOOPBACK = "127.0.0.1:8030"


@pytest.fixture(autouse=True)
def _isolate_fastmcp_settings(monkeypatch):
    monkeypatch.setattr(fastmcp.settings, "http_host_origin_protection", False)
    monkeypatch.setattr(fastmcp.settings, "http_allowed_hosts", None)
    monkeypatch.setattr(fastmcp.settings, "http_allowed_origins", None)


@pytest.fixture
def client(mock_settings):
    from mcp_server_mattermost.server import mcp

    app = mcp.http_app(host_origin_protection="auto")
    return TestClient(app, base_url=f"http://{LOOPBACK}")


def test_logger_is_outside_the_guard(client) -> None:
    """The guard is the outermost FastMCP middleware; ours has to sit outside it to see 421/403."""
    assert client.app.user_middleware[0].cls is GuardRejectionLoggingMiddleware


def test_rejected_host_is_logged(client, caplog) -> None:
    with caplog.at_level("WARNING"):
        assert client.get("/health", headers={"Host": "evil.example"}).status_code == 421

    logged = caplog.text
    assert "evil.example" in logged
    assert "MATTERMOST_HTTP_ALLOWED_HOSTS" in logged


def test_rejected_origin_is_logged(client, caplog) -> None:
    with caplog.at_level("WARNING"):
        response = client.get("/health", headers={"Origin": "https://evil.example"})
        assert response.status_code == 403

    logged = caplog.text
    assert "https://evil.example" in logged
    assert "MATTERMOST_HTTP_ALLOWED_ORIGINS" in logged


def test_accepted_request_logs_nothing(client, caplog) -> None:
    with caplog.at_level("WARNING"):
        assert client.get("/health").status_code == 200

    assert "Host/Origin protection" not in caplog.text


def test_response_body_is_unchanged(client) -> None:
    """Diagnostics go to the server log; the client learns nothing extra."""
    response = client.get("/health", headers={"Host": "evil.example"})
    assert response.text == "Misdirected Request"


class TestConfiguredPostureReachesHttpApp:
    """``mcp.http_app()`` with no keyword arguments must inherit the configured protection.

    This is the path used by ``fastmcp run``, a standalone ASGI server, and this app mounted
    into a parent application — none of which pass protection keyword arguments.
    """

    def test_unset_leaves_app_unprotected(self, mock_settings) -> None:
        from mcp_server_mattermost.server import mcp

        client = TestClient(mcp.http_app(), base_url=f"http://{LOOPBACK}")
        assert client.get("/health", headers={"Host": "mcp.example.com"}).status_code == 200

    def test_configured_protection_is_inherited(self, mock_settings, monkeypatch) -> None:
        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.server import mcp

        monkeypatch.setenv("MATTERMOST_HTTP_HOST_ORIGIN_PROTECTION", "auto")
        get_settings.cache_clear()
        apply_http_security_settings(get_settings())

        client = TestClient(mcp.http_app(), base_url=f"http://{LOOPBACK}")
        assert client.get("/health", headers={"Host": "mcp.example.com"}).status_code == 421

    def test_configured_allowlist_is_inherited(self, mock_settings, monkeypatch) -> None:
        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.server import mcp

        monkeypatch.setenv("MATTERMOST_HTTP_HOST_ORIGIN_PROTECTION", "auto")
        monkeypatch.setenv("MATTERMOST_HTTP_ALLOWED_HOSTS", "mcp.example.com")
        get_settings.cache_clear()
        apply_http_security_settings(get_settings())

        client = TestClient(mcp.http_app(), base_url=f"http://{LOOPBACK}")
        assert client.get("/health", headers={"Host": "mcp.example.com"}).status_code == 200
