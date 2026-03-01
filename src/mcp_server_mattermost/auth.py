"""Mattermost token verifier for FastMCP authentication."""

import hashlib
from http import HTTPStatus

import httpx
from cachetools import TTLCache
from fastmcp.server.auth import AccessToken, TokenVerifier

from .logging import logger


_TOKEN_CACHE_TTL = 60  # seconds


class MattermostTokenVerifier(TokenVerifier):
    """Validates bearer tokens by calling Mattermost /api/v4/users/me.

    Implements FastMCP TokenVerifier ABC. Used as ``auth=`` parameter on
    the FastMCP server when ``allow_http_client_tokens=True``.

    Settings are loaded lazily (on first call to ``verify_token``) so that
    this class can be instantiated at module import time without requiring
    ``MATTERMOST_URL`` to be set in the environment.

    Features:
        - Reusable httpx.AsyncClient (avoids TCP+TLS handshake per request)
        - In-memory TTL cache keyed by SHA256 hash of token (60s default)

    Token validation flow:
        1. Check cache — return immediately if valid and not expired
        2. Receive bearer token from MCP client's Authorization header
        3. Call GET /api/v4/users/me with the token
        4. On 200: cache and return AccessToken with mattermost_token in claims
        5. On any error: return None — FastMCP responds with 401
    """

    def __init__(self) -> None:
        """Initialize verifier with empty cache and no HTTP client."""
        super().__init__()
        self._client: httpx.AsyncClient | None = None
        self._cache: TTLCache[str, AccessToken] = TTLCache(maxsize=512, ttl=_TOKEN_CACHE_TTL)

    def _get_client(self) -> httpx.AsyncClient:
        """Return reusable httpx.AsyncClient, creating lazily on first call."""
        if self._client is None:
            from .config import get_settings  # noqa: PLC0415

            settings = get_settings()
            self._client = httpx.AsyncClient(
                verify=settings.verify_ssl,
                timeout=httpx.Timeout(settings.timeout),
            )
        return self._client

    @staticmethod
    def _hash_token(token: str) -> str:
        """Return SHA256 hex digest of token for cache key."""
        return hashlib.sha256(token.encode()).hexdigest()

    async def verify_token(self, token: str) -> AccessToken | None:
        """Validate token against Mattermost and return AccessToken if valid.

        Args:
            token: Bearer token string from Authorization header

        Returns:
            AccessToken with mattermost_token claim if valid, None otherwise
        """
        cache_key = self._hash_token(token)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        from .config import get_settings  # noqa: PLC0415

        settings = get_settings()
        url = f"{settings.url}/api/{settings.api_version}/users/me"
        try:
            client = self._get_client()
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Mattermost token verification failed (network error): %s", exc)
            return None

        if response.status_code == HTTPStatus.OK:
            user = response.json()
            user_id = user.get("id", "unknown")
            logger.debug("Token verified for Mattermost user: %s", user_id)
            access_token = AccessToken(
                token=token,
                client_id=user_id,
                scopes=[],
                claims={"mattermost_token": token},
            )
            self._cache[cache_key] = access_token
            return access_token

        logger.debug("Mattermost token rejected (status=%d)", response.status_code)
        return None

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
