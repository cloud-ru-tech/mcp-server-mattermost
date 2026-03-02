"""Integration test: client bearer token flows through to real Mattermost API."""

import json
import os
from unittest.mock import patch

import pytest
from fastmcp import Client
from fastmcp.client.auth import BearerAuth

from tests.helpers import UvicornTestServer


class TestClientTokenFlowIntegration:
    @pytest.mark.asyncio
    async def test_bearer_token_reaches_real_mattermost(self, mattermost_env) -> None:
        """Bearer token from MCP client reaches real Mattermost via full auth chain.

        Chain:
            Client(auth=BearerAuth(token))
            → HTTP transport
            → MattermostTokenVerifier.verify_token(token)
            → GET /api/v4/users/me [REAL Mattermost]
            → AccessToken(claims={"mattermost_token": token})
            → get_client() uses token from claims
            → MattermostClient(token=token)
            → get_me tool → GET /api/v4/users/me [REAL Mattermost]
            → User response
        """
        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.server import _create_mcp

        with patch.dict(
            os.environ,
            {
                "MATTERMOST_URL": mattermost_env.url,
                "MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS": "true",
            },
        ):
            get_settings.cache_clear()

            try:
                mcp_server = _create_mcp()
                asgi_app = mcp_server.http_app(transport="streamable-http")

                server = UvicornTestServer(asgi_app)
                server.start()
                assert server.wait_until_ready(), "MCP HTTP server did not start in time"

                try:
                    mcp_url = f"{server.url}/mcp"
                    async with Client(mcp_url, auth=BearerAuth(mattermost_env.token)) as client:
                        result = await client.call_tool("get_me", {})
                finally:
                    server.stop()
                    server.join(timeout=5.0)
            finally:
                get_settings.cache_clear()

        assert result is not None
        data = json.loads(result.content[0].text)
        assert "id" in data
        assert "username" in data
