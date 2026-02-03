"""Tests for LoggingMiddleware."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestLoggingMiddlewareRedaction:
    """Test parameter redaction."""

    def test_redacts_message_content(self):
        """Parameter 'message' not included in logs."""
        from mcp_server_mattermost.middleware import LoggingMiddleware

        middleware = LoggingMiddleware()
        params = {
            "channel_id": "ch123",
            "message": "Secret message content",
        }

        redacted = middleware._redact_params(params)

        assert "channel_id" in redacted
        assert "message" not in redacted

    def test_logs_whitelisted_params(self):
        """Whitelisted params are logged."""
        from mcp_server_mattermost.middleware import LoggingMiddleware

        middleware = LoggingMiddleware()
        params = {
            "team_id": "team123",
            "channel_id": "ch123",
            "user_id": "user123",
            "page": 0,
            "per_page": 50,
        }

        redacted = middleware._redact_params(params)

        assert redacted == params

    def test_redacts_unknown_params(self):
        """Unknown parameters not logged (safe by default)."""
        from mcp_server_mattermost.middleware import LoggingMiddleware

        middleware = LoggingMiddleware()
        params = {
            "channel_id": "ch123",
            "custom_field": "unknown data",
            "another_field": 12345,
        }

        redacted = middleware._redact_params(params)

        assert redacted == {"channel_id": "ch123"}


class TestLoggingMiddlewareRequestId:
    """Test request ID handling."""

    def test_get_request_id_from_fastmcp_context(self):
        """Falls back to FastMCP request_id when no HTTP header."""
        from mcp_server_mattermost.middleware import LoggingMiddleware

        middleware = LoggingMiddleware()

        # Mock context without HTTP request
        mock_context = MagicMock()
        mock_context.fastmcp_context.request_id = "fastmcp-request-123"

        with patch(
            "mcp_server_mattermost.middleware.get_http_request",
            side_effect=Exception("No HTTP request"),
        ):
            request_id = middleware._get_request_id(mock_context)

        assert request_id == "fastmcp-request-123"

    def test_get_request_id_from_http_header(self):
        """Uses X-Request-ID header when available."""
        from mcp_server_mattermost.middleware import LoggingMiddleware

        middleware = LoggingMiddleware()

        mock_context = MagicMock()
        mock_context.fastmcp_context.request_id = "fastmcp-request-123"

        mock_request = MagicMock()
        mock_request.headers.get.return_value = "client-request-456"

        with patch(
            "mcp_server_mattermost.middleware.get_http_request",
            return_value=mock_request,
        ):
            request_id = middleware._get_request_id(mock_context)

        assert request_id == "client-request-456"

    def test_falls_back_when_header_empty(self):
        """Falls back to FastMCP request_id when header is empty."""
        from mcp_server_mattermost.middleware import LoggingMiddleware

        middleware = LoggingMiddleware()

        mock_context = MagicMock()
        mock_context.fastmcp_context.request_id = "fastmcp-request-123"

        mock_request = MagicMock()
        mock_request.headers.get.return_value = None

        with patch(
            "mcp_server_mattermost.middleware.get_http_request",
            return_value=mock_request,
        ):
            request_id = middleware._get_request_id(mock_context)

        assert request_id == "fastmcp-request-123"


class TestLoggingMiddlewareLogging:
    """Test logging behavior."""

    @pytest.mark.asyncio
    async def test_logs_tool_call_start(self):
        """Logs event=tool_call_start with tool name and params."""
        from mcp_server_mattermost.middleware import LoggingMiddleware

        middleware = LoggingMiddleware()

        mock_context = MagicMock()
        mock_context.fastmcp_context.request_id = "req-123"
        mock_context.message.name = "list_channels"
        mock_context.message.arguments = {"team_id": "team123"}

        mock_call_next = AsyncMock(return_value=MagicMock())

        with (
            patch("mcp_server_mattermost.middleware.get_http_request", side_effect=Exception("No HTTP")),
            patch("mcp_server_mattermost.middleware.logger") as mock_logger,
        ):
            await middleware.on_call_tool(mock_context, mock_call_next)

        # Verify logger.info was called with tool_call_start event
        info_calls = list(mock_logger.info.call_args_list)
        assert len(info_calls) >= 1

        # Check the first call (tool_call_start)
        first_call_kwargs = info_calls[0][1]["extra"]
        assert first_call_kwargs["event"] == "tool_call_start"
        assert first_call_kwargs["tool"] == "list_channels"
        assert first_call_kwargs["request_id"] == "req-123"
        assert first_call_kwargs["params"] == {"team_id": "team123"}

    @pytest.mark.asyncio
    async def test_logs_tool_call_success(self):
        """Logs event=tool_call_success with duration_ms."""
        from mcp_server_mattermost.middleware import LoggingMiddleware

        middleware = LoggingMiddleware()

        mock_context = MagicMock()
        mock_context.fastmcp_context.request_id = "req-123"
        mock_context.message.name = "list_channels"
        mock_context.message.arguments = {}

        mock_call_next = AsyncMock(return_value=MagicMock())

        with (
            patch("mcp_server_mattermost.middleware.get_http_request", side_effect=Exception("No HTTP")),
            patch("mcp_server_mattermost.middleware.logger") as mock_logger,
        ):
            await middleware.on_call_tool(mock_context, mock_call_next)

        # Verify logger.info was called twice (start + success)
        assert mock_logger.info.call_count == 2

        # Check the second call (tool_call_success)
        success_call_kwargs = mock_logger.info.call_args_list[1][1]["extra"]
        assert success_call_kwargs["event"] == "tool_call_success"
        assert success_call_kwargs["tool"] == "list_channels"
        assert "duration_ms" in success_call_kwargs

    @pytest.mark.asyncio
    async def test_logs_tool_call_error(self):
        """Logs event=tool_call_error with error_type and message."""
        from mcp_server_mattermost.middleware import LoggingMiddleware

        middleware = LoggingMiddleware()

        mock_context = MagicMock()
        mock_context.fastmcp_context.request_id = "req-123"
        mock_context.message.name = "post_message"
        mock_context.message.arguments = {}

        mock_call_next = AsyncMock(side_effect=ValueError("Test error"))

        with (
            patch("mcp_server_mattermost.middleware.get_http_request", side_effect=Exception("No HTTP")),
            patch("mcp_server_mattermost.middleware.logger") as mock_logger,
            pytest.raises(ValueError, match="Test error"),
        ):
            await middleware.on_call_tool(mock_context, mock_call_next)

        # Verify logger.info was called for start and logger.error for error
        assert mock_logger.info.call_count == 1  # tool_call_start
        assert mock_logger.error.call_count == 1  # tool_call_error

        # Check the error call
        error_call_kwargs = mock_logger.error.call_args[1]["extra"]
        assert error_call_kwargs["event"] == "tool_call_error"
        assert error_call_kwargs["tool"] == "post_message"
        assert error_call_kwargs["error_type"] == "ValueError"
        assert error_call_kwargs["error_message"] == "Test error"


class TestLoggingMiddlewareContextVar:
    """Test ContextVar propagation."""

    @pytest.mark.asyncio
    async def test_sets_request_id_contextvar(self):
        """request_id available via ContextVar during tool execution."""
        from mcp_server_mattermost.logging import request_id_var
        from mcp_server_mattermost.middleware import LoggingMiddleware

        middleware = LoggingMiddleware()

        captured_request_id = None

        async def capture_request_id(context):
            nonlocal captured_request_id
            captured_request_id = request_id_var.get()
            return MagicMock()

        mock_context = MagicMock()
        mock_context.fastmcp_context.request_id = "req-123"
        mock_context.message.name = "test_tool"
        mock_context.message.arguments = {}

        with patch(
            "mcp_server_mattermost.middleware.get_http_request",
            side_effect=Exception("No HTTP"),
        ):
            await middleware.on_call_tool(mock_context, capture_request_id)

        assert captured_request_id == "req-123"
