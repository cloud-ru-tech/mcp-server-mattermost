"""Mattermost token verifier for FastMCP authentication."""

from http import HTTPStatus

import httpx
from fastmcp.server.auth import AccessToken, TokenVerifier

from .config import Settings
from .logging import logger


class MattermostTokenVerifier(TokenVerifier):
    """Validates bearer tokens by calling Mattermost /api/v4/users/me.

    Implements FastMCP TokenVerifier ABC. Used as `auth=` parameter on
    the FastMCP server when `allow_http_client_tokens=True`.

    Token validation flow:
        1. Receive bearer token from MCP client's Authorization header
        2. Call GET /api/v4/users/me with the token
        3. On 200: return AccessToken with mattermost_token in claims
        4. On any error: return None — FastMCP responds with 401
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize with application settings.

        Args:
            settings: Application configuration (used for URL and SSL settings)
        """
        super().__init__()
        self._settings = settings

    async def verify_token(self, token: str) -> AccessToken | None:
        """Validate token against Mattermost and return AccessToken if valid.

        Args:
            token: Bearer token string from Authorization header

        Returns:
            AccessToken with mattermost_token claim if valid, None otherwise
        """
        url = f"{self._settings.url}/api/{self._settings.api_version}/users/me"
        try:
            async with httpx.AsyncClient(
                verify=self._settings.verify_ssl,
                timeout=httpx.Timeout(self._settings.timeout),
            ) as client:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                )
        except Exception as exc:  # noqa: BLE001 - fail-closed: any error means invalid token
            logger.warning("Mattermost token verification failed (network error): %s", exc)
            return None

        if response.status_code == HTTPStatus.OK:
            user = response.json()
            user_id = user.get("id", "unknown")
            logger.debug("Token verified for Mattermost user: %s", user_id)
            return AccessToken(
                token=token,
                client_id=user_id,
                scopes=[],
                claims={"mattermost_token": token},
            )

        logger.debug("Mattermost token rejected (status=%d)", response.status_code)
        return None
