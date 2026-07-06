"""Configuration management using Pydantic Settings."""

from enum import Enum
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthMode(str, Enum):
    """Mattermost authentication mode."""

    STATIC_TOKEN = "static_token"  # noqa: S105
    CLIENT_TOKEN = "client_token"  # noqa: S105
    OAUTH_PROXY = "oauth_proxy"


class OAuthClientType(str, Enum):
    """Mattermost OAuth application client type."""

    PUBLIC = "public"
    CONFIDENTIAL = "confidential"


_LOCALHOST_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _uses_https_or_localhost(url: str) -> bool:
    """Return whether URL is HTTPS or points at localhost."""
    parts = urlsplit(url)
    return parts.scheme == "https" or parts.hostname in _LOCALHOST_HOSTS


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Environment variables:
        MATTERMOST_URL: Mattermost server URL (required)
        MATTERMOST_AUTH_MODE: static_token, client_token, or oauth_proxy
        MATTERMOST_TOKEN: Bot/user access token (required for static_token)
        MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS: Deprecated alias for MATTERMOST_AUTH_MODE=client_token
        MATTERMOST_OAUTH_CLIENT_ID: Mattermost OAuth App client ID for oauth_proxy
        MATTERMOST_OAUTH_CLIENT_TYPE: public or confidential for oauth_proxy
        MATTERMOST_OAUTH_CLIENT_SECRET: Mattermost OAuth App secret for confidential oauth_proxy
        MATTERMOST_OAUTH_JWT_SIGNING_KEY: FastMCP JWT signing key for oauth_proxy
        MATTERMOST_OAUTH_MCP_PUBLIC_URL: Public base URL of this MCP server
        MATTERMOST_OAUTH_MATTERMOST_PUBLIC_URL: Browser-facing Mattermost URL
        MATTERMOST_TIMEOUT: Request timeout in seconds (default: 30)
        MATTERMOST_MAX_RETRIES: Max retry attempts (default: 3)
        MATTERMOST_VERIFY_SSL: Verify SSL certificates (default: true)
        MATTERMOST_EXTRA_CA_CERTS: Path to PEM file with additional trusted CAs
        MATTERMOST_LOG_LEVEL: Logging level (default: INFO)
        MATTERMOST_LOG_FORMAT: Log format, 'json' or 'text' (default: json)
        MATTERMOST_API_VERSION: API version (default: v4)
    """

    model_config = SettingsConfigDict(
        env_prefix="MATTERMOST_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    url: str = Field(description="Mattermost server URL")
    token: str | None = Field(default=None, description="Bot or user access token")
    auth_mode: AuthMode = Field(default=AuthMode.STATIC_TOKEN, description="Authentication mode")
    allow_http_client_tokens: bool = Field(
        default=False,
        description="Deprecated alias for auth_mode=client_token",
    )
    timeout: int = Field(default=30, ge=1, le=300, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    extra_ca_certs: str | None = Field(
        default=None,
        description=(
            "Path to a PEM file with additional CA certificates appended to "
            "the default trust store (corporate/private CAs)"
        ),
    )
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format: 'json' or 'text'")
    api_version: str = Field(default="v4", description="Mattermost API version")

    oauth_client_id: str | None = Field(default=None, description="Mattermost OAuth App client ID")
    oauth_client_type: OAuthClientType = Field(
        default=OAuthClientType.CONFIDENTIAL,
        description="Mattermost OAuth App client type",
    )
    oauth_client_secret: str | None = Field(default=None, description="Mattermost OAuth App client secret")
    oauth_callback_path: str = Field(default="/oauth/callback/mm", description="OAuth callback path")
    oauth_jwt_signing_key: str | None = Field(default=None, description="FastMCP JWT signing key")
    oauth_mcp_public_url: str | None = Field(default=None, description="Public base URL of this MCP server")
    oauth_mattermost_public_url: str | None = Field(
        default=None,
        description="Browser-facing Mattermost URL for OAuth redirects",
    )
    oauth_allowed_redirect_uris: list[str] = Field(
        default_factory=lambda: ["http://localhost:*", "http://127.0.0.1:*"],
        description="Allowed MCP client redirect URI patterns",
    )
    oauth_require_consent: bool = Field(default=True, description="Require FastMCP consent screen")
    oauth_fallback_access_token_expiry_seconds: int | None = Field(
        default=None,
        ge=1,
        description="Fallback access token TTL when Mattermost omits expires_in",
    )

    @field_validator("url", "oauth_mcp_public_url", "oauth_mattermost_public_url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        """Remove trailing slash."""
        if v is None:
            return v
        return v.rstrip("/")

    @field_validator("extra_ca_certs")
    @classmethod
    def validate_extra_ca_certs(cls, v: str | None) -> str | None:
        """Ensure the extra CA bundle exists when configured."""
        if v is None or not v.strip():
            return None
        if not Path(v).is_file():
            msg = f"MATTERMOST_EXTRA_CA_CERTS file not found: {v}"
            raise ValueError(msg)
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure level is in DEBUG, INFO, WARNING, ERROR, or CRITICAL."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid_levels:
            msg = f"Invalid log level: {v}. Must be one of {valid_levels}"
            raise ValueError(msg)
        return upper

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Ensure format is 'json' or 'text'."""
        valid_formats = {"json", "text"}
        lower = v.lower()
        if lower not in valid_formats:
            msg = f"Invalid log format: {v}. Must be one of {valid_formats}"
            raise ValueError(msg)
        return lower

    @field_validator("oauth_callback_path")
    @classmethod
    def validate_oauth_callback_path(cls, v: str) -> str:
        """Ensure OAuth callback path is absolute."""
        if not v.startswith("/"):
            msg = "MATTERMOST_OAUTH_CALLBACK_PATH must start with '/'"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def validate_auth_configuration(self) -> "Settings":
        """Validate mode-specific authentication settings."""
        if self.allow_http_client_tokens:
            if "auth_mode" not in self.model_fields_set:
                self.auth_mode = AuthMode.CLIENT_TOKEN
            elif self.auth_mode is not AuthMode.CLIENT_TOKEN:
                msg = "MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS conflicts with MATTERMOST_AUTH_MODE"
                raise ValueError(msg)

        if self.auth_mode is AuthMode.STATIC_TOKEN and not (self.token and self.token.strip()):
            msg = "MATTERMOST_TOKEN is required when MATTERMOST_AUTH_MODE=static_token"
            raise ValueError(msg)

        if self.auth_mode is AuthMode.OAUTH_PROXY:
            self._validate_oauth_proxy()

        return self

    def _validate_oauth_proxy(self) -> None:
        """Validate oauth_proxy-specific settings."""
        if not self.oauth_mcp_public_url:
            msg = "MATTERMOST_OAUTH_MCP_PUBLIC_URL is required when MATTERMOST_AUTH_MODE=oauth_proxy"
            raise ValueError(msg)
        if not self.oauth_client_id:
            msg = "MATTERMOST_OAUTH_CLIENT_ID is required when MATTERMOST_AUTH_MODE=oauth_proxy"
            raise ValueError(msg)
        if self.oauth_client_type is OAuthClientType.PUBLIC and not (
            self.oauth_jwt_signing_key and self.oauth_jwt_signing_key.strip()
        ):
            msg = "MATTERMOST_OAUTH_JWT_SIGNING_KEY is required for public OAuth clients"
            raise ValueError(msg)
        if self.oauth_client_type is OAuthClientType.CONFIDENTIAL and not (
            self.oauth_client_secret and self.oauth_client_secret.strip()
        ):
            msg = "MATTERMOST_OAUTH_CLIENT_SECRET is required for confidential OAuth clients"
            raise ValueError(msg)
        if not _uses_https_or_localhost(self.oauth_mcp_public_url):
            msg = "MATTERMOST_OAUTH_MCP_PUBLIC_URL must use HTTPS unless it is localhost"
            raise ValueError(msg)
        browser_facing_mattermost_url = self.oauth_mattermost_public_url or self.url
        if not _uses_https_or_localhost(browser_facing_mattermost_url):
            msg = (
                "Browser-facing Mattermost URL must use HTTPS unless it is localhost. "
                "Set MATTERMOST_OAUTH_MATTERMOST_PUBLIC_URL to an HTTPS URL or use HTTPS for MATTERMOST_URL."
            )
            raise ValueError(msg)


@lru_cache
def get_settings() -> Settings:
    """Get application settings (cached).

    Returns:
        Application settings

    Raises:
        ConfigurationError: If required settings are missing
    """
    from .exceptions import ConfigurationError  # noqa: PLC0415

    try:
        return Settings()
    except Exception as e:
        msg = f"Failed to load configuration: {e}"
        raise ConfigurationError(msg) from e
