"""End-to-end test for client token flow through MattermostTokenVerifier."""

import asyncio
import contextlib
import json
import os
import socket
import threading
import time
from unittest.mock import patch

import httpx
import pytest
import respx
import uvicorn
from fastmcp import Client
from fastmcp.client.auth import BearerAuth


class _ServerThread(threading.Thread):
    """Runs a uvicorn server in a background thread with its own event loop.

    The server thread has a separate event loop from the test loop.  respx
    patches httpcore at the class level, so it intercepts httpx calls from
    *both* event loops.  The test uses ``respx.route(host=...).pass_through()``
    for the local MCP server so the real TCP connection is used for MCP
    protocol traffic, while Mattermost API calls are intercepted and mocked.
    """

    def __init__(self, app: object, host: str, port: int) -> None:
        super().__init__(daemon=True)
        self._app = app
        self._host = host
        self._port = port
        self._started = threading.Event()
        self._server: uvicorn.Server | None = None

    def run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        config = uvicorn.Config(self._app, host=self._host, port=self._port, log_level="critical")
        self._server = uvicorn.Server(config)

        async def _serve() -> None:
            await self._server.serve()  # type: ignore[union-attr]

        async def _watch_and_notify() -> None:
            # Poll until uvicorn signals startup; asyncio.Event cannot be used
            # here because the flag is set by a different thread (the watcher
            # itself), and we simply poll the thread-safe uvicorn.Server.started
            # attribute.
            while not (self._server and self._server.started):  # noqa: ASYNC110
                await asyncio.sleep(0.02)
            self._started.set()

        async def _main() -> None:
            await asyncio.gather(_serve(), _watch_and_notify())

        loop.run_until_complete(_main())

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True

    def wait_until_ready(self, timeout: float = 10.0) -> bool:
        """Wait until the server TCP listener is accepting connections.

        Args:
            timeout: Maximum seconds to wait.

        Returns:
            True if ready within the timeout, False otherwise.
        """
        if not self._started.wait(timeout):
            return False
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            connected = False
            with contextlib.suppress(OSError), socket.create_connection((self._host, self._port), timeout=0.1):
                connected = True
            if connected:
                return True
            time.sleep(0.05)
        return False


class TestClientTokenFlow:
    @pytest.mark.asyncio
    async def test_client_token_flows_through_to_mattermost_api(self) -> None:
        """Bearer token from MCP client reaches Mattermost API via full chain.

        Chain:
            Client(auth=BearerAuth("client-token"))
            → MattermostTokenVerifier.verify_token("client-token")
            → GET /api/v4/users/me [mock: verify_token]
            → AccessToken(claims={"mattermost_token": "client-token"})
            → get_access_token() in deps.py
            → MattermostClient(token="client-token")
            → get_me tool → GET /api/v4/users/me [mock: tool call]
            → User(id="user123")
        """
        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.server import _create_mcp

        mm_url = "http://mattermost.example.com"
        server_host = "127.0.0.1"
        with socket.socket() as _sock:
            _sock.bind(("", 0))
            server_port = _sock.getsockname()[1]

        with patch.dict(
            os.environ,
            {
                "MATTERMOST_URL": mm_url,
                "MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS": "true",
            },
            clear=True,
        ):
            get_settings.cache_clear()

            mcp = _create_mcp()
            asgi_app = mcp.http_app(transport="streamable-http")

            # Full user response satisfying the User Pydantic model's required fields.
            user_response = {
                "id": "user123",
                "username": "alice",
                "email": "alice@example.com",
                "first_name": "Alice",
                "last_name": "Smith",
                "nickname": "",
                "delete_at": 0,
                "auth_service": "",
                "roles": "system_user",
                "locale": "en",
            }

            server_thread = _ServerThread(asgi_app, server_host, server_port)
            server_thread.start()
            assert server_thread.wait_until_ready(), "Server did not start in time"

            try:
                with respx.mock:
                    # Pass through real TCP connections to the local MCP server so that
                    # the FastMCP client can complete the MCP protocol handshake.
                    respx.route(host=server_host).pass_through()
                    # Mock both Mattermost API calls (verify_token + get_me tool).
                    # Because respx patches httpcore globally, it also intercepts
                    # httpx calls from the server thread's event loop.
                    respx.get(f"{mm_url}/api/v4/users/me").mock(
                        return_value=httpx.Response(200, json=user_response)
                    )

                    mcp_url = f"http://{server_host}:{server_port}/mcp"
                    async with Client(mcp_url, auth=BearerAuth("client-token")) as client:
                        result = await client.call_tool("get_me", {})
            finally:
                server_thread.stop()
                server_thread.join(timeout=5.0)

            get_settings.cache_clear()

        assert result is not None
        # FastMCP 3 call_tool returns a ToolResult; content[0].text is JSON-serialized.
        data = json.loads(result.content[0].text)
        assert data["id"] == "user123"
