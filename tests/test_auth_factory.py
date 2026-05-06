"""Tests for FastMCP auth provider selection."""

from unittest.mock import patch


def test_build_auth_provider_static_token_returns_none() -> None:
    from mcp_server_mattermost.auth_factory import build_auth_provider
    from mcp_server_mattermost.config import Settings

    settings = Settings(url="http://mm.example.com", token="static-token")

    assert build_auth_provider(settings) is None


def test_build_auth_provider_client_token_returns_verifier() -> None:
    from mcp_server_mattermost.auth import MattermostTokenVerifier
    from mcp_server_mattermost.auth_factory import build_auth_provider
    from mcp_server_mattermost.config import Settings

    settings = Settings(url="http://mm.example.com", auth_mode="client_token")

    assert isinstance(build_auth_provider(settings), MattermostTokenVerifier)


def test_build_auth_provider_oauth_proxy_delegates_to_builder() -> None:
    from mcp_server_mattermost.auth_factory import build_auth_provider
    from mcp_server_mattermost.config import Settings

    settings = Settings(
        url="http://mattermost.internal",
        auth_mode="oauth_proxy",
        oauth_client_type="public",
        oauth_client_id="mm-client",
        oauth_jwt_signing_key="signing-key-1234567890",
        oauth_mcp_public_url="http://localhost:8000",
    )

    sentinel = object()
    with patch("mcp_server_mattermost.auth_factory.build_mattermost_oauth_proxy", return_value=sentinel) as builder:
        result = build_auth_provider(settings)

    assert result is sentinel
    builder.assert_called_once_with(settings)


def test_build_auth_provider_from_env_uses_legacy_flag() -> None:
    import os

    from mcp_server_mattermost.auth import MattermostTokenVerifier
    from mcp_server_mattermost.auth_factory import build_auth_provider_from_env
    from mcp_server_mattermost.config import get_settings

    with patch.dict(
        os.environ,
        {"MATTERMOST_URL": "http://mm.example.com", "MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS": "true"},
        clear=True,
    ):
        get_settings.cache_clear()
        provider = build_auth_provider_from_env()
        get_settings.cache_clear()

    assert isinstance(provider, MattermostTokenVerifier)
