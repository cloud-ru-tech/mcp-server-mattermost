"""Dependency injection providers for MCP tools."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from .client import MattermostClient
from .config import Settings, get_settings


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
