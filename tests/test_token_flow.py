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
            from mcp_server_mattermost.server import _create_mcp

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


class TestOAuthProxyDiscovery:
    def test_oauth_proxy_mcp_endpoint_returns_resource_metadata_challenge(self) -> None:
        """oauth_proxy mode exposes FastMCP OAuth metadata and protects /mcp."""
        import os
        from unittest.mock import patch

        from starlette.testclient import TestClient

        from mcp_server_mattermost.config import get_settings

        with patch.dict(
            os.environ,
            {
                "MATTERMOST_URL": "http://mattermost.internal",
                "MATTERMOST_AUTH_MODE": "oauth_proxy",
                "MATTERMOST_OAUTH_CLIENT_TYPE": "public",
                "MATTERMOST_OAUTH_CLIENT_ID": "mm-client",
                "MATTERMOST_OAUTH_JWT_SIGNING_KEY": "signing-key-1234567890",
                "MATTERMOST_OAUTH_MCP_PUBLIC_URL": "http://localhost:8000",
                "MATTERMOST_OAUTH_REQUIRE_CONSENT": "false",
            },
            clear=True,
        ):
            get_settings.cache_clear()
            from mcp_server_mattermost.server import _create_mcp

            app = _create_mcp().http_app(transport="streamable-http")
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/mcp")
                metadata_response = client.get("/.well-known/oauth-protected-resource/mcp")
                as_response = client.get("/.well-known/oauth-authorization-server")
            get_settings.cache_clear()

        assert response.status_code == 401
        assert (
            'resource_metadata="http://localhost:8000/.well-known/oauth-protected-resource/mcp"'
            in response.headers["www-authenticate"]
        )
        assert metadata_response.status_code == 200
        metadata = metadata_response.json()
        assert metadata["resource"] == "http://localhost:8000/mcp"
        assert metadata["authorization_servers"] == ["http://localhost:8000/"]
        assert as_response.status_code == 200
        authorization_metadata = as_response.json()
        assert authorization_metadata["authorization_endpoint"] == "http://localhost:8000/authorize"
        assert authorization_metadata["registration_endpoint"] == "http://localhost:8000/register"
        assert authorization_metadata["token_endpoint"] == "http://localhost:8000/token"
        assert authorization_metadata.get("client_id_metadata_document_supported") is not True
