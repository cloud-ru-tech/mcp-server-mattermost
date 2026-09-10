"""Dependency injection providers for MCP tools."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastmcp.server.dependencies import get_access_token

from .client import MattermostClient
from .config import AuthMode, Settings, get_settings
from .exceptions import AuthenticationError, ValidationError
from .http_pool import shared_http_client
from .logging import logger, request_id_var


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

    The pool comes from ``http_pool``, not from the FastMCP lifespan context, so
    these tools also work when imported into another server or driven directly
    as a library. The per-request token is attached by ``MattermostClient``; it
    is never stored in the shared client.

    Yields:
        MattermostClient ready for API calls.
    """
    settings = get_settings()
    token: str | None = None

    if settings.auth_mode in {AuthMode.CLIENT_TOKEN, AuthMode.OAUTH_PROXY}:
        token = _get_mattermost_token_from_auth_context()

    async with shared_http_client(settings) as http_client:
        client = MattermostClient(settings, token=token, http_client=http_client)
        async with client.lifespan():
            yield client


def resolve_team_id(team_id: str | None, settings: Settings) -> str:
    """Resolve a validated tool argument using the deployment's default team.

    Args:
        team_id: Explicit team ID, or None to use the configured default.
        settings: Settings of the client handling this call.

    Returns:
        The explicit or configured team ID.

    Raises:
        ValidationError: Neither a team ID nor a default is available.
    """
    if team_id is not None:
        return team_id
    if settings.default_team_id is not None:
        logger.info(
            "Using configured default team %s",
            settings.default_team_id,
            extra={
                "event": "default_team_resolved",
                "team_id": settings.default_team_id,
                "request_id": request_id_var.get(),
            },
        )
        return settings.default_team_id
    msg = (
        "team_id is required when MATTERMOST_DEFAULT_TEAM_ID is not configured. "
        "Pass team_id; use list_teams to discover available teams."
    )
    raise ValidationError(msg)
