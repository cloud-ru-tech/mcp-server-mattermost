"""Tests for package init and CLI entry point."""

import sys
from unittest.mock import MagicMock, patch

import pytest


class TestMain:
    """Tests for main() entry point."""

    def test_main_exists(self) -> None:
        """Test that main function is exported."""
        from mcp_server_mattermost import main

        assert callable(main)

    def test_main_with_no_args_uses_stdio(self) -> None:
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
        """--http uses http transport with Host/Origin protection."""
        from mcp_server_mattermost.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("MATTERMOST_URL", "https://mm.example.com")
        monkeypatch.setenv("MATTERMOST_AUTH_MODE", "client_token")
        monkeypatch.setattr(sys, "argv", ["mcp-server-mattermost", "--http"])

        with patch("mcp_server_mattermost.server.mcp") as mock_mcp:
            mock_mcp.run = MagicMock()
            from mcp_server_mattermost import main

            main()

            mock_mcp.run.assert_called_once_with(
                transport="http",
                host="127.0.0.1",
                port=8000,
                uvicorn_config={"ws": "wsproto"},
                host_origin_protection="auto",
                allowed_hosts=None,
                allowed_origins=None,
            )
        get_settings.cache_clear()

    def test_main_http_allowlists_flow_to_run(self, monkeypatch) -> None:
        """Non-empty MATTERMOST_HTTP_ALLOWED_* env values reach mcp.run()."""
        from mcp_server_mattermost.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("MATTERMOST_URL", "https://mm.example.com")
        monkeypatch.setenv("MATTERMOST_AUTH_MODE", "client_token")
        monkeypatch.setenv("MATTERMOST_HTTP_ALLOWED_HOSTS", "good.example, other.example")
        monkeypatch.setenv("MATTERMOST_HTTP_ALLOWED_ORIGINS", '["https://good.example"]')
        monkeypatch.setattr(sys, "argv", ["mcp-server-mattermost", "--http"])

        with patch("mcp_server_mattermost.server.mcp") as mock_mcp:
            mock_mcp.run = MagicMock()
            from mcp_server_mattermost import main

            main()

            mock_mcp.run.assert_called_once_with(
                transport="http",
                host="127.0.0.1",
                port=8000,
                uvicorn_config={"ws": "wsproto"},
                host_origin_protection="auto",
                allowed_hosts=["good.example", "other.example"],
                allowed_origins=["https://good.example"],
            )
        get_settings.cache_clear()

    def test_main_with_custom_port(self, monkeypatch) -> None:
        """--port is respected on the http run call."""
        from mcp_server_mattermost.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("MATTERMOST_URL", "https://mm.example.com")
        monkeypatch.setenv("MATTERMOST_AUTH_MODE", "client_token")
        monkeypatch.setattr(sys, "argv", ["mcp-server-mattermost", "--http", "--port", "9000"])

        with patch("mcp_server_mattermost.server.mcp") as mock_mcp:
            mock_mcp.run = MagicMock()
            from mcp_server_mattermost import main

            main()

            assert mock_mcp.run.call_args[1]["port"] == 9000
        get_settings.cache_clear()

    def test_main_with_custom_host(self, monkeypatch) -> None:
        """--host flag is respected under the client_token auth mode."""
        from mcp_server_mattermost.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("MATTERMOST_URL", "https://mm.example.com")
        monkeypatch.setenv("MATTERMOST_AUTH_MODE", "client_token")
        monkeypatch.setattr(sys, "argv", ["mcp-server-mattermost", "--http", "--host", "0.0.0.0"])  # noqa: S104

        with patch("mcp_server_mattermost.server.mcp") as mock_mcp:
            mock_mcp.run = MagicMock()
            from mcp_server_mattermost import main

            main()

            mock_mcp.run.assert_called_once_with(
                transport="http",
                host="0.0.0.0",  # noqa: S104
                port=8000,
                uvicorn_config={"ws": "wsproto"},
                host_origin_protection="auto",
                allowed_hosts=None,
                allowed_origins=None,
            )
        get_settings.cache_clear()


class TestHttpTransportSecurity:
    """main() fail-closed guard for unauthenticated HTTP."""

    def test_http_static_token_no_optin_refuses(self, monkeypatch) -> None:
        from mcp_server_mattermost.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("MATTERMOST_URL", "https://mm.example.com")
        monkeypatch.setenv("MATTERMOST_TOKEN", "test-token")
        monkeypatch.setattr(sys, "argv", ["mcp-server-mattermost", "--http", "--host", "127.0.0.1"])

        from mcp_server_mattermost import main

        with pytest.raises(SystemExit) as exc:
            main()
        assert "MATTERMOST_ALLOW_UNAUTHENTICATED_HTTP" in str(exc.value)
        get_settings.cache_clear()

    def test_http_static_token_public_refuses_even_with_optin(self, monkeypatch) -> None:
        from mcp_server_mattermost.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("MATTERMOST_URL", "https://mm.example.com")
        monkeypatch.setenv("MATTERMOST_TOKEN", "test-token")
        monkeypatch.setenv("MATTERMOST_ALLOW_UNAUTHENTICATED_HTTP", "true")
        monkeypatch.setattr(sys, "argv", ["mcp-server-mattermost", "--http", "--host", "0.0.0.0"])  # noqa: S104

        from mcp_server_mattermost import main

        with pytest.raises(SystemExit):
            main()
        get_settings.cache_clear()

    def test_http_static_token_loopback_optin_runs_with_warning(self, monkeypatch) -> None:
        from mcp_server_mattermost.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("MATTERMOST_URL", "https://mm.example.com")
        monkeypatch.setenv("MATTERMOST_TOKEN", "test-token")
        monkeypatch.setenv("MATTERMOST_ALLOW_UNAUTHENTICATED_HTTP", "true")
        monkeypatch.setattr(sys, "argv", ["mcp-server-mattermost", "--http", "--host", "127.0.0.1"])

        with (
            patch("mcp_server_mattermost.server.mcp") as mock_mcp,
            patch("mcp_server_mattermost.logging.logger") as mock_logger,
            patch("mcp_server_mattermost.logging.setup_logging"),
        ):
            mock_mcp.run = MagicMock()
            from mcp_server_mattermost import main

            main()

            mock_mcp.run.assert_called_once_with(
                transport="http",
                host="127.0.0.1",
                port=8000,
                uvicorn_config={"ws": "wsproto"},
                host_origin_protection="auto",
                allowed_hosts=None,
                allowed_origins=None,
            )
            mock_logger.warning.assert_called_once()
        get_settings.cache_clear()

    def test_http_client_token_runs_without_optin(self, monkeypatch) -> None:
        from mcp_server_mattermost.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("MATTERMOST_URL", "https://mm.example.com")
        monkeypatch.setenv("MATTERMOST_AUTH_MODE", "client_token")
        monkeypatch.setattr(sys, "argv", ["mcp-server-mattermost", "--http", "--host", "0.0.0.0"])  # noqa: S104

        with patch("mcp_server_mattermost.server.mcp") as mock_mcp:
            mock_mcp.run = MagicMock()
            from mcp_server_mattermost import main

            main()

            mock_mcp.run.assert_called_once_with(
                transport="http",
                host="0.0.0.0",  # noqa: S104
                port=8000,
                uvicorn_config={"ws": "wsproto"},
                host_origin_protection="auto",
                allowed_hosts=None,
                allowed_origins=None,
            )
        get_settings.cache_clear()


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
