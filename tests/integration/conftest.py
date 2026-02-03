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
import os
from dataclasses import dataclass

import pytest
from _pytest.monkeypatch import MonkeyPatch
from fastmcp import Client

from mcp_server_mattermost.config import get_settings
from mcp_server_mattermost.server import mcp

from .utils import cleanup_channel, make_test_name, setup_docker_host, to_dict


# Setup DOCKER_HOST for Testcontainers BEFORE any Docker operations
# Must happen at module level, before pytest creates any fixtures
_DOCKER_AVAILABLE = setup_docker_host()


@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop for async fixtures.

    Replaces deprecated asyncio.get_event_loop() calls.
    Required for session-scoped async operations with pytest-asyncio.
    """
    import asyncio

    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


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


@pytest.fixture(scope="session")
def mattermost_env(monkeypatch_session, event_loop) -> TestEnvironment:
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

        with httpx.Client(
            base_url=f"{url}/api/v4",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
            follow_redirects=True,
        ) as client:
            teams = client.get("/users/me/teams").json()
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
                env_data = event_loop.run_until_complete(initialize_mattermost(mm.get_base_url()))

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


@pytest.fixture
async def mcp_client(mattermost_env):
    """MCP client connected to server via in-memory transport.

    Tests the full MCP stack:
    - MCP protocol (tools/list, tools/call)
    - Pydantic validation
    - FastMCP routing
    - MattermostClient HTTP logic
    - Real Mattermost API
    """
    async with Client(mcp) as client:
        yield client


@pytest.fixture(scope="session")
def session_mcp_client_sync(mattermost_env, event_loop):
    """Session-scoped MCP client for setup operations (sync wrapper).

    Uses a more robust pattern that properly handles exceptions during cleanup.
    """
    import warnings

    client = None
    cleanup_exc = None

    async def create_and_track():
        nonlocal client
        client = Client(mcp)
        await client.__aenter__()
        return client

    try:
        event_loop.run_until_complete(create_and_track())
        yield client
    finally:
        if client is not None:

            async def cleanup():
                nonlocal cleanup_exc
                try:
                    await client.__aexit__(None, None, None)
                except Exception as e:  # noqa: BLE001 - need to catch all to warn and continue
                    cleanup_exc = e

            event_loop.run_until_complete(cleanup())

            if cleanup_exc is not None:
                warnings.warn(f"Error during MCP client cleanup: {cleanup_exc}", stacklevel=2)


@pytest.fixture(scope="session")
def bot_user(session_mcp_client_sync, mattermost_env, event_loop):
    """Bot user info (reused across all tests)."""

    async def get_bot():
        result = await session_mcp_client_sync.call_tool("get_me", {})
        return to_dict(result)

    return event_loop.run_until_complete(get_bot())


@pytest.fixture(scope="session")
def team(session_mcp_client_sync, mattermost_env, event_loop):
    """Test team info (reused across all tests)."""

    async def get_team():
        result = await session_mcp_client_sync.call_tool(
            "get_team",
            {"team_id": mattermost_env.team_id},
        )
        return to_dict(result)

    return event_loop.run_until_complete(get_team())


@pytest.fixture
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


@pytest.fixture
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


@pytest.fixture(scope="session", autouse=True)
def cleanup_orphaned_resources(session_mcp_client_sync, mattermost_env, event_loop):
    """Clean up leftover test resources before and after tests."""

    async def cleanup():
        result = await session_mcp_client_sync.call_tool(
            "list_channels",
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

    event_loop.run_until_complete(cleanup())

    yield

    event_loop.run_until_complete(cleanup())
