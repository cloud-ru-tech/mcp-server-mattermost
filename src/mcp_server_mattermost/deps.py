"""Dependency injection providers for MCP tools."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastmcp.server.dependencies import get_access_token, get_context

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
    """Provide a Mattermost client bound to the process-wide shared HTTP pool.

    The shared ``httpx.AsyncClient`` is created once by ``app_lifespan`` and
    reached here via the FastMCP request context. The per-request token is
    attached by ``MattermostClient``; it is never stored in the shared client.

    Yields:
        MattermostClient ready for API calls.

    Raises:
        RuntimeError: If the shared HTTP client is not available (server lifespan not running).
    """
    settings = get_settings()
    token: str | None = None

    if settings.auth_mode in {AuthMode.CLIENT_TOKEN, AuthMode.OAUTH_PROXY}:
        token = _get_mattermost_token_from_auth_context()

    http_client = get_context().lifespan_context.get("http_client")
    if http_client is None:
        msg = "Shared HTTP client is not initialized — app_lifespan is not running"
        raise RuntimeError(msg)

    client = MattermostClient(settings, token=token, http_client=http_client)
    async with client.lifespan():
        yield client
