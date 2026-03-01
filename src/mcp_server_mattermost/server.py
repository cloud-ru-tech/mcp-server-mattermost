"""FastMCP server for Mattermost integration."""

import os
from collections.abc import AsyncIterator
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan
from fastmcp.server.providers import FileSystemProvider
from pydantic import TypeAdapter
from starlette.requests import Request
from starlette.responses import JSONResponse

from .auth import MattermostTokenVerifier
from .config import get_settings
from .logging import logger, setup_logging
from .middleware import LoggingMiddleware


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
        if isinstance(_server.auth, MattermostTokenVerifier):
            await _server.auth.close()
        logger.info("Mattermost MCP server shutdown complete")


def _create_mcp() -> FastMCP:
    """Create FastMCP instance with optional Mattermost token authentication.

    Reads ``MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS`` directly from the environment
    (without full pydantic validation) so the module can be safely imported
    before ``MATTERMOST_URL`` and ``MATTERMOST_TOKEN`` are configured.
    Full settings validation happens inside the lifespan and ``verify_token``.

    When the flag is ``true``, attaches a ``MattermostTokenVerifier`` that
    validates bearer tokens against the Mattermost API before allowing tool access.

    Returns:
        Configured FastMCP server instance
    """
    allow_http = TypeAdapter(bool).validate_python(os.getenv("MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS", "false"))
    auth: MattermostTokenVerifier | None = MattermostTokenVerifier() if allow_http else None
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
