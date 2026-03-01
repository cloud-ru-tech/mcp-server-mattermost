"""FastMCP server for Mattermost integration."""

from collections.abc import AsyncIterator
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan
from fastmcp.server.providers import FileSystemProvider
from starlette.requests import Request
from starlette.responses import JSONResponse

from .config import get_settings
from .logging import logger, setup_logging
from .middleware import LoggingMiddleware


@lifespan
async def app_lifespan(_server: FastMCP) -> AsyncIterator[dict[str, object]]:
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_format)
    logger.info("Starting Mattermost MCP server")
    logger.debug("Server URL: %s", settings.url)
    try:
        yield {}
    finally:
        logger.info("Mattermost MCP server shutdown complete")


mcp = FastMCP(
    name="Mattermost",
    instructions="MCP server for Mattermost team collaboration platform",
    lifespan=app_lifespan,
    providers=[FileSystemProvider(Path(__file__).parent / "tools")],
)

mcp.add_middleware(LoggingMiddleware())


@mcp.custom_route("/health", methods=["GET"])
async def health_check(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "mcp-server-mattermost"})
