"""Transport-security guards for the HTTP transport.

The ``static_token`` auth mode runs the MCP endpoint with no client authentication:
the shared Mattermost token is used server-side for every tool call. Exposing that
over HTTP lets any network peer drive the tools with the token's privileges, so this
module refuses that combination unless it is explicitly opted into on loopback, and
resolves the FastMCP Host/Origin (DNS-rebinding) protection settings.
"""

import ipaddress
from typing import Literal, TypedDict

from .config import AuthMode, Settings
from .exceptions import ConfigurationError


_LOOPBACK_REFUSAL = (
    "HTTP transport with MATTERMOST_AUTH_MODE=static_token exposes an MCP endpoint that "
    "requires no client authentication and executes tools with the shared Mattermost token. "
    "Refusing to start. "
    "To run on loopback for local/single-host use, set MATTERMOST_ALLOW_UNAUTHENTICATED_HTTP=true. "
    "For networked or multi-user access, use MATTERMOST_AUTH_MODE=client_token or "
    "MATTERMOST_AUTH_MODE=oauth_proxy instead."
)

_NON_LOOPBACK_REFUSAL = (
    "HTTP transport with MATTERMOST_AUTH_MODE=static_token is bound to a non-loopback address "
    "({host}) without client authentication. Refusing to start. "
    "MATTERMOST_ALLOW_UNAUTHENTICATED_HTTP only permits binding to loopback "
    "(127.0.0.1 / ::1 / localhost). "
    "For network exposure use MATTERMOST_AUTH_MODE=client_token or oauth_proxy, or place an "
    "authenticating reverse proxy in the same network namespace and bind this server to loopback."
)

_LOOPBACK_WARNING = (
    "Unauthenticated HTTP enabled on loopback (MATTERMOST_ALLOW_UNAUTHENTICATED_HTTP=true). "
    "The MCP endpoint executes tools with the shared Mattermost token and performs no client "
    "authentication. Ensure this host is trusted. Host/Origin DNS-rebinding protection is active."
)


def is_loopback_host(host: str) -> bool:
    """Return whether the bind host is a loopback address.

    Args:
        host: Bind host (IP literal or hostname) from ``--host`` / ``MCP_HOST``.

    Returns:
        True for 127.0.0.0/8, ::1, or the literal "localhost"; False otherwise, including
        0.0.0.0 / :: (unspecified) and any resolvable hostname, which are treated as public.
    """
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def enforce_unauthenticated_http_policy(settings: Settings, *, transport: str, host: str) -> str | None:
    """Enforce the fail-closed policy for unauthenticated HTTP.

    Args:
        settings: Loaded application settings.
        transport: Resolved transport ("http" or "stdio").
        host: Bind host for HTTP transport.

    Returns:
        A security warning string when the opted-in loopback combination is risky-but-allowed,
        or None when there is nothing to warn about.

    Raises:
        ConfigurationError: When the transport / auth mode / host combination is forbidden.
    """
    if transport != "http" or settings.auth_mode is not AuthMode.STATIC_TOKEN:
        return None

    if not is_loopback_host(host):
        raise ConfigurationError(_NON_LOOPBACK_REFUSAL.format(host=host))

    if not settings.allow_unauthenticated_http:
        raise ConfigurationError(_LOOPBACK_REFUSAL)

    return _LOOPBACK_WARNING


class HostOriginRunKwargs(TypedDict):
    """Keyword arguments for ``mcp.run(transport="http", **kwargs)``."""

    host_origin_protection: Literal["auto"]
    allowed_hosts: list[str] | None
    allowed_origins: list[str] | None


def resolve_host_origin_kwargs(settings: Settings) -> HostOriginRunKwargs:
    """Build FastMCP Host/Origin protection kwargs for ``mcp.run(transport="http")``.

    Returns:
        Kwargs enabling "auto" DNS-rebinding protection plus any configured allowlists.
    """
    return {
        "host_origin_protection": "auto",
        "allowed_hosts": settings.http_allowed_hosts,
        "allowed_origins": settings.http_allowed_origins,
    }
