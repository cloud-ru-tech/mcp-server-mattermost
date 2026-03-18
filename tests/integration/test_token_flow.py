"""Integration test: client bearer token flows through to real Mattermost API.

Uses a standalone FastMCP instance (no FileSystemProvider) to avoid
``importlib.reload()`` of tool modules, which would corrupt the
module-level ``mcp`` singleton used by other integration tests.
"""

import json
import os
from unittest.mock import patch

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

        # Snapshot the cached settings BEFORE we touch env/cache.
        # We must restore it afterwards so subsequent tests (test_users, etc.)
        # don't fail with ConfigurationError when get_settings() tries to
        # reconstruct Settings from a possibly-altered environment.
        original_settings = get_settings()

        with patch.dict(
            os.environ,
            {
                "MATTERMOST_URL": mattermost_env.url,
                "MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS": "true",
            },
        ):
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
                # Restore the original cached settings.  We can't just call
                # cache_clear() and let the next get_settings() reconstruct
                # from env — patch.dict may have altered os.environ state, and
                # the lru_cache would pick up the wrong values.
                get_settings.cache_clear()

        # Outside the patch.dict context, env vars are restored.
        # Re-populate the lru_cache so downstream tests get the original settings.
        # If env vars are intact this is equivalent to original_settings;
        # if not, we force it by calling get_settings() which reads the restored env.
        _repopulated = get_settings()

        # Sanity check: the repopulated settings must match the original URL.
        assert _repopulated.url == original_settings.url, (
            f"get_settings() returned url={_repopulated.url!r} after test, "
            f"expected {original_settings.url!r} — env var leak?"
        )

        assert result is not None
        data = json.loads(result.content[0].text)
        assert "id" in data
        assert "username" in data
