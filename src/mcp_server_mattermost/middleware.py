"""Middleware for structured logging of tool calls."""

import time
from collections.abc import Awaitable, Callable
from typing import Any

from fastmcp.server.dependencies import get_http_request
from fastmcp.server.middleware import Middleware, MiddlewareContext

from .logging import logger, request_id_var


class LoggingMiddleware(Middleware):
    """Middleware that logs all tool calls with request correlation."""

    WHITELISTED_PARAMS: frozenset[str] = frozenset(
        {
            # IDs
            "team_id",
            "channel_id",
            "user_id",
            "post_id",
            "file_id",
            "bookmark_id",
            "root_id",
            # Pagination
            "page",
            "per_page",
            "limit",
            "offset",
            # Flags
            "include_deleted",
            "exclude_bots",
            "is_or_search",
            # Bookmarks
            "bookmarks_since",
            "new_sort_order",
            "bookmark_type",
        },
    )

    async def on_call_tool(
        self,
        context: MiddlewareContext,
        call_next: Callable[[MiddlewareContext], Awaitable[Any]],
    ) -> Any:  # noqa: ANN401
        """Log tool call start, success, and error events.

        Args:
            context: Middleware context with message and FastMCP context
            call_next: Next middleware or tool handler

        Returns:
            Tool result

        Raises:
            Exception: Re-raises any exception from tool after logging
        """
        request_id = self._get_request_id(context)
        request_id_var.set(request_id)

        tool_name = context.message.name
        params = self._redact_params(context.message.arguments or {})

        start_time = time.monotonic()

        logger.info(
            "",
            extra={
                "event": "tool_call_start",
                "request_id": request_id,
                "tool": tool_name,
                "params": params,
            },
        )

        try:
            result = await call_next(context)
        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000

            logger.error(
                "",
                extra={
                    "event": "tool_call_error",
                    "request_id": request_id,
                    "tool": tool_name,
                    "duration_ms": round(duration_ms, 2),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )

            raise
        else:
            duration_ms = (time.monotonic() - start_time) * 1000

            logger.info(
                "",
                extra={
                    "event": "tool_call_success",
                    "request_id": request_id,
                    "tool": tool_name,
                    "duration_ms": round(duration_ms, 2),
                },
            )

            return result

    def _get_request_id(self, context: MiddlewareContext) -> str:
        """Get request ID from HTTP header or FastMCP context.

        Tries X-Request-ID header first (HTTP transport),
        falls back to FastMCP's request_id (stdio transport).

        Args:
            context: Middleware context

        Returns:
            Request ID string
        """
        try:
            http_request = get_http_request()
            client_request_id = http_request.headers.get("X-Request-ID")
            if client_request_id:
                return client_request_id
        except Exception:  # noqa: BLE001, S110
            # stdio transport has no HTTP request - fall back to FastMCP request_id
            pass

        # Fall back to FastMCP context request_id, or generate one if not available
        if context.fastmcp_context and hasattr(context.fastmcp_context, "request_id"):
            return context.fastmcp_context.request_id
        return "unknown"

    def _redact_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Filter params to only include whitelisted keys.

        Args:
            params: Original tool parameters

        Returns:
            Filtered dict with only safe params
        """
        return {k: v for k, v in params.items() if k in self.WHITELISTED_PARAMS}
