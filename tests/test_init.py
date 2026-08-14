"""Tests for package init and CLI entry point."""

import sys
from unittest.mock import MagicMock, patch

import pytest


HTTP_RUN_KWARGS = {
    "transport": "http",
    "port": 8000,
    "uvicorn_config": {"ws": "wsproto"},
}


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Drop the cached Settings around every test, including failing ones."""
    from mcp_server_mattermost.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestMain:
    """Tests for main() entry point."""

    def test_main_exists(self) -> None:
        """Test that main function is exported."""
        from mcp_server_mattermost import main

        assert callable(main)

    def test_main_with_no_args_uses_stdio(self, mock_settings) -> None:
        """Test that main() defaults to stdio transport."""
        with (
            patch.object(sys, "argv", ["mcp-server-mattermost"]),
            patch("mcp_server_mattermost.server.mcp") as mock_mcp,
        ):
            mock_mcp.run = MagicMock()
            from mcp_server_mattermost import main

            main()

            mock_mcp.run.assert_called_once_with(transport="stdio")

    def test_main_with_http_flag(self, monkeypatch) -> None:
        """--http uses http transport and leaves the security posture to FastMCP settings."""
        monkeypatch.setenv("MATTERMOST_URL", "https://mm.example.com")
        monkeypatch.setenv("MATTERMOST_AUTH_MODE", "client_token")
        monkeypatch.setattr(sys, "argv", ["mcp-server-mattermost", "--http"])

        with patch("mcp_server_mattermost.server.mcp") as mock_mcp:
            mock_mcp.run = MagicMock()
            from mcp_server_mattermost import main

            main()

            mock_mcp.run.assert_called_once_with(host="127.0.0.1", **HTTP_RUN_KWARGS)

    def test_main_does_not_pass_protection_kwargs(self, monkeypatch) -> None:
        """Protection reaches FastMCP through its settings, not through mcp.run().

        Passing it here would apply it only to the console entry point, and would silently
        override an operator's own FASTMCP_HTTP_HOST_ORIGIN_PROTECTION.
        """
        monkeypatch.setenv("MATTERMOST_URL", "https://mm.example.com")
        monkeypatch.setenv("MATTERMOST_AUTH_MODE", "client_token")
        monkeypatch.setenv("MATTERMOST_HTTP_ALLOWED_HOSTS", "good.example, other.example")
        monkeypatch.setenv("MATTERMOST_HTTP_ALLOWED_ORIGINS", '["https://good.example"]')
        monkeypatch.setattr(sys, "argv", ["mcp-server-mattermost", "--http"])

        with patch("mcp_server_mattermost.server.mcp") as mock_mcp:
            mock_mcp.run = MagicMock()
            from mcp_server_mattermost import main

            main()

            kwargs = mock_mcp.run.call_args[1]
            assert "host_origin_protection" not in kwargs
            assert "allowed_hosts" not in kwargs
            assert "allowed_origins" not in kwargs

    def test_main_with_custom_port(self, monkeypatch) -> None:
        """--port is respected on the http run call."""
        monkeypatch.setenv("MATTERMOST_URL", "https://mm.example.com")
        monkeypatch.setenv("MATTERMOST_AUTH_MODE", "client_token")
        monkeypatch.setattr(sys, "argv", ["mcp-server-mattermost", "--http", "--port", "9000"])

        with patch("mcp_server_mattermost.server.mcp") as mock_mcp:
            mock_mcp.run = MagicMock()
            from mcp_server_mattermost import main

            main()

            assert mock_mcp.run.call_args[1]["port"] == 9000

    def test_main_with_custom_host(self, monkeypatch) -> None:
        """--host flag is respected under the client_token auth mode."""
        monkeypatch.setenv("MATTERMOST_URL", "https://mm.example.com")
        monkeypatch.setenv("MATTERMOST_AUTH_MODE", "client_token")
        monkeypatch.setattr(sys, "argv", ["mcp-server-mattermost", "--http", "--host", "0.0.0.0"])  # noqa: S104

        with patch("mcp_server_mattermost.server.mcp") as mock_mcp:
            mock_mcp.run = MagicMock()
            from mcp_server_mattermost import main

            main()

            mock_mcp.run.assert_called_once_with(host="0.0.0.0", **HTTP_RUN_KWARGS)  # noqa: S104


class TestHttpTransportSecurity:
    """main() guard for unauthenticated HTTP: warn (never refuse), louder off-loopback."""

    @pytest.mark.parametrize("host", ["0.0.0.0", "127.0.0.1"])  # noqa: S104
    def test_http_static_token_runs_with_warning(self, monkeypatch, host: str) -> None:
        monkeypatch.setenv("MATTERMOST_URL", "https://mm.example.com")
        monkeypatch.setenv("MATTERMOST_TOKEN", "test-token")
        monkeypatch.setattr(sys, "argv", ["mcp-server-mattermost", "--http", "--host", host])

        with (
            patch("mcp_server_mattermost.server.mcp") as mock_mcp,
            patch("mcp_server_mattermost.logging.logger") as mock_logger,
            patch("mcp_server_mattermost.logging.setup_logging"),
        ):
            mock_mcp.run = MagicMock()
            from mcp_server_mattermost import main

            main()

            mock_mcp.run.assert_called_once_with(host=host, **HTTP_RUN_KWARGS)
            mock_logger.warning.assert_called_once()

    def test_http_client_token_runs_without_warning(self, monkeypatch) -> None:
        monkeypatch.setenv("MATTERMOST_URL", "https://mm.example.com")
        monkeypatch.setenv("MATTERMOST_AUTH_MODE", "client_token")
        monkeypatch.setattr(sys, "argv", ["mcp-server-mattermost", "--http", "--host", "0.0.0.0"])  # noqa: S104

        with (
            patch("mcp_server_mattermost.server.mcp") as mock_mcp,
            patch("mcp_server_mattermost.logging.logger") as mock_logger,
            patch("mcp_server_mattermost.logging.setup_logging"),
        ):
            mock_mcp.run = MagicMock()
            from mcp_server_mattermost import main

            main()

            mock_mcp.run.assert_called_once_with(host="0.0.0.0", **HTTP_RUN_KWARGS)  # noqa: S104
            mock_logger.warning.assert_not_called()

    def test_inert_allowlist_warns(self, monkeypatch) -> None:
        """An allowlist without protection enabled is dead configuration; say so."""
        monkeypatch.setenv("MATTERMOST_URL", "https://mm.example.com")
        monkeypatch.setenv("MATTERMOST_AUTH_MODE", "client_token")
        monkeypatch.setenv("MATTERMOST_HTTP_ALLOWED_HOSTS", "good.example")
        monkeypatch.setattr(sys, "argv", ["mcp-server-mattermost", "--http"])

        with (
            patch("mcp_server_mattermost.server.mcp") as mock_mcp,
            patch("mcp_server_mattermost.logging.logger") as mock_logger,
            patch("mcp_server_mattermost.logging.setup_logging"),
            patch("mcp_server_mattermost.http_security.effective_protection") as mock_effective,
        ):
            from mcp_server_mattermost.config import HostOriginProtection

            mock_effective.return_value = HostOriginProtection.OFF
            mock_mcp.run = MagicMock()
            from mcp_server_mattermost import main

            main()

            assert "no effect" in mock_logger.warning.call_args[0][0]


class TestVersion:
    """Tests for version string."""

    def test_version_is_string(self) -> None:
        """Test that __version__ is a valid string."""
        from mcp_server_mattermost import __version__

        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_exports(self) -> None:
        """Test that expected names are exported."""
        import mcp_server_mattermost

        assert hasattr(mcp_server_mattermost, "main")
        assert hasattr(mcp_server_mattermost, "__version__")
