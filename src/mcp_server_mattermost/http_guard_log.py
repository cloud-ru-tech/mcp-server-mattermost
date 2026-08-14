"""Operator-facing logging for Host/Origin guard rejections.

FastMCP answers a rejected ``Host`` with a bare ``421 Misdirected Request`` and a rejected
``Origin`` with ``403 Forbidden Origin``. Neither names the offending value nor the setting
that would accept it, and the guard runs as the outermost middleware inside the Starlette
app, so nothing installed through ``http_app(middleware=...)`` can observe the rejection.
This middleware is inserted ahead of the guard to log what was rejected; the response the
client receives is left untouched.
"""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .logging import logger


_GUARD_REJECTIONS = {
    421: (b"Misdirected Request", "host", "MATTERMOST_HTTP_ALLOWED_HOSTS"),
    403: (b"Forbidden Origin", "origin", "MATTERMOST_HTTP_ALLOWED_ORIGINS"),
}

_REJECTION_LOG = (
    "HTTP request rejected by Host/Origin protection: %s=%r on %s (arrived on %s, status %d). "
    "Add it to %s if this client is legitimate."
)


def _header(scope: Scope, name: str) -> str:
    raw = name.encode()
    headers: list[tuple[bytes, bytes]] = scope.get("headers", [])
    for key, value in headers:
        if key == raw:
            return value.decode("latin-1")
    return ""


def _arrival_address(scope: Scope) -> str:
    server = scope.get("server")
    return f"{server[0]}:{server[1]}" if server else "unknown"


class GuardRejectionLoggingMiddleware:
    """Log rejections produced by FastMCP's ``HostOriginGuardMiddleware``."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pass the request through, logging a guard rejection if one comes back.

        Args:
            scope: ASGI connection scope.
            receive: ASGI receive callable.
            send: ASGI send callable.
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        status = 0

        async def logging_send(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            elif message["type"] == "http.response.body":
                self._log_if_rejection(scope, status, message.get("body", b""))
                status = 0
            await send(message)

        await self.app(scope, receive, logging_send)

    def _log_if_rejection(self, scope: Scope, status: int, body: bytes) -> None:
        """Log when the response body identifies it as a guard rejection.

        Matching on the body keeps an authentication ``403`` from being reported as an
        ``Origin`` rejection. If FastMCP ever rewords its guard responses this stops
        logging rather than logging something untrue; ``tests/test_http_guard_log.py``
        drives the real guard so the drift surfaces.

        Args:
            scope: ASGI connection scope.
            status: Response status code.
            body: First body chunk of the response.
        """
        rejection = _GUARD_REJECTIONS.get(status)
        if rejection is None:
            return
        expected_body, header_name, env_var = rejection
        if body.strip() != expected_body:
            return
        logger.warning(
            _REJECTION_LOG,
            header_name,
            _header(scope, header_name),
            scope.get("path", ""),
            _arrival_address(scope),
            status,
            env_var,
        )
