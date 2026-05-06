"""FastMCP authentication provider selection."""

from fastmcp.server.auth import AuthProvider

from .auth import MattermostTokenVerifier
from .auth_oauth import build_mattermost_oauth_proxy
from .config import AuthMode, Settings, get_settings


def build_auth_provider(settings: Settings) -> AuthProvider | None:
    """Build the FastMCP auth provider for the configured auth mode.

    Args:
        settings: Validated application settings.

    Returns:
        Auth provider for HTTP transports, or None for static token mode.
    """
    if settings.auth_mode is AuthMode.STATIC_TOKEN:
        return None
    if settings.auth_mode is AuthMode.CLIENT_TOKEN:
        return MattermostTokenVerifier()
    if settings.auth_mode is AuthMode.OAUTH_PROXY:
        return build_mattermost_oauth_proxy(settings)

    msg = f"Unsupported auth mode: {settings.auth_mode}"
    raise ValueError(msg)


def build_auth_provider_from_env() -> AuthProvider | None:
    """Build auth provider from environment-backed settings."""
    return build_auth_provider(get_settings())
