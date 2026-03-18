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
    __version__ = "0.3.0"

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

    from .server import mcp  # noqa: PLC0415

    with contextlib.suppress(KeyboardInterrupt):
        if args.http:
            mcp.run(transport="http", host=args.host, port=args.port, uvicorn_config={"ws": "wsproto"})
        else:
            mcp.run(transport="stdio")
