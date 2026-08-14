"""Transport-security advisories and posture for the HTTP transport.

The ``static_token`` auth mode runs the MCP endpoint with no client authentication:
the shared Mattermost token is used server-side for every tool call. This module warns
(but never refuses) when that mode is served over HTTP — a plain warning on a loopback
bind, a louder one on a non-loopback bind where any reachable peer can drive the tools
with the token's privileges — matching the MCP spec's posture (auth is a SHOULD, and the
hard control is Host/Origin validation).

It also applies the Host/Origin (DNS-rebinding) protection to FastMCP's own settings, so
the posture holds for every way of serving the app — ``mcp.run()``, ``fastmcp run``, an
ASGI server over ``mcp.http_app()``, or the app mounted into a parent Starlette/FastAPI
application — rather than only for the console entry point.
"""

import ipaddress
from typing import Literal

import fastmcp

from .config import AuthMode, HostOriginProtection, Settings


_NON_LOOPBACK_WARNING = (
    "Unauthenticated HTTP on a non-loopback address ({host}): the MCP endpoint executes tools "
    "with the shared Mattermost token and performs NO client authentication, so any peer that can "
    "reach {host} can drive the tools with the token's privileges. Put an authenticating reverse "
    "proxy in front, or switch to MATTERMOST_AUTH_MODE=client_token or oauth_proxy."
)

_LOOPBACK_WARNING = (
    "Unauthenticated HTTP on loopback: the MCP endpoint executes tools with the shared "
    "Mattermost token and performs no client authentication. Ensure this host is trusted; "
    "for networked or multi-user access use MATTERMOST_AUTH_MODE=client_token or oauth_proxy."
)

_POSTURE_OFF = (
    "HTTP Host/Origin protection is OFF: no request is rejected on its Host or Origin header. "
    "Set MATTERMOST_HTTP_HOST_ORIGIN_PROTECTION=auto to protect loopback arrivals against "
    "DNS rebinding, or =strict to validate every connection. This default changes to 'auto' in "
    "1.0.0 — set the variable explicitly (=off is a valid choice) to keep today's behavior across "
    "that upgrade."
)

_POSTURE_AUTO = (
    "HTTP Host/Origin protection active (mode=auto, allowed_hosts={hosts}, allowed_origins={origins}). "
    "Each connection is validated by the local address it arrives on: arrivals on 127.0.0.1/localhost/::1 "
    "always, other arrivals only when an allowlist is set."
)

_POSTURE_AUTO_LOOPBACK_BIND = (
    "HTTP Host/Origin protection active (mode=auto, bind={host}, allowed_hosts={hosts}, "
    "allowed_origins={origins}). The bind is loopback, so FastMCP adds {host} to the allowlist and "
    "validates Host and Origin on every connection — a reverse proxy forwarding a public Host must "
    "have it listed in MATTERMOST_HTTP_ALLOWED_HOSTS."
)

_POSTURE_STRICT = (
    "HTTP Host/Origin protection active (mode=strict, allowed_hosts={hosts}, allowed_origins={origins}). "
    "Host and Origin are validated on every connection regardless of the address it arrives on."
)

_INERT_ALLOWLIST_WARNING = (
    "MATTERMOST_HTTP_ALLOWED_HOSTS/MATTERMOST_HTTP_ALLOWED_ORIGINS are set but Host/Origin protection "
    "is off, so they have no effect. Set MATTERMOST_HTTP_HOST_ORIGIN_PROTECTION=auto or =strict to "
    "enable them."
)

_FASTMCP_PROTECTION: dict[HostOriginProtection, bool | Literal["auto"]] = {
    HostOriginProtection.OFF: False,
    HostOriginProtection.AUTO: "auto",
    HostOriginProtection.STRICT: True,
}


def normalize_host(host: str) -> str:
    """Return a bare host, matching how FastMCP normalizes a Host header or bind address.

    Args:
        host: Raw host, optionally bracketed (``[::1]``) or carrying a port (``example:8000``).

    Returns:
        Lowercased host with surrounding whitespace, IPv6 brackets, and any trailing port removed.
    """
    host = host.strip().lower()
    if not host:
        return ""
    if host.startswith("["):
        end = host.find("]")
        return host if end == -1 else host[1:end]
    if host.count(":") == 1:
        return host.rsplit(":", 1)[0]
    return host


def is_loopback_host(host: str) -> bool:
    """Return whether the bind host is a loopback address.

    Mirrors FastMCP's own classification so the warnings this module emits describe the
    posture FastMCP actually applies.

    Args:
        host: Bind host (IP literal or hostname) from ``--host`` / ``MCP_HOST``.

    Returns:
        True for 127.0.0.0/8, ::1, or the literal "localhost"; False otherwise, including
        0.0.0.0 / :: (unspecified) and any resolvable hostname, which are treated as public.
    """
    normalized = normalize_host(host)
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def apply_http_security_settings(settings: Settings) -> None:
    """Push the configured Host/Origin protection into FastMCP's global settings.

    FastMCP resolves ``host_origin_protection`` and the allowlists from ``fastmcp.settings``
    whenever the corresponding keyword arguments are None, which every entry point does by
    default. Writing them here therefore applies the posture uniformly instead of only on the
    path that happens to pass keyword arguments to ``mcp.run()``.

    Leaving ``MATTERMOST_HTTP_HOST_ORIGIN_PROTECTION`` unset touches nothing, so FastMCP's
    default (off) and an operator's own ``FASTMCP_HTTP_HOST_ORIGIN_PROTECTION`` both survive.

    Args:
        settings: Loaded application settings.
    """
    if settings.http_host_origin_protection is not None:
        fastmcp.settings.http_host_origin_protection = _FASTMCP_PROTECTION[settings.http_host_origin_protection]
    if settings.http_allowed_hosts is not None:
        fastmcp.settings.http_allowed_hosts = settings.http_allowed_hosts
    if settings.http_allowed_origins is not None:
        fastmcp.settings.http_allowed_origins = settings.http_allowed_origins


def effective_protection() -> HostOriginProtection:
    """Return the Host/Origin protection level FastMCP will actually apply.

    Returns:
        The level resolved from FastMCP's settings, which reflects both this package's
        configuration and FastMCP's own environment variables.
    """
    value = fastmcp.settings.http_host_origin_protection
    if value is True:
        return HostOriginProtection.STRICT
    if value == "auto":
        return HostOriginProtection.AUTO
    return HostOriginProtection.OFF


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


def host_origin_posture(settings: Settings, *, host: str) -> str:
    """Return an operator-facing summary of the Host/Origin protection actually in effect.

    Reports the level resolved from FastMCP's settings rather than this package's raw
    configuration, so the line stays true when FastMCP's own environment variables are used.

    Args:
        settings: Loaded application settings.
        host: Bind host for the HTTP transport.

    Returns:
        A one-line message naming the active level, the configured allowlists, and the
        rule by which individual connections are validated.
    """
    protection = effective_protection()
    if protection is HostOriginProtection.OFF:
        return _POSTURE_OFF

    hosts = repr(settings.http_allowed_hosts)
    origins = repr(settings.http_allowed_origins)
    if protection is HostOriginProtection.STRICT:
        return _POSTURE_STRICT.format(hosts=hosts, origins=origins)
    if is_loopback_host(host):
        return _POSTURE_AUTO_LOOPBACK_BIND.format(host=host, hosts=hosts, origins=origins)
    return _POSTURE_AUTO.format(hosts=hosts, origins=origins)


def inert_allowlist_warning(settings: Settings) -> str | None:
    """Return a warning when allowlists are configured but protection is off.

    Args:
        settings: Loaded application settings.

    Returns:
        A warning string when an allowlist is set while protection is off, else None.
    """
    if effective_protection() is not HostOriginProtection.OFF:
        return None
    if settings.http_allowed_hosts is None and settings.http_allowed_origins is None:
        return None
    return _INERT_ALLOWLIST_WARNING
