"""Behavioral tests for FastMCP Host/Origin (DNS-rebinding) protection.

Protection is decided per connection, from the local address the connection arrived on
(``scope["server"][0]``) — not from the address the server is bound to. A server bound to
``0.0.0.0`` therefore validates a request reaching it through ``127.0.0.1`` and skips one
reaching it through a LAN address. These tests drive that distinction through the TestClient
``base_url``, which is what populates ``scope["server"]``.

The bind address cannot be exercised from here: ``mcp.http_app()`` never receives one. Only
``mcp.run()`` does, where FastMCP additionally pins an allowlist for a loopback bind. These tests
pass the protection level explicitly; that it is also picked up from configuration on every
entry point is asserted in ``tests/test_http_security.py``.
"""

import fastmcp
import pytest
from starlette.testclient import TestClient


LOOPBACK = "127.0.0.1:8020"
LAN = "192.0.2.10:8020"  # RFC 5737 documentation range


@pytest.fixture
def arrival_client(mock_settings, monkeypatch):
    """Return a factory for TestClients whose connections arrive on a chosen local address."""
    # http_app() falls back to the global FastMCP settings for unset allowlists, and those read
    # FASTMCP_HTTP_ALLOWED_* plus any .env file. Pin them so a developer's environment cannot
    # shift a request into a different row of the matrix below.
    monkeypatch.setattr(fastmcp.settings, "http_allowed_hosts", None)
    monkeypatch.setattr(fastmcp.settings, "http_allowed_origins", None)

    def _build(*, arrives_on, allowed_hosts=None, allowed_origins=None):
        from mcp_server_mattermost.server import mcp

        app = mcp.http_app(
            host_origin_protection="auto",
            allowed_hosts=allowed_hosts,
            allowed_origins=allowed_origins,
        )
        return TestClient(app, base_url=f"http://{arrives_on}")

    return _build


class TestLoopbackArrival:
    """A connection arriving on loopback is validated even with no allowlist configured."""

    @pytest.fixture
    def client(self, arrival_client):
        return arrival_client(arrives_on=LOOPBACK)

    def test_arrival_address_as_host_passes(self, client) -> None:
        assert client.get("/health").status_code == 200

    def test_foreign_host_rejected(self, client) -> None:
        assert client.get("/health", headers={"Host": "legacy-client.example"}).status_code == 421

    def test_foreign_origin_rejected(self, client) -> None:
        assert client.get("/health", headers={"Origin": "https://legacy-client.example"}).status_code == 403

    def test_loopback_origin_passes(self, client) -> None:
        # Any loopback Origin is accepted while Host is loopback, whatever the port.
        assert client.get("/health", headers={"Origin": f"http://{LOOPBACK}"}).status_code == 200


class TestNonLoopbackArrival:
    """A connection arriving on a LAN address is unvalidated until an allowlist exists.

    One process bound to 0.0.0.0 therefore accepts these headers on its LAN address while
    rejecting the very same headers on 127.0.0.1.
    """

    @pytest.fixture
    def client(self, arrival_client):
        return arrival_client(arrives_on=LAN)

    def test_foreign_host_passes(self, client) -> None:
        assert client.get("/health", headers={"Host": "legacy-client.example"}).status_code == 200

    def test_foreign_origin_passes(self, client) -> None:
        assert client.get("/health", headers={"Origin": "https://legacy-client.example"}).status_code == 200


class TestAllowedHostsOffLoopback:
    """MATTERMOST_HTTP_ALLOWED_HOSTS turns on both Host and Origin validation on every interface."""

    @pytest.fixture
    def client(self, arrival_client):
        return arrival_client(arrives_on=LAN, allowed_hosts=["good.example"])

    def test_listed_host_passes(self, client) -> None:
        assert client.get("/health", headers={"Host": "good.example"}).status_code == 200

    def test_unlisted_host_rejected(self, client) -> None:
        assert client.get("/health", headers={"Host": "evil.example"}).status_code == 421

    def test_origin_validated_too(self, client) -> None:
        response = client.get("/health", headers={"Host": "good.example", "Origin": "https://evil.example"})
        assert response.status_code == 403

    def test_arrival_address_as_host_passes(self, client) -> None:
        assert client.get("/health", headers={"Host": LAN}).status_code == 200


class TestAllowedOriginsOnlyOffLoopback:
    """MATTERMOST_HTTP_ALLOWED_ORIGINS alone validates Origin but leaves Host unvalidated."""

    @pytest.fixture
    def client(self, arrival_client):
        return arrival_client(arrives_on=LAN, allowed_origins=["https://good.example"])

    def test_host_still_unvalidated(self, client) -> None:
        # The asymmetry: an origins-only allowlist does not extend Host validation off-loopback.
        assert client.get("/health", headers={"Host": "evil.example"}).status_code == 200

    def test_listed_origin_passes(self, client) -> None:
        assert client.get("/health", headers={"Origin": "https://good.example"}).status_code == 200

    def test_unlisted_origin_rejected(self, client) -> None:
        assert client.get("/health", headers={"Origin": "https://evil.example"}).status_code == 403

    def test_missing_origin_passes(self, client) -> None:
        # Non-browser MCP clients send no Origin; they must not be blocked.
        assert client.get("/health").status_code == 200

    def test_same_origin_rejected_off_loopback(self, client) -> None:
        # Documented footgun: an origins-only allowlist drops the same-origin exemption here.
        assert client.get("/health", headers={"Origin": f"http://{LAN}"}).status_code == 403

    def test_same_origin_passes_on_loopback_arrival(self, arrival_client) -> None:
        # Contrast with the case above: a loopback arrival keeps the same-origin exemption.
        client = arrival_client(arrives_on=LOOPBACK, allowed_origins=["https://good.example"])
        assert client.get("/health", headers={"Origin": f"http://{LOOPBACK}"}).status_code == 200


class TestBothAllowlistsOffLoopback:
    """The configuration the docs recommend behind a reverse proxy: both allowlists declared."""

    @pytest.fixture
    def client(self, arrival_client):
        return arrival_client(
            arrives_on=LAN,
            allowed_hosts=["good.example"],
            allowed_origins=["https://good.example"],
        )

    def test_listed_host_and_origin_pass(self, client) -> None:
        response = client.get("/health", headers={"Host": "good.example", "Origin": "https://good.example"})
        assert response.status_code == 200

    def test_unlisted_host_rejected(self, client) -> None:
        assert client.get("/health", headers={"Host": "evil.example"}).status_code == 421

    def test_unlisted_origin_rejected(self, client) -> None:
        response = client.get("/health", headers={"Host": "good.example", "Origin": "https://evil.example"})
        assert response.status_code == 403
