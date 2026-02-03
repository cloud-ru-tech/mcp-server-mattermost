"""Tests for health check endpoint."""

import pytest
from starlette.testclient import TestClient


@pytest.fixture
def http_client(mock_settings):
    """Create test client for HTTP app."""
    from mcp_server_mattermost.server import mcp

    app = mcp.http_app()
    return TestClient(app)


def test_health_endpoint_returns_ok(http_client):
    """Health endpoint returns healthy status."""
    response = http_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "mcp-server-mattermost"}


def test_health_endpoint_content_type(http_client):
    """Health endpoint returns JSON content type."""
    response = http_client.get("/health")

    assert response.headers["content-type"] == "application/json"
