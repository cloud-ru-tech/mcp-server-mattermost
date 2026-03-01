"""End-to-end test for client token flow through MattermostTokenVerifier."""

import json
import os
from unittest.mock import patch

import httpx
import pytest
import respx
from fastmcp import Client
from fastmcp.client.auth import BearerAuth

from tests.helpers import UvicornTestServer


class TestClientTokenFlow:
    @pytest.mark.asyncio
    async def test_client_token_flows_through_to_mattermost_api(self) -> None:
        """Bearer token from MCP client reaches Mattermost API via full chain.

        Chain:
            Client(auth=BearerAuth("client-token"))
            -> MattermostTokenVerifier.verify_token("client-token")
            -> GET /api/v4/users/me [mock: verify_token]
            -> AccessToken(claims={"mattermost_token": "client-token"})
            -> get_access_token() in deps.py
            -> MattermostClient(token="client-token")
            -> get_me tool -> GET /api/v4/users/me [mock: tool call]
            -> User(id="user123")
        """
        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.server import _create_mcp

        mm_url = "http://mattermost.example.com"

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

            server = UvicornTestServer(asgi_app)
            server.start()
            assert server.wait_until_ready(), "Server did not start in time"

            try:
                with respx.mock:
                    # Pass through real TCP connections to the local MCP server so that
                    # the FastMCP client can complete the MCP protocol handshake.
                    respx.route(host=server.host).pass_through()
                    # Mock both Mattermost API calls (verify_token + get_me tool).
                    # Because respx patches httpcore globally, it also intercepts
                    # httpx calls from the server thread's event loop.
                    respx.get(f"{mm_url}/api/v4/users/me").mock(return_value=httpx.Response(200, json=user_response))

                    async with Client(f"{server.url}/mcp", auth=BearerAuth("client-token")) as client:
                        result = await client.call_tool("get_me", {})
            finally:
                server.stop()
                server.join(timeout=5.0)

            get_settings.cache_clear()

        assert result is not None
        # FastMCP 3 call_tool returns a ToolResult; content[0].text is JSON-serialized.
        data = json.loads(result.content[0].text)
        assert data["id"] == "user123"
