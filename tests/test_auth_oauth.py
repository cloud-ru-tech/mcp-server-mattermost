"""Tests for Mattermost OAuthProxy construction."""

from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from fastmcp.server.auth import OAuthProxy


def test_build_public_oauth_proxy_uses_public_client_settings() -> None:
    from mcp_server_mattermost.auth_oauth import build_mattermost_oauth_proxy
    from mcp_server_mattermost.config import Settings

    settings = Settings(
        url="http://mattermost.internal",
        auth_mode="oauth_proxy",
        oauth_client_type="public",
        oauth_client_id="mm-client",
        oauth_jwt_signing_key="signing-key-1234567890",
        oauth_mcp_public_url="http://localhost:8000",
        oauth_mattermost_public_url="http://localhost:8065",
        oauth_require_consent=False,
        oauth_allowed_redirect_uris=["http://localhost:*"],
        oauth_fallback_access_token_expiry_seconds=3600,
    )

    auth = build_mattermost_oauth_proxy(settings)

    assert isinstance(auth, OAuthProxy)
    assert auth._upstream_authorization_endpoint == "http://localhost:8065/oauth/authorize"
    assert auth._upstream_token_endpoint == "http://mattermost.internal/oauth/access_token"
    assert auth._upstream_client_id == "mm-client"
    assert auth._upstream_client_secret.get_secret_value() == ""
    assert auth._token_endpoint_auth_method == "none"
    assert auth._redirect_path == "/oauth/callback/mm"
    assert auth._forward_pkce is True
    assert auth._allowed_client_redirect_uris == ["http://localhost:*"]
    assert auth._fallback_access_token_expiry_seconds == 3600


def test_build_confidential_oauth_proxy_uses_secret_post() -> None:
    from mcp_server_mattermost.auth_oauth import build_mattermost_oauth_proxy
    from mcp_server_mattermost.config import Settings

    settings = Settings(
        url="https://mattermost.internal",
        auth_mode="oauth_proxy",
        oauth_client_type="confidential",
        oauth_client_id="mm-client",
        oauth_client_secret="mm-secret",
        oauth_mcp_public_url="https://mcp.example.com",
        oauth_callback_path="/custom/callback",
    )

    auth = build_mattermost_oauth_proxy(settings)

    assert isinstance(auth, OAuthProxy)
    assert auth._upstream_authorization_endpoint == "https://mattermost.internal/oauth/authorize"
    assert auth._upstream_token_endpoint == "https://mattermost.internal/oauth/access_token"
    assert auth._upstream_client_secret.get_secret_value() == "mm-secret"
    assert auth._token_endpoint_auth_method == "client_secret_post"
    assert auth._redirect_path == "/custom/callback"


def test_build_oauth_proxy_uses_mattermost_token_verifier() -> None:
    from mcp_server_mattermost.auth import MattermostTokenVerifier
    from mcp_server_mattermost.auth_oauth import build_mattermost_oauth_proxy
    from mcp_server_mattermost.config import Settings

    settings = Settings(
        url="https://mattermost.internal",
        auth_mode="oauth_proxy",
        oauth_client_type="confidential",
        oauth_client_id="mm-client",
        oauth_client_secret="mm-secret",
        oauth_mcp_public_url="https://mcp.example.com",
    )

    auth = build_mattermost_oauth_proxy(settings)

    assert isinstance(auth._token_validator, MattermostTokenVerifier)


def test_build_public_oauth_proxy_passes_explicit_signing_key() -> None:
    from mcp_server_mattermost.auth_oauth import build_mattermost_oauth_proxy
    from mcp_server_mattermost.config import Settings

    settings = Settings(
        url="http://mattermost.internal",
        auth_mode="oauth_proxy",
        oauth_client_type="public",
        oauth_client_id="mm-client",
        oauth_jwt_signing_key="signing-key-1234567890",
        oauth_mcp_public_url="http://localhost:8000",
    )

    with patch("mcp_server_mattermost.auth_oauth.MattermostOAuthProxy") as proxy_cls:
        build_mattermost_oauth_proxy(settings)

    assert proxy_cls.call_args.kwargs["jwt_signing_key"] == "signing-key-1234567890"


def test_mattermost_oauth_proxy_does_not_forward_resource_to_upstream_authorize() -> None:
    """Mattermost rejects RFC8707 resource indicators on /oauth/authorize."""
    from mcp_server_mattermost.auth_oauth import build_mattermost_oauth_proxy
    from mcp_server_mattermost.config import Settings

    settings = Settings(
        url="https://mattermost.internal",
        auth_mode="oauth_proxy",
        oauth_client_type="public",
        oauth_client_id="mm-client",
        oauth_jwt_signing_key="signing-key-1234567890",
        oauth_mcp_public_url="https://mcp.example.com/mattermost",
        oauth_mattermost_public_url="https://mm.example.com",
    )

    auth = build_mattermost_oauth_proxy(settings)
    upstream_url = auth._build_upstream_authorize_url(
        "txn-id",
        {
            "scopes": [],
            "resource": "https://mcp.example.com/mattermost/mcp",
            "proxy_code_verifier": "proxy-verifier",
        },
    )

    query = parse_qs(urlparse(upstream_url).query)

    assert query["client_id"] == ["mm-client"]
    assert query["redirect_uri"] == ["https://mcp.example.com/mattermost/oauth/callback/mm"]
    assert "resource" not in query
