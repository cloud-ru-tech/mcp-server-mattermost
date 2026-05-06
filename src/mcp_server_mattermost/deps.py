"""Dependency injection providers for MCP tools."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastmcp.server.dependencies import get_access_token

from .client import MattermostClient
from .config import AuthMode, get_settings
from .exceptions import AuthenticationError


def _get_mattermost_token_from_auth_context() -> str:
    """Return Mattermost token from FastMCP auth context.

    Raises:
        AuthenticationError: If no validated Mattermost token is available.
    """
    access_token = get_access_token()
    token = access_token.claims.get("mattermost_token") if access_token is not None else None
    if not isinstance(token, str) or not token.strip():
        msg = "Mattermost token is required for this auth mode"
        raise AuthenticationError(msg)
    return token


@asynccontextmanager
async def get_client() -> AsyncIterator[MattermostClient]:
    """Provide Mattermost client with automatic lifecycle management.

    Yields:
        MattermostClient ready for API calls
    """
    settings = get_settings()
    token: str | None = None

    if settings.auth_mode in {AuthMode.CLIENT_TOKEN, AuthMode.OAUTH_PROXY}:
        token = _get_mattermost_token_from_auth_context()

    client = MattermostClient(settings, token=token)
    async with client.lifespan():
        yield client
