"""Integration test: client bearer token flows through to real Mattermost API.

Uses a standalone FastMCP instance (no FileSystemProvider) to avoid
``importlib.reload()`` of tool modules, which would corrupt the
module-level ``mcp`` singleton used by other integration tests.

Does NOT touch ``get_settings`` cache or environment variables — the
standalone server's ``MattermostTokenVerifier`` picks up URL and SSL
settings from the already-cached ``get_settings()`` (populated by the
session ``mattermost_env`` fixture). The tool dependency receives an
isolated client-token settings copy so the test cannot fall back to the
session's static token.
"""

import json
from unittest.mock import patch

import pytest
from fastmcp import Client, FastMCP
from fastmcp.client.auth import BearerAuth

from mcp_server_mattermost.config import AuthMode, get_settings
from tests.helpers import UvicornTestServer


def _create_token_flow_server() -> FastMCP:
    """Create a minimal FastMCP instance with auth and only the get_me tool.

    Avoids FileSystemProvider to prevent ``importlib.reload()`` of tool
    modules that would break the module-level ``mcp`` singleton's DI.
    """
    from mcp_server_mattermost.auth import MattermostTokenVerifier
    from mcp_server_mattermost.server import app_lifespan
    from mcp_server_mattermost.tools.users import get_me

    server = FastMCP(name="TokenFlowTest", auth=MattermostTokenVerifier(), lifespan=app_lifespan)
    server.add_tool(get_me)
    return server


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
        client_token_settings = get_settings().model_copy(
            update={"auth_mode": AuthMode.CLIENT_TOKEN, "token": "unused-static-token"},
        )

        with patch("mcp_server_mattermost.deps.get_settings", return_value=client_token_settings):
            mcp_server = _create_token_flow_server()
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

            assert not server.is_alive(), "MCP HTTP server did not stop in time"

        assert result is not None
        data = json.loads(result.content[0].text)
        assert "id" in data
        assert "username" in data
