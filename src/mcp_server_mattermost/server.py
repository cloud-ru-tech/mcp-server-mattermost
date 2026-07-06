"""FastMCP server for Mattermost integration."""

from collections.abc import AsyncIterator
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan
from fastmcp.server.providers import FileSystemProvider
from starlette.requests import Request
from starlette.responses import JSONResponse

from .auth_factory import build_auth_provider_from_env
from .config import get_settings
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


def _create_mcp() -> FastMCP:
    """Create FastMCP instance with configured authentication.

    Settings are loaded through pydantic-settings so auth mode selection is
    validated consistently across stdio and HTTP transports.

    Returns:
        Configured FastMCP server instance
    """
    install_extra_ca_certs(get_settings())
    auth = build_auth_provider_from_env()
    return FastMCP(
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
