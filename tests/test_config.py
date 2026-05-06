import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("MATTERMOST_URL", "https://example.com")
    monkeypatch.setenv("MATTERMOST_TOKEN", "test-token")

    from mcp_server_mattermost.config import Settings

    settings = Settings()
    assert settings.url == "https://example.com"
    assert settings.token == "test-token"


def test_settings_removes_trailing_slash(monkeypatch):
    monkeypatch.setenv("MATTERMOST_URL", "https://example.com/")
    monkeypatch.setenv("MATTERMOST_TOKEN", "test-token")

    from mcp_server_mattermost.config import Settings

    settings = Settings()
    assert settings.url == "https://example.com"


def test_settings_defaults(monkeypatch):
    monkeypatch.setenv("MATTERMOST_URL", "https://example.com")
    monkeypatch.setenv("MATTERMOST_TOKEN", "test-token")

    from mcp_server_mattermost.config import Settings

    settings = Settings()
    assert settings.timeout == 30
    assert settings.max_retries == 3
    assert settings.verify_ssl is True
    assert settings.log_level == "INFO"


def test_settings_validates_log_level(monkeypatch):
    monkeypatch.setenv("MATTERMOST_URL", "https://example.com")
    monkeypatch.setenv("MATTERMOST_TOKEN", "test-token")
    monkeypatch.setenv("MATTERMOST_LOG_LEVEL", "INVALID")

    from pydantic import ValidationError

    from mcp_server_mattermost.config import Settings

    with pytest.raises(ValidationError):
        Settings()


def test_get_settings_raises_on_missing_url(monkeypatch):
    monkeypatch.delenv("MATTERMOST_URL", raising=False)
    monkeypatch.delenv("MATTERMOST_TOKEN", raising=False)

    from mcp_server_mattermost.config import get_settings
    from mcp_server_mattermost.exceptions import ConfigurationError

    # Clear the lru_cache to force re-reading environment
    get_settings.cache_clear()

    with pytest.raises(ConfigurationError):
        get_settings()


def test_api_version_default():
    """Test default API version is v4."""
    from mcp_server_mattermost.config import Settings

    settings = Settings(url="https://mm.example.com", token="token")
    assert settings.api_version == "v4"


def test_api_version_custom(monkeypatch):
    """Test custom API version can be set."""
    monkeypatch.setenv("MATTERMOST_URL", "https://mm.example.com")
    monkeypatch.setenv("MATTERMOST_TOKEN", "token")
    monkeypatch.setenv("MATTERMOST_API_VERSION", "v5")

    from mcp_server_mattermost.config import Settings

    settings = Settings()
    assert settings.api_version == "v5"


def test_log_format_default(mock_settings):
    """Default log_format is 'json'."""
    from mcp_server_mattermost.config import get_settings

    settings = get_settings()
    assert settings.log_format == "json"


def test_log_format_text_valid(monkeypatch):
    """log_format='text' is valid."""
    monkeypatch.setenv("MATTERMOST_URL", "https://test.mattermost.com")
    monkeypatch.setenv("MATTERMOST_TOKEN", "test-token")
    monkeypatch.setenv("MATTERMOST_LOG_FORMAT", "text")

    from mcp_server_mattermost.config import Settings

    settings = Settings()
    assert settings.log_format == "text"


def test_log_format_invalid_raises(monkeypatch):
    """Invalid log_format raises ValidationError."""
    from pydantic import ValidationError

    monkeypatch.setenv("MATTERMOST_URL", "https://test.mattermost.com")
    monkeypatch.setenv("MATTERMOST_TOKEN", "test-token")
    monkeypatch.setenv("MATTERMOST_LOG_FORMAT", "xml")

    from mcp_server_mattermost.config import Settings

    with pytest.raises(ValidationError, match="log_format"):
        Settings()


class TestAllowHttpClientTokens:
    """Tests for allow_http_client_tokens config field and its model validator."""

    def test_token_optional_when_allow_http_client_tokens(self) -> None:
        """No token required when allow_http_client_tokens=True."""
        from mcp_server_mattermost.config import Settings

        with patch.dict(
            os.environ,
            {
                "MATTERMOST_URL": "http://mm.example.com",
                "MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS": "true",
            },
            clear=True,
        ):
            settings = Settings()
            assert settings.allow_http_client_tokens is True
            assert settings.token is None

    def test_token_required_when_not_allow_http_client_tokens(self) -> None:
        """Token required when allow_http_client_tokens=False (default)."""
        from mcp_server_mattermost.config import Settings

        with (
            patch.dict(os.environ, {"MATTERMOST_URL": "http://mm.example.com"}, clear=True),
            pytest.raises(ValidationError, match="MATTERMOST_TOKEN is required"),
        ):
            Settings()


class TestAuthModeSettings:
    def test_default_auth_mode_is_static_token(self) -> None:
        from mcp_server_mattermost.config import AuthMode, Settings

        with patch.dict(
            os.environ,
            {"MATTERMOST_URL": "http://mm.example.com", "MATTERMOST_TOKEN": "static-token"},
            clear=True,
        ):
            settings = Settings()

        assert settings.auth_mode is AuthMode.STATIC_TOKEN
        assert settings.allow_http_client_tokens is False

    def test_auth_mode_client_token_does_not_require_static_token(self) -> None:
        from mcp_server_mattermost.config import AuthMode, Settings

        with patch.dict(
            os.environ,
            {"MATTERMOST_URL": "http://mm.example.com", "MATTERMOST_AUTH_MODE": "client_token"},
            clear=True,
        ):
            settings = Settings()

        assert settings.auth_mode is AuthMode.CLIENT_TOKEN
        assert settings.token is None

    def test_legacy_allow_http_client_tokens_maps_to_client_token(self) -> None:
        from mcp_server_mattermost.config import AuthMode, Settings

        with patch.dict(
            os.environ,
            {"MATTERMOST_URL": "http://mm.example.com", "MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS": "true"},
            clear=True,
        ):
            settings = Settings()

        assert settings.auth_mode is AuthMode.CLIENT_TOKEN
        assert settings.allow_http_client_tokens is True

    def test_legacy_flag_conflicts_with_explicit_static_token_mode(self) -> None:
        from mcp_server_mattermost.config import Settings

        with (
            patch.dict(
                os.environ,
                {
                    "MATTERMOST_URL": "http://mm.example.com",
                    "MATTERMOST_TOKEN": "static-token",
                    "MATTERMOST_AUTH_MODE": "static_token",
                    "MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS": "true",
                },
                clear=True,
            ),
            pytest.raises(ValidationError, match="MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS conflicts"),
        ):
            Settings()

    def test_static_token_requires_token(self) -> None:
        from mcp_server_mattermost.config import Settings

        with (
            patch.dict(
                os.environ,
                {"MATTERMOST_URL": "http://mm.example.com", "MATTERMOST_AUTH_MODE": "static_token"},
                clear=True,
            ),
            pytest.raises(ValidationError, match="MATTERMOST_TOKEN is required when MATTERMOST_AUTH_MODE=static_token"),
        ):
            Settings()

    def test_oauth_proxy_public_minimal_valid_settings(self) -> None:
        from mcp_server_mattermost.config import AuthMode, OAuthClientType, Settings

        with patch.dict(
            os.environ,
            {
                "MATTERMOST_URL": "http://mattermost.internal",
                "MATTERMOST_AUTH_MODE": "oauth_proxy",
                "MATTERMOST_OAUTH_CLIENT_TYPE": "public",
                "MATTERMOST_OAUTH_CLIENT_ID": "mm-oauth-client",
                "MATTERMOST_OAUTH_JWT_SIGNING_KEY": "signing-key-1234567890",
                "MATTERMOST_OAUTH_MCP_PUBLIC_URL": "http://localhost:8000",
            },
            clear=True,
        ):
            settings = Settings()

        assert settings.auth_mode is AuthMode.OAUTH_PROXY
        assert settings.oauth_client_type is OAuthClientType.PUBLIC
        assert settings.oauth_client_id == "mm-oauth-client"
        assert settings.oauth_mcp_public_url == "http://localhost:8000"
        assert settings.oauth_callback_path == "/oauth/callback/mm"
        assert settings.oauth_allowed_redirect_uris == ["http://localhost:*", "http://127.0.0.1:*"]

    def test_oauth_proxy_requires_client_id(self) -> None:
        from mcp_server_mattermost.config import Settings

        with (
            patch.dict(
                os.environ,
                {
                    "MATTERMOST_URL": "http://mattermost.internal",
                    "MATTERMOST_AUTH_MODE": "oauth_proxy",
                    "MATTERMOST_OAUTH_CLIENT_TYPE": "public",
                    "MATTERMOST_OAUTH_JWT_SIGNING_KEY": "signing-key-1234567890",
                    "MATTERMOST_OAUTH_MCP_PUBLIC_URL": "http://localhost:8000",
                },
                clear=True,
            ),
            pytest.raises(ValidationError, match="MATTERMOST_OAUTH_CLIENT_ID is required"),
        ):
            Settings()

    def test_oauth_proxy_public_requires_jwt_signing_key(self) -> None:
        from mcp_server_mattermost.config import Settings

        with (
            patch.dict(
                os.environ,
                {
                    "MATTERMOST_URL": "http://mattermost.internal",
                    "MATTERMOST_AUTH_MODE": "oauth_proxy",
                    "MATTERMOST_OAUTH_CLIENT_TYPE": "public",
                    "MATTERMOST_OAUTH_CLIENT_ID": "mm-oauth-client",
                    "MATTERMOST_OAUTH_MCP_PUBLIC_URL": "http://localhost:8000",
                },
                clear=True,
            ),
            pytest.raises(ValidationError, match="MATTERMOST_OAUTH_JWT_SIGNING_KEY is required for public"),
        ):
            Settings()

    def test_oauth_proxy_confidential_requires_secret(self) -> None:
        from mcp_server_mattermost.config import Settings

        with (
            patch.dict(
                os.environ,
                {
                    "MATTERMOST_URL": "http://mattermost.internal",
                    "MATTERMOST_AUTH_MODE": "oauth_proxy",
                    "MATTERMOST_OAUTH_CLIENT_TYPE": "confidential",
                    "MATTERMOST_OAUTH_CLIENT_ID": "mm-oauth-client",
                    "MATTERMOST_OAUTH_MCP_PUBLIC_URL": "http://localhost:8000",
                },
                clear=True,
            ),
            pytest.raises(ValidationError, match="MATTERMOST_OAUTH_CLIENT_SECRET is required"),
        ):
            Settings()

    def test_oauth_proxy_confidential_valid_settings(self) -> None:
        from mcp_server_mattermost.config import AuthMode, OAuthClientType, Settings

        with patch.dict(
            os.environ,
            {
                "MATTERMOST_URL": "http://mattermost.internal",
                "MATTERMOST_AUTH_MODE": "oauth_proxy",
                "MATTERMOST_OAUTH_CLIENT_TYPE": "confidential",
                "MATTERMOST_OAUTH_CLIENT_ID": "mm-oauth-client",
                "MATTERMOST_OAUTH_CLIENT_SECRET": "mm-secret",
                "MATTERMOST_OAUTH_MCP_PUBLIC_URL": "https://mcp.example.com",
                "MATTERMOST_OAUTH_MATTERMOST_PUBLIC_URL": "https://mattermost.example.com",
            },
            clear=True,
        ):
            settings = Settings()

        assert settings.auth_mode is AuthMode.OAUTH_PROXY
        assert settings.oauth_client_type is OAuthClientType.CONFIDENTIAL
        assert settings.oauth_client_secret == "mm-secret"
        assert settings.oauth_mcp_public_url == "https://mcp.example.com"
        assert settings.oauth_mattermost_public_url == "https://mattermost.example.com"

    def test_oauth_proxy_callback_path_must_start_with_slash(self) -> None:
        from mcp_server_mattermost.config import Settings

        with (
            patch.dict(
                os.environ,
                {
                    "MATTERMOST_URL": "http://mattermost.internal",
                    "MATTERMOST_AUTH_MODE": "oauth_proxy",
                    "MATTERMOST_OAUTH_CLIENT_TYPE": "public",
                    "MATTERMOST_OAUTH_CLIENT_ID": "mm-oauth-client",
                    "MATTERMOST_OAUTH_JWT_SIGNING_KEY": "signing-key-1234567890",
                    "MATTERMOST_OAUTH_MCP_PUBLIC_URL": "http://localhost:8000",
                    "MATTERMOST_OAUTH_CALLBACK_PATH": "oauth/callback/mm",
                },
                clear=True,
            ),
            pytest.raises(ValidationError, match="MATTERMOST_OAUTH_CALLBACK_PATH must start with '/'"),
        ):
            Settings()
