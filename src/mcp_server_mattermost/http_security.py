"""Transport-security advisories for the HTTP transport.

The ``static_token`` auth mode runs the MCP endpoint with no client authentication:
the shared Mattermost token is used server-side for every tool call. This module warns
(but never refuses) when that mode is served over HTTP — a plain warning on a loopback
bind, a louder one on a non-loopback bind where any reachable peer can drive the tools
with the token's privileges — matching the MCP spec's posture (auth is a SHOULD, and the
hard control is Host/Origin validation). It also resolves the FastMCP Host/Origin
(DNS-rebinding) protection settings and summarizes the resulting per-connection posture
for operators.
"""

import ipaddress
from typing import Literal, TypedDict

from .config import AuthMode, Settings


_NON_LOOPBACK_WARNING = (
    "Unauthenticated HTTP on a non-loopback address ({host}): the MCP endpoint executes tools "
    "with the shared Mattermost token and performs NO client authentication, so any peer that can "
    "reach {host} can drive the tools with the token's privileges. Put an authenticating reverse "
    "proxy in front, or switch to MATTERMOST_AUTH_MODE=client_token or oauth_proxy. Host/Origin "
    "DNS-rebinding protection is decided per connection from the local address it arrives on: loopback "
    "arrivals are validated, other arrivals are not until you set MATTERMOST_HTTP_ALLOWED_HOSTS (Host "
    "and Origin) or MATTERMOST_HTTP_ALLOWED_ORIGINS (Origin only)."
)

_LOOPBACK_WARNING = (
    "Unauthenticated HTTP on loopback: the MCP endpoint executes tools with the shared "
    "Mattermost token and performs no client authentication. Ensure this host is trusted; "
    "for networked or multi-user access use MATTERMOST_AUTH_MODE=client_token or oauth_proxy. "
    "Host/Origin DNS-rebinding protection is active."
)

_PROTECTION_POSTURE = (
    "HTTP Host/Origin protection active (mode=auto, allowed_hosts={hosts}, allowed_origins={origins}). "
    "Each connection is validated by the local address it arrives on: arrivals on 127.0.0.1/localhost/::1 "
    "always, other arrivals only when an allowlist is set."
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


def unauthenticated_http_warning(settings: Settings, *, transport: str, host: str) -> str | None:
    """Return a security warning when static_token is served unauthenticated over HTTP.

    Never refuses to start: the server always boots. The warning is louder on a
    non-loopback bind, where the endpoint is reachable by network peers.

    Args:
        settings: Loaded application settings.
        transport: Resolved transport ("http" or "stdio").
        host: Bind host for HTTP transport.

    Returns:
        A security warning string when static_token runs unauthenticated over HTTP
        (louder for a non-loopback bind), or None when there is nothing to warn about.
    """
    if transport != "http" or settings.auth_mode is not AuthMode.STATIC_TOKEN:
        return None

    if not is_loopback_host(host):
        return _NON_LOOPBACK_WARNING.format(host=host)

    return _LOOPBACK_WARNING


def host_origin_posture(settings: Settings) -> str:
    """Return an operator-facing summary of the active Host/Origin protection rule.

    The rule is evaluated per connection, so the summary states the rule and the configured
    allowlists rather than a single on/off verdict, which would not be true of every connection.

    Args:
        settings: Loaded application settings.

    Returns:
        A one-line message naming the configured allowlists and the per-connection rule.
    """
    return _PROTECTION_POSTURE.format(
        hosts=f"[{', '.join(settings.http_allowed_hosts or [])}]",
        origins=f"[{', '.join(settings.http_allowed_origins or [])}]",
    )


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
