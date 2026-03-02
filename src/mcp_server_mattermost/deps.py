"""Dependency injection providers for MCP tools."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastmcp.server.dependencies import get_access_token

from .client import MattermostClient
from .config import get_settings


@asynccontextmanager
async def get_client() -> AsyncIterator[MattermostClient]:
    """Provide Mattermost client with automatic lifecycle management.

    Token selection logic:
        - STDIO transport: ``get_access_token()`` returns ``None``; falls back to
          ``settings.token`` (``MATTERMOST_TOKEN`` env var).
        - HTTP transport with ``allow_http_client_tokens=True``: FastMCP validates
          the bearer token via ``MattermostTokenVerifier`` before this runs;
          ``get_access_token()`` returns the validated ``AccessToken`` whose
          ``claims["mattermost_token"]`` holds the original Mattermost token.
        - HTTP transport with ``allow_http_client_tokens=False``: flag is ``False``,
          so the access token is ignored; ``settings.token`` is used.

    Yields:
        MattermostClient ready for API calls
    """
    settings = get_settings()
    token: str | None = None

    if settings.allow_http_client_tokens:
        access_token = get_access_token()
        if access_token is not None:
            token = access_token.claims.get("mattermost_token")

    client = MattermostClient(settings, token=token)
    async with client.lifespan():
        yield client
