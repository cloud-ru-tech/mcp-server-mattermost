"""Tests for main() environment variable support."""

from unittest.mock import MagicMock, patch

import pytest


# ruff: noqa: S104


@pytest.fixture
def mock_mcp_run():
    """Mock mcp.run() to capture calls."""
    with patch("mcp_server_mattermost.server.mcp") as mock:
        mock.run = MagicMock()
        yield mock


class TestMainEnvVars:
    """Tests for environment variable transport configuration."""

    def test_mcp_transport_http_env_var(self, mock_settings, mock_mcp_run, monkeypatch):
        """MCP_TRANSPORT=http triggers HTTP mode."""
        monkeypatch.setenv("MCP_TRANSPORT", "http")
        monkeypatch.setattr("sys.argv", ["mcp-server-mattermost"])

        from mcp_server_mattermost import main

        main()

        mock_mcp_run.run.assert_called_once()
        call_kwargs = mock_mcp_run.run.call_args[1]
        assert call_kwargs["transport"] == "http"

    def test_mcp_host_env_var(self, mock_settings, mock_mcp_run, monkeypatch):
        """MCP_HOST env var sets HTTP host."""
        monkeypatch.setenv("MCP_TRANSPORT", "http")
        monkeypatch.setenv("MCP_HOST", "0.0.0.0")
        monkeypatch.setattr("sys.argv", ["mcp-server-mattermost"])

        from mcp_server_mattermost import main

        main()

        call_kwargs = mock_mcp_run.run.call_args[1]
        assert call_kwargs["host"] == "0.0.0.0"

    def test_mcp_port_env_var(self, mock_settings, mock_mcp_run, monkeypatch):
        """MCP_PORT env var sets HTTP port."""
        monkeypatch.setenv("MCP_TRANSPORT", "http")
        monkeypatch.setenv("MCP_PORT", "9000")
        monkeypatch.setattr("sys.argv", ["mcp-server-mattermost"])

        from mcp_server_mattermost import main

        main()

        call_kwargs = mock_mcp_run.run.call_args[1]
        assert call_kwargs["port"] == 9000

    def test_cli_args_override_env_vars(self, mock_settings, mock_mcp_run, monkeypatch):
        """CLI arguments take precedence over env vars."""
        monkeypatch.setenv("MCP_PORT", "9000")
        monkeypatch.setattr("sys.argv", ["mcp-server-mattermost", "--http", "--port", "8080"])

        from mcp_server_mattermost import main

        main()

        call_kwargs = mock_mcp_run.run.call_args[1]
        assert call_kwargs["port"] == 8080

    def test_mcp_port_invalid_value(self, mock_settings, monkeypatch):
        """MCP_PORT with non-integer value shows helpful error."""
        monkeypatch.setenv("MCP_PORT", "abc")
        monkeypatch.setattr("sys.argv", ["mcp-server-mattermost"])

        from mcp_server_mattermost import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert "MCP_PORT must be an integer" in str(exc_info.value)
