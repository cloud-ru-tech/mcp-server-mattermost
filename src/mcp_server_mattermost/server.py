"""FastMCP server for Mattermost integration."""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Literal

from fastmcp import FastMCP
from fastmcp.server.event_store import EventStore
from fastmcp.server.http import StarletteWithLifespan
from fastmcp.server.lifespan import lifespan
from fastmcp.server.providers import FileSystemProvider
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .auth_factory import build_auth_provider_from_env
from .config import get_settings
from .http_guard_log import GuardRejectionLoggingMiddleware
from .http_security import apply_http_security_settings
from .logging import logger, setup_logging
from .middleware import LoggingMiddleware
from .tls import install_extra_ca_certs


@lifespan
async def app_lifespan(_server: FastMCP) -> AsyncIterator[dict[str, object]]:
    """Manage application lifecycle.

    Args:
        _server: FastMCP server instance (required by FastMCP lifespan protocol)

    Yields:
        Empty dict (no shared lifespan state needed)
    """
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_format)
    logger.info("Starting Mattermost MCP server")
    logger.debug("Server URL: %s", settings.url)
    try:
        yield {}
    finally:
        if _server.auth is not None and hasattr(_server.auth, "close"):
            await _server.auth.close()
        logger.info("Mattermost MCP server shutdown complete")


class MattermostMCP(FastMCP):
    """FastMCP server that logs Host/Origin guard rejections on every HTTP app it builds."""

    def http_app(  # noqa: PLR0913
        self,
        path: str | None = None,
        middleware: list[Middleware] | None = None,
        json_response: bool | None = None,  # noqa: FBT001
        stateless_http: bool | None = None,  # noqa: FBT001
        transport: Literal["http", "streamable-http", "sse"] = "http",
        event_store: EventStore | None = None,
        retry_interval: int | None = None,
        host_origin_protection: bool | Literal["auto"] | None = None,  # noqa: FBT001
        allowed_hosts: list[str] | None = None,
        allowed_origins: list[str] | None = None,
    ) -> StarletteWithLifespan:
        """Build the HTTP app with rejection logging wrapped around the Host/Origin guard.

        ``add_middleware`` prepends, so the logger ends up outside FastMCP's guard and can
        observe the 421/403 it produces — anything passed via ``middleware`` runs inside it.

        Args:
            path: Endpoint path.
            middleware: Additional ASGI middleware, applied inside the guard.
            json_response: Whether to use JSON response format.
            stateless_http: Whether to use stateless HTTP.
            transport: Transport protocol to serve.
            event_store: Event store for resumable streams.
            retry_interval: SSE retry interval.
            host_origin_protection: Host/Origin validation level; defaults to FastMCP settings.
            allowed_hosts: Additional accepted Host header values.
            allowed_origins: Additional accepted browser origins.

        Returns:
            The Starlette application, with rejection logging as its outermost middleware.
        """
        app = super().http_app(
            path=path,
            middleware=middleware,
            json_response=json_response,
            stateless_http=stateless_http,
            transport=transport,
            event_store=event_store,
            retry_interval=retry_interval,
            host_origin_protection=host_origin_protection,
            allowed_hosts=allowed_hosts,
            allowed_origins=allowed_origins,
        )
        app.add_middleware(GuardRejectionLoggingMiddleware)
        return app


def _create_mcp() -> MattermostMCP:
    """Create FastMCP instance with configured authentication and HTTP transport security.

    Settings are loaded through pydantic-settings so auth mode selection is
    validated consistently across stdio and HTTP transports. The Host/Origin
    protection is written into FastMCP's settings here, rather than passed to
    ``mcp.run()``, so it also covers ``fastmcp run``, a standalone ASGI server,
    and this app mounted into a parent Starlette/FastAPI application.

    Returns:
        Configured FastMCP server instance
    """
    settings = get_settings()
    install_extra_ca_certs(settings)
    apply_http_security_settings(settings)
    auth = build_auth_provider_from_env()
    return MattermostMCP(
        name="Mattermost",
        instructions="MCP server for Mattermost team collaboration platform",
        lifespan=app_lifespan,
        providers=[FileSystemProvider(Path(__file__).parent / "tools")],
        auth=auth,
    )


mcp = _create_mcp()
mcp.add_middleware(LoggingMiddleware())


@mcp.custom_route("/health", methods=["GET"])
async def health_check(_request: Request) -> JSONResponse:
    """Health check endpoint for container orchestration.

    Args:
        _request: Incoming HTTP request (required by FastMCP route signature)

    Returns:
        JSON response with service status
    """
    return JSONResponse({"status": "healthy", "service": "mcp-server-mattermost"})
