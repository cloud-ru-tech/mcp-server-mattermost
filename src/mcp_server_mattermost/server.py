"""FastMCP server for Mattermost integration."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from .client import MattermostClient
from .config import Settings, get_settings
from .logging import logger, setup_logging
from .middleware import LoggingMiddleware


@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncIterator[None]:
    """Manage application lifecycle.

    Args:
        _server: FastMCP server instance (required by FastMCP)

    Yields:
        None
    """
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_format)

    logger.info("Starting Mattermost MCP server")
    logger.debug("Server URL: %s", settings.url)
    yield
    logger.info("Mattermost MCP server shutdown complete")


# Create FastMCP instance with lifespan
mcp = FastMCP(
    name="Mattermost",
    instructions="MCP server for Mattermost team collaboration platform",
    lifespan=app_lifespan,
)

# Register logging middleware
mcp.add_middleware(LoggingMiddleware())


@mcp.custom_route("/health", methods=["GET"])
async def health_check(_request: Request) -> JSONResponse:
    """Health check endpoint for container orchestration.

    Args:
        _request: HTTP request (required by FastMCP)

    Returns:
        JSON response with service status
    """
    return JSONResponse({"status": "healthy", "service": "mcp-server-mattermost"})


# === Dependency Injection Providers ===


def get_settings_dep() -> Settings:
    """Provide application settings.

    Returns:
        Settings instance loaded from environment
    """
    return get_settings()


@asynccontextmanager
async def get_client() -> AsyncIterator[MattermostClient]:
    """Provide Mattermost client with automatic lifecycle management.

    The client is created and destroyed per-request.
    Connection pooling is handled by httpx internally.

    Yields:
        MattermostClient ready for API calls
    """
    settings = get_settings()
    client = MattermostClient(settings)
    async with client.lifespan():
        yield client


# Register tools with mcp instance
# Must happen after mcp and get_client are defined
from . import tools as _tools  # noqa: E402, F401
