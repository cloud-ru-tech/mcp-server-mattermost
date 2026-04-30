"""Mattermost OAuthProxy construction."""

import hashlib
from base64 import urlsafe_b64encode
from typing import Any
from urllib.parse import urlencode

from fastmcp.server.auth import OAuthProxy

from .auth import MattermostTokenVerifier
from .config import OAuthClientType, Settings


class MattermostOAuthProxy(OAuthProxy):
    """OAuthProxy variant for Mattermost's OAuth service provider.

    FastMCP validates the MCP client's RFC8707 resource indicator locally and
    stores it in the transaction. Mattermost does not advertise resource
    indicator support and rejects the extra parameter on /oauth/authorize, so
    we intentionally do not forward it upstream.
    """

    def _build_upstream_authorize_url(self, txn_id: str, transaction: dict[str, Any]) -> str:
        """Construct the Mattermost authorize URL without RFC8707 resource."""
        query_params: dict[str, Any] = {
            "response_type": "code",
            "client_id": self._upstream_client_id,
            "redirect_uri": f"{str(self.base_url).rstrip('/')}{self._redirect_path}",
            "state": txn_id,
        }

        scopes_to_use = transaction.get("scopes") or self.required_scopes or []
        if scopes_to_use:
            query_params["scope"] = " ".join(scopes_to_use)

        proxy_code_verifier = transaction.get("proxy_code_verifier")
        if proxy_code_verifier:
            challenge_bytes = hashlib.sha256(proxy_code_verifier.encode()).digest()
            proxy_code_challenge = urlsafe_b64encode(challenge_bytes).decode().rstrip("=")
            query_params["code_challenge"] = proxy_code_challenge
            query_params["code_challenge_method"] = "S256"

        if self._extra_authorize_params:
            query_params.update(self._extra_authorize_params)

        separator = "&" if "?" in self._upstream_authorization_endpoint else "?"
        return f"{self._upstream_authorization_endpoint}{separator}{urlencode(query_params)}"


def build_mattermost_oauth_proxy(settings: Settings) -> OAuthProxy:
    """Build a FastMCP OAuthProxy configured for Mattermost OAuth.

    Args:
        settings: Validated application settings.

    Returns:
        Configured FastMCP OAuthProxy instance.

    Raises:
        ValueError: If oauth_proxy settings are missing.
    """
    if not settings.oauth_mcp_public_url:
        msg = "oauth_mcp_public_url is required"
        raise ValueError(msg)
    if not settings.oauth_client_id:
        msg = "oauth_client_id is required"
        raise ValueError(msg)

    mattermost_public_url = settings.oauth_mattermost_public_url or settings.url

    if settings.oauth_client_type is OAuthClientType.PUBLIC:
        return MattermostOAuthProxy(
            upstream_authorization_endpoint=f"{mattermost_public_url}/oauth/authorize",
            upstream_token_endpoint=f"{settings.url}/oauth/access_token",
            upstream_client_id=settings.oauth_client_id,
            upstream_client_secret="",
            token_verifier=MattermostTokenVerifier(),
            base_url=settings.oauth_mcp_public_url,
            redirect_path=settings.oauth_callback_path,
            allowed_client_redirect_uris=settings.oauth_allowed_redirect_uris,
            forward_pkce=True,
            token_endpoint_auth_method="none",  # noqa: S106
            jwt_signing_key=settings.oauth_jwt_signing_key,
            require_authorization_consent=settings.oauth_require_consent,
            fallback_access_token_expiry_seconds=settings.oauth_fallback_access_token_expiry_seconds,
            enable_cimd=False,
        )

    return MattermostOAuthProxy(
        upstream_authorization_endpoint=f"{mattermost_public_url}/oauth/authorize",
        upstream_token_endpoint=f"{settings.url}/oauth/access_token",
        upstream_client_id=settings.oauth_client_id,
        upstream_client_secret=settings.oauth_client_secret or "",
        token_verifier=MattermostTokenVerifier(),
        base_url=settings.oauth_mcp_public_url,
        redirect_path=settings.oauth_callback_path,
        allowed_client_redirect_uris=settings.oauth_allowed_redirect_uris,
        forward_pkce=True,
        token_endpoint_auth_method="client_secret_post",  # noqa: S106
        jwt_signing_key=settings.oauth_jwt_signing_key,
        require_authorization_consent=settings.oauth_require_consent,
        fallback_access_token_expiry_seconds=settings.oauth_fallback_access_token_expiry_seconds,
        enable_cimd=False,
    )
