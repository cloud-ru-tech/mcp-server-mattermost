"""MCP server for Mattermost integration."""

import argparse
import contextlib
import os
from importlib.metadata import PackageNotFoundError, version

from mcp_server_mattermost import constants
from mcp_server_mattermost.enums import ToolTag


try:
    __version__ = version("mcp-server-mattermost")
except PackageNotFoundError:
    __version__ = "0.5.1"

__all__ = [
    "ToolTag",
    "__version__",
    "constants",
    "main",
]


def main() -> None:
    """Run the MCP server.

    Supports both STDIO and HTTP transports via CLI args or env vars:
        mcp-server-mattermost              # STDIO (default)
        mcp-server-mattermost --http       # HTTP streaming
        MCP_TRANSPORT=http mcp-server-mattermost  # HTTP via env var

    Environment variables (used as defaults, CLI args override):
        MCP_TRANSPORT: "stdio" or "http" (default: stdio)
        MCP_HOST: HTTP host (default: 127.0.0.1)
        MCP_PORT: HTTP port (default: 8000)
    """
    # Get env var defaults
    env_transport = os.getenv("MCP_TRANSPORT", "stdio")
    env_host = os.getenv("MCP_HOST", "127.0.0.1")
    try:
        env_port = int(os.getenv("MCP_PORT", "8000"))
    except ValueError as e:
        port_value = os.getenv("MCP_PORT")
        msg = f"Error: MCP_PORT must be an integer, got '{port_value}'"
        raise SystemExit(msg) from e

    parser = argparse.ArgumentParser(
        prog="mcp-server-mattermost",
        description="MCP server for Mattermost team collaboration platform",
    )
    parser.add_argument(
        "--http",
        action="store_true",
        default=(env_transport == "http"),
        help="Run with HTTP transport instead of STDIO",
    )
    parser.add_argument(
        "--host",
        default=env_host,
        help=f"HTTP host (default: {env_host})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=env_port,
        help=f"HTTP port (default: {env_port})",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    args = parser.parse_args()

    if not args.http:
        from .server import mcp  # noqa: PLC0415

        with contextlib.suppress(KeyboardInterrupt):
            mcp.run(transport="stdio")
        return

    # HTTP transport: enforce transport security before importing/binding the server.
    from mcp_server_mattermost.config import get_settings  # noqa: PLC0415
    from mcp_server_mattermost.exceptions import ConfigurationError  # noqa: PLC0415
    from mcp_server_mattermost.http_security import (  # noqa: PLC0415
        enforce_unauthenticated_http_policy,
        resolve_host_origin_kwargs,
    )
    from mcp_server_mattermost.logging import logger, setup_logging  # noqa: PLC0415

    settings = get_settings()
    try:
        warning = enforce_unauthenticated_http_policy(settings, transport="http", host=args.host)
    except ConfigurationError as exc:
        raise SystemExit(str(exc)) from exc
    if warning:
        setup_logging(settings.log_level, settings.log_format)
        logger.warning(warning)

    from .server import mcp  # noqa: PLC0415

    with contextlib.suppress(KeyboardInterrupt):
        mcp.run(
            transport="http",
            host=args.host,
            port=args.port,
            uvicorn_config={"ws": "wsproto"},
            **resolve_host_origin_kwargs(settings),
        )
