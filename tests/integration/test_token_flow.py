"""Integration test: client bearer token flows through to real Mattermost API.

Uses a standalone FastMCP instance (no FileSystemProvider) to avoid
``importlib.reload()`` of tool modules, which would corrupt the
module-level ``mcp`` singleton used by other integration tests.
"""

import json

import pytest
from fastmcp import FastMCP
from fastmcp.client.auth import BearerAuth

from tests.helpers import UvicornTestServer


def _create_token_flow_server() -> FastMCP:
    """Create a minimal FastMCP instance with auth and only the get_me tool.

    Avoids FileSystemProvider to prevent ``importlib.reload()`` of tool
    modules that would break the module-level ``mcp`` singleton's DI.
    """
    from mcp_server_mattermost.auth import MattermostTokenVerifier
    from mcp_server_mattermost.tools.users import get_me

    server = FastMCP(name="TokenFlowTest", auth=MattermostTokenVerifier())
    server.add_tool(get_me)
    return server


class TestClientTokenFlowIntegration:
    @pytest.mark.asyncio
    async def test_bearer_token_reaches_real_mattermost(self, mattermost_env, monkeypatch) -> None:
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

        # Use monkeypatch (not patch.dict) — it restores env vars on teardown
        # without the snapshot/restore semantics that can erase vars set by
        # session-scoped monkeypatch_session.
        monkeypatch.setenv("MATTERMOST_URL", mattermost_env.url)
        monkeypatch.setenv("MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS", "true")
        get_settings.cache_clear()

        try:
            mcp_server = _create_token_flow_server()
            asgi_app = mcp_server.http_app(transport="streamable-http")

            server = UvicornTestServer(asgi_app)
            server.start()
            assert server.wait_until_ready(), "MCP HTTP server did not start in time"

            try:
                from fastmcp import Client

                mcp_url = f"{server.url}/mcp"
                async with Client(mcp_url, auth=BearerAuth(mattermost_env.token)) as client:
                    result = await client.call_tool("get_me", {})
            finally:
                server.stop()
                server.join(timeout=5.0)
        finally:
            # Restore settings cache so subsequent tests (test_users, etc.)
            # get the original settings without ALLOW_HTTP_CLIENT_TOKENS.
            get_settings.cache_clear()

        # monkeypatch teardown will restore env vars; next get_settings() call
        # from a subsequent test will reconstruct from clean env.

        assert result is not None
        data = json.loads(result.content[0].text)
        assert "id" in data
        assert "username" in data
