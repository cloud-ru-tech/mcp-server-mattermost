"""Tests for package init and CLI entry point."""

import sys
from unittest.mock import MagicMock, patch


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

    def test_main_with_http_flag(self) -> None:
        """Test that --http flag uses http transport."""
        with (
            patch.object(sys, "argv", ["mcp-server-mattermost", "--http"]),
            patch("mcp_server_mattermost.server.mcp") as mock_mcp,
        ):
            mock_mcp.run = MagicMock()
            from mcp_server_mattermost import main

            main()

            mock_mcp.run.assert_called_once_with(
                transport="http",
                host="127.0.0.1",
                port=8000,
                uvicorn_config={"ws": "wsproto"},
            )

    def test_main_with_custom_port(self) -> None:
        """Test that --port flag is respected."""
        with (
            patch.object(sys, "argv", ["mcp-server-mattermost", "--http", "--port", "9000"]),
            patch("mcp_server_mattermost.server.mcp") as mock_mcp,
        ):
            mock_mcp.run = MagicMock()
            from mcp_server_mattermost import main

            main()

            mock_mcp.run.assert_called_once_with(
                transport="http",
                host="127.0.0.1",
                port=9000,
                uvicorn_config={"ws": "wsproto"},
            )

    def test_main_with_custom_host(self) -> None:
        """Test that --host flag is respected."""
        with (
            patch.object(sys, "argv", ["mcp-server-mattermost", "--http", "--host", "0.0.0.0"]),  # noqa: S104
            patch("mcp_server_mattermost.server.mcp") as mock_mcp,
        ):
            mock_mcp.run = MagicMock()
            from mcp_server_mattermost import main

            main()

            mock_mcp.run.assert_called_once_with(
                transport="http",
                host="0.0.0.0",  # noqa: S104
                port=8000,
                uvicorn_config={"ws": "wsproto"},
            )


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
