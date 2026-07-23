# tests/integration/conftest.py
"""Pytest fixtures for integration tests.

Fixtures provide:
- mattermost_env: Test environment (Testcontainers or external server)
- mcp_client: FastMCP client for MCP protocol testing
- session_mcp_client: Session-scoped client for setup
- bot_user: Current bot user info
- team: Test team info
- test_channel: Fresh channel per test (with cleanup)
- test_post: Fresh post per test (with cleanup)
"""

import contextlib
import inspect
import os
from dataclasses import dataclass
from pathlib import Path

import pytest
import pytest_asyncio
from _pytest.monkeypatch import MonkeyPatch
from fastmcp import Client

from mcp_server_mattermost.config import get_settings

from .utils import cleanup_channel, make_test_name, setup_docker_host, to_dict


# Setup DOCKER_HOST for Testcontainers BEFORE any Docker operations
# Must happen at module level, before pytest creates any fixtures
_DOCKER_AVAILABLE = setup_docker_host()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Run async integration tests on the server's session-scoped event loop."""
    integration_dir = Path(__file__).parent
    session_loop = pytest.mark.asyncio(loop_scope="session")
    for item in items:
        if item.path.is_relative_to(integration_dir) and inspect.iscoroutinefunction(item.obj):
            item.add_marker(session_loop, append=False)


@dataclass
class TestEnvironment:
    """Test environment configuration."""

    url: str
    token: str
    team_id: str
    admin_token: str | None = None


@pytest.fixture(scope="session")
def monkeypatch_session():
    """Session-scoped monkeypatch for environment variables."""
    mp = MonkeyPatch()
    yield mp
    mp.undo()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def mattermost_env(monkeypatch_session) -> TestEnvironment:
    """Configure test environment: external server or Testcontainers.

    If MATTERMOST_URL and MATTERMOST_TOKEN are set, uses external server.
    Otherwise, starts Mattermost via Testcontainers (requires Docker).
    """
    url = os.getenv("MATTERMOST_URL")
    token = os.getenv("MATTERMOST_TOKEN")

    if url and token:
        import httpx

        # Remove trailing slash to avoid double-slash in URLs
        url = url.rstrip("/")

        async with httpx.AsyncClient(
            base_url=f"{url}/api/v4",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
            follow_redirects=True,
        ) as client:
            teams = (await client.get("/users/me/teams")).json()
            team_id = teams[0]["id"] if teams else ""

        yield TestEnvironment(url=url, token=token, team_id=team_id)
    else:
        # Testcontainers mode - check Docker availability
        if not _DOCKER_AVAILABLE:
            pytest.skip("Docker not available for Testcontainers")

        from testcontainers.postgres import PostgresContainer

        from .containers import MattermostContainer
        from .utils import initialize_mattermost

        postgres = PostgresContainer("postgres:15")
        postgres.start()

        try:
            # Get PostgreSQL container's IP in Docker network for inter-container communication
            # Mattermost runs inside Docker and needs to connect via Docker network, not host
            pg_container = postgres.get_wrapped_container()
            pg_container.reload()  # Refresh to get network info
            pg_ip = pg_container.attrs["NetworkSettings"]["Networks"]["bridge"]["IPAddress"]

            postgres_dsn = (
                f"postgres://{postgres.username}:{postgres.password}"
                f"@{pg_ip}:5432"  # Use internal Docker IP and port
                f"/{postgres.dbname}?sslmode=disable"
            )

            mm = MattermostContainer()
            mm.configure(postgres_dsn)
            mm.start()

            try:
                env_data = await initialize_mattermost(mm.get_base_url())

                monkeypatch_session.setenv("MATTERMOST_URL", env_data["url"])
                monkeypatch_session.setenv("MATTERMOST_TOKEN", env_data["token"])

                get_settings.cache_clear()

                yield TestEnvironment(
                    url=env_data["url"],
                    token=env_data["token"],
                    team_id=env_data["team_id"],
                    admin_token=env_data["admin_token"],
                )
            finally:
                mm.stop()
        finally:
            postgres.stop()


@pytest_asyncio.fixture(loop_scope="session")
async def mcp_client(mattermost_env):
    """MCP client connected to server via in-memory transport.

    Tests the full MCP stack:
    - MCP protocol (tools/list, tools/call)
    - Pydantic validation
    - FastMCP routing
    - MattermostClient HTTP logic
    - Real Mattermost API
    """
    from mcp_server_mattermost.server import mcp

    async with Client(mcp) as client:
        yield client


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def session_mcp_client(mattermost_env):
    """Session-scoped MCP client for setup and cleanup operations."""
    from mcp_server_mattermost.server import mcp

    async with Client(mcp) as client:
        yield client


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def bot_user(session_mcp_client, mattermost_env):
    """Bot user info (reused across all tests)."""
    result = await session_mcp_client.call_tool("get_me", {})
    return to_dict(result)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def team(session_mcp_client, mattermost_env):
    """Test team info (reused across all tests)."""
    result = await session_mcp_client.call_tool(
        "get_team",
        {"team_id": mattermost_env.team_id},
    )
    return to_dict(result)


@pytest_asyncio.fixture(loop_scope="session")
async def test_channel(mcp_client, team):
    """Fresh channel for each test with cleanup."""
    name = make_test_name()
    result = await mcp_client.call_tool(
        "create_channel",
        {
            "team_id": team["id"],
            "name": name,
            "display_name": f"Test {name}",
            "channel_type": "O",
        },
    )
    channel = to_dict(result)

    yield channel

    await cleanup_channel(channel["id"])


@pytest_asyncio.fixture(loop_scope="session")
async def test_post(mcp_client, test_channel):
    """Fresh message for each test with cleanup."""
    result = await mcp_client.call_tool(
        "post_message",
        {
            "channel_id": test_channel["id"],
            "message": "[MCP-TEST] Test message",
        },
    )
    post = to_dict(result)

    yield post

    with contextlib.suppress(Exception):
        await mcp_client.call_tool("delete_message", {"post_id": post["id"]})


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def cleanup_orphaned_resources(session_mcp_client, mattermost_env):
    """Clean up leftover test resources before and after tests."""

    async def cleanup():
        result = await session_mcp_client.call_tool(
            "list_public_channels",
            {"team_id": mattermost_env.team_id},
        )
        channels = to_dict(result)

        import httpx

        settings = get_settings()
        async with httpx.AsyncClient(
            base_url=f"{settings.url}/api/v4",
            headers={"Authorization": f"Bearer {settings.token}"},
            timeout=10.0,
        ) as client:
            for channel in channels:
                if channel["name"].startswith("mcp-test-"):
                    with contextlib.suppress(Exception):
                        await client.delete(f"/channels/{channel['id']}")

    await cleanup()

    yield

    await cleanup()
