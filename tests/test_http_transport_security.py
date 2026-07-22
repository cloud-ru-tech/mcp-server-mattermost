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
