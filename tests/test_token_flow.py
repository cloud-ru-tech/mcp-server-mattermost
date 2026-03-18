"""End-to-end test for client token flow through MattermostTokenVerifier."""

import json
import os
from typing import Any
from unittest.mock import patch

import httpx
import pytest
import respx
from asgi_lifespan import LifespanManager
from fastmcp import Client
from fastmcp.client.auth import BearerAuth
from fastmcp.client.transports.http import StreamableHttpTransport


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

            async with LifespanManager(asgi_app):

                def asgi_httpx_factory(
                    headers: dict[str, str] | None = None,
                    timeout: httpx.Timeout | None = None,
                    auth: httpx.Auth | None = None,
                    **kwargs: Any,
                ) -> httpx.AsyncClient:
                    """Create httpx client with ASGI transport for in-memory testing."""
                    return httpx.AsyncClient(
                        transport=httpx.ASGITransport(app=asgi_app),
                        headers=headers,
                        timeout=timeout,
                        auth=auth,
                        **kwargs,
                    )

                transport = StreamableHttpTransport(
                    url="http://localhost/mcp",
                    auth=BearerAuth("client-token"),
                    httpx_client_factory=asgi_httpx_factory,
                )

                with respx.mock:
                    # Mock Mattermost API calls (verify_token + get_me tool).
                    respx.get(f"{mm_url}/api/v4/users/me").mock(
                        return_value=httpx.Response(200, json=user_response),
                    )

                    async with Client(transport) as client:
                        result = await client.call_tool("get_me", {})

            get_settings.cache_clear()

        assert result is not None
        # FastMCP 3 call_tool returns a ToolResult; content[0].text is JSON-serialized.
        data = json.loads(result.content[0].text)
        assert data["id"] == "user123"
