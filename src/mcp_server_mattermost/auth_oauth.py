"""Mattermost OAuthProxy construction."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastmcp.server.auth import OAuthProxy

from .auth import MattermostTokenVerifier
from .config import OAuthClientType, Settings


if TYPE_CHECKING:
    from key_value.aio.protocols import AsyncKeyValue
    from pydantic import AnyHttpUrl


class MattermostOAuthProxy(OAuthProxy):
    """OAuthProxy variant for Mattermost's OAuth service provider.

    FastMCP validates the MCP client's RFC8707 resource indicator locally and
    stores it in the transaction. Mattermost does not advertise resource
    indicator support and rejects the extra parameter on /oauth/authorize, so
    we intentionally do not forward it upstream.
    """

    def __init__(  # noqa: PLR0913
        self,
        *,
        upstream_authorization_endpoint: str,
        upstream_token_endpoint: str,
        upstream_client_id: str,
        upstream_client_secret: str,
        mattermost_verifier: MattermostTokenVerifier,
        base_url: AnyHttpUrl | str,
        upstream_revocation_endpoint: str | None = None,
        redirect_path: str | None = None,
        issuer_url: AnyHttpUrl | str | None = None,
        service_documentation_url: AnyHttpUrl | str | None = None,
        allowed_client_redirect_uris: list[str] | None = None,
        valid_scopes: list[str] | None = None,
        forward_pkce: bool = True,
        token_endpoint_auth_method: str | None = None,
        extra_authorize_params: dict[str, str] | None = None,
        extra_token_params: dict[str, str] | None = None,
        client_storage: AsyncKeyValue | None = None,
        jwt_signing_key: str | bytes | None = None,
        require_authorization_consent: bool = True,
        consent_csp_policy: str | None = None,
        fallback_access_token_expiry_seconds: int | None = None,
        enable_cimd: bool = True,
    ) -> None:
        """Initialize the proxy with the Mattermost verifier as its token verifier."""
        super().__init__(
            upstream_authorization_endpoint=upstream_authorization_endpoint,
            upstream_token_endpoint=upstream_token_endpoint,
            upstream_client_id=upstream_client_id,
            upstream_client_secret=upstream_client_secret,
            upstream_revocation_endpoint=upstream_revocation_endpoint,
            token_verifier=mattermost_verifier,
            base_url=base_url,
            redirect_path=redirect_path,
            issuer_url=issuer_url,
            service_documentation_url=service_documentation_url,
            allowed_client_redirect_uris=allowed_client_redirect_uris,
            valid_scopes=valid_scopes,
            forward_pkce=forward_pkce,
            token_endpoint_auth_method=token_endpoint_auth_method,
            extra_authorize_params=extra_authorize_params,
            extra_token_params=extra_token_params,
            client_storage=client_storage,
            jwt_signing_key=jwt_signing_key,
            require_authorization_consent=require_authorization_consent,
            consent_csp_policy=consent_csp_policy,
            fallback_access_token_expiry_seconds=fallback_access_token_expiry_seconds,
            enable_cimd=enable_cimd,
        )

    def _build_upstream_authorize_url(self, txn_id: str, transaction: dict[str, Any]) -> str:
        """Construct the Mattermost authorize URL without RFC8707 resource."""
        url = super()._build_upstream_authorize_url(txn_id, transaction)
        parts = urlsplit(url)
        query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key != "resource"]
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


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
    common_kwargs: dict[str, Any] = {
        "upstream_authorization_endpoint": f"{mattermost_public_url}/oauth/authorize",
        "upstream_token_endpoint": f"{settings.url}/oauth/access_token",
        "upstream_client_id": settings.oauth_client_id,
        "mattermost_verifier": MattermostTokenVerifier(),
        "base_url": settings.oauth_mcp_public_url,
        "redirect_path": settings.oauth_callback_path,
        "allowed_client_redirect_uris": settings.oauth_allowed_redirect_uris,
        "forward_pkce": True,
        "jwt_signing_key": settings.oauth_jwt_signing_key,
        "require_authorization_consent": settings.oauth_require_consent,
        "fallback_access_token_expiry_seconds": settings.oauth_fallback_access_token_expiry_seconds,
        "enable_cimd": False,
    }

    if settings.oauth_client_type is OAuthClientType.PUBLIC:
        return MattermostOAuthProxy(
            **common_kwargs,
            upstream_client_secret="",
            token_endpoint_auth_method="none",  # noqa: S106
        )

    return MattermostOAuthProxy(
        **common_kwargs,
        upstream_client_secret=settings.oauth_client_secret or "",
        token_endpoint_auth_method="client_secret_post",  # noqa: S106
    )
