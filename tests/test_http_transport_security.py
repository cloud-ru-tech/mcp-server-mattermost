"""Behavioral tests for FastMCP Host/Origin (DNS-rebinding) protection."""

import pytest
from starlette.testclient import TestClient


@pytest.fixture
def guard_client(mock_settings):
    """TestClient over the HTTP app with auto protection and explicit allowlists."""
    from mcp_server_mattermost.server import mcp

    app = mcp.http_app(
        host_origin_protection="auto",
        allowed_hosts=["good.example"],
        allowed_origins=["https://good.example"],
    )
    return TestClient(app)


def test_allowed_host_passes(guard_client) -> None:
    response = guard_client.get("/health", headers={"Host": "good.example"})
    assert response.status_code == 200


def test_foreign_host_rejected(guard_client) -> None:
    response = guard_client.get("/health", headers={"Host": "evil.example"})
    assert response.status_code == 421


def test_foreign_origin_rejected(guard_client) -> None:
    response = guard_client.get(
        "/health",
        headers={"Host": "good.example", "Origin": "https://evil.example"},
    )
    assert response.status_code == 403


def test_missing_origin_passes(guard_client) -> None:
    # Non-browser MCP clients send no Origin; they must not be blocked.
    response = guard_client.get("/health", headers={"Host": "good.example"})
    assert response.status_code == 200


@pytest.fixture
def default_path_client(mock_settings):
    """TestClient over the HTTP app with auto protection and NO allowlist.

    This mirrors the shipping default: a loopback bind with no explicit
    allowed_hosts/allowed_origins, relying on FastMCP's "auto" mode to detect
    the loopback bind and validate Host against its built-in defaults
    (127.0.0.1, localhost, ::1).

    The TestClient base_url is overridden to a loopback address so the
    server's bound host is loopback, which is what triggers "auto"
    validation (the default base_url of http://testserver is non-loopback).
    """
    from mcp_server_mattermost.server import mcp

    app = mcp.http_app(host_origin_protection="auto")
    return TestClient(app, base_url="http://127.0.0.1")


def test_default_path_loopback_host_passes(default_path_client) -> None:
    response = default_path_client.get("/health", headers={"Host": "127.0.0.1"})
    assert response.status_code == 200


def test_default_path_foreign_host_rejected(default_path_client) -> None:
    response = default_path_client.get("/health", headers={"Host": "evil.example"})
    assert response.status_code == 421
