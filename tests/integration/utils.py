# tests/integration/utils.py
"""Utility functions for integration tests."""

import asyncio
import json
import os
import subprocess
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any


class MattermostInitError(Exception):
    """Raised when Mattermost initialization fails."""


def _unwrap_result(data: Any) -> Any:
    """Unwrap FastMCP's {"result": [...]} wrapper for list returns."""
    if isinstance(data, dict) and list(data.keys()) == ["result"]:
        return data["result"]
    return data


def to_dict(result: Any) -> Any:
    """Convert MCP tool result to dict for testing.

    FastMCP Client's result.data has a bug with dict[str, Model] fields -
    it wraps them in Root() objects losing nested content. Workaround:
    use result.structured_content which contains the raw JSON dict.

    Note: For list returns, structured_content wraps in {"result": [...]},
    so we unwrap that automatically.

    Args:
        result: CallToolResult from client.call_tool(), or raw data

    Returns:
        Dict or list representation of the result
    """
    # If it's a CallToolResult with structured_content, use that
    if hasattr(result, "structured_content") and result.structured_content is not None:
        return _unwrap_result(result.structured_content)

    # Fallback: if it has content with text, parse JSON from there
    if hasattr(result, "content") and result.content:
        for content in result.content:
            if hasattr(content, "text") and content.text:
                return _unwrap_result(json.loads(content.text))

    # Fallback for Pydantic models or lists
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if isinstance(result, list):
        return [to_dict(item) for item in result]

    return result


def setup_docker_host() -> bool:
    """Setup DOCKER_HOST from docker context if needed and check Docker availability.

    Works with any Docker runtime: Docker Desktop, Colima, Rancher Desktop, Podman, etc.
    Uses `docker context inspect` to get socket path dynamically.

    Returns:
        True if Docker is available, False otherwise
    """
    # If DOCKER_HOST set or default socket exists, use as-is
    if not os.getenv("DOCKER_HOST") and not Path("/var/run/docker.sock").exists():
        try:
            result = subprocess.run(
                ["docker", "context", "inspect"],  # noqa: S607 - intentionally use PATH
                capture_output=True,
                text=True,
                check=True,
            )
            contexts = json.loads(result.stdout)
            if contexts:
                host = contexts[0].get("Endpoints", {}).get("docker", {}).get("Host", "")
                if host:
                    os.environ["DOCKER_HOST"] = host
        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
            pass

    # Configure testcontainers for Colima (Ryuk needs socket path inside container)
    docker_host = os.getenv("DOCKER_HOST", "")
    if ".colima" in docker_host:
        os.environ.setdefault("TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE", "/var/run/docker.sock")

    try:
        import docker
        from docker.errors import DockerException

        docker.from_env().ping()
    except (ImportError, DockerException, OSError):
        return False
    else:
        return True


async def wait_for_indexing(
    check: Callable[[], Awaitable[bool]],
    timeout: float = 5.0,
    interval: float = 0.5,
) -> None:
    """Wait for search indexing to complete.

    Mattermost search indexing can take a few seconds after posting.
    This helper polls a check function until it returns True.

    Args:
        check: Async function that returns True when ready
        timeout: Maximum time to wait in seconds
        interval: Time between checks in seconds

    Raises:
        TimeoutError: If check doesn't return True within timeout
    """
    elapsed = 0.0
    while elapsed < timeout:
        if await check():
            return
        await asyncio.sleep(interval)
        elapsed += interval

    msg = f"Timed out after {timeout}s waiting for condition"
    raise TimeoutError(msg)


def make_test_name(prefix: str = "mcp-test") -> str:
    """Generate unique test resource name.

    Args:
        prefix: Name prefix for easy identification

    Returns:
        Unique name like 'mcp-test-1706400000123'
    """
    import time

    return f"{prefix}-{int(time.time() * 1000)}"


async def cleanup_channel(channel_id: str) -> None:
    """Delete a channel (best effort cleanup).

    Used by tests to clean up created channels.
    Silently ignores errors - channel may already be deleted.

    Args:
        channel_id: Mattermost channel ID to delete
    """
    import contextlib

    import httpx

    from mcp_server_mattermost.config import get_settings

    settings = get_settings()
    async with httpx.AsyncClient(
        base_url=f"{settings.url}/api/v4",
        headers={"Authorization": f"Bearer {settings.token}"},
        timeout=10.0,
    ) as client:
        with contextlib.suppress(Exception):
            await client.delete(f"/channels/{channel_id}")


async def initialize_mattermost(base_url: str) -> dict:
    """Initialize fresh Mattermost instance for testing.

    Creates admin user, team, and bot with access token.
    Used when running with Testcontainers.

    Security note: Credentials below (Admin123!) are for ephemeral
    Testcontainers instances only. These containers are destroyed
    after tests complete and are never exposed to networks.

    Args:
        base_url: Mattermost server URL

    Returns:
        Dict with url, token, team_id, admin_token keys
    """
    import httpx

    async with httpx.AsyncClient(base_url=f"{base_url}/api/v4", timeout=30.0) as client:
        # 1. Create admin user
        admin_data = {
            "email": "admin@test.local",
            "username": "admin",
            "password": "Admin123!",
        }
        resp = await client.post("/users", json=admin_data)
        if resp.status_code not in (200, 201):
            pass

        # Login as admin
        login_resp = await client.post(
            "/users/login",
            json={"login_id": "admin", "password": "Admin123!"},
        )
        if login_resp.status_code != 200:
            msg = f"Admin login failed: {login_resp.status_code} - {login_resp.text}"
            raise MattermostInitError(msg)
        admin_token = login_resp.headers.get("Token")
        if not admin_token:
            msg = "Login succeeded but no Token header in response"
            raise MattermostInitError(msg)

        # Create test team
        headers = {"Authorization": f"Bearer {admin_token}"}
        team_data = {
            "name": "mcp-test-team",
            "display_name": "MCP Test Team",
            "type": "O",
        }
        team_resp = await client.post("/teams", json=team_data, headers=headers)
        if team_resp.status_code in (200, 201):
            team = team_resp.json()
        else:
            team_resp = await client.get("/teams/name/mcp-test-team", headers=headers)
            if team_resp.status_code != 200:
                msg = f"Failed to create/get team: {team_resp.status_code} - {team_resp.text}"
                raise MattermostInitError(msg)
            team = team_resp.json()

        team_id = team["id"]

        # Create bot user
        bot_data = {
            "username": "mcp-test-bot",
            "display_name": "MCP Test Bot",
        }
        bot_resp = await client.post("/bots", json=bot_data, headers=headers)
        if bot_resp.status_code == 201:
            bot = bot_resp.json()
        else:
            bot_resp = await client.get("/bots/mcp-test-bot", headers=headers)
            if bot_resp.status_code != 200:
                msg = f"Failed to create/get bot: {bot_resp.status_code} - {bot_resp.text}"
                raise MattermostInitError(msg)
            bot = bot_resp.json()

        bot_user_id = bot["user_id"]

        # Add bot to team
        await client.post(
            f"/teams/{team_id}/members",
            json={"team_id": team_id, "user_id": bot_user_id},
            headers=headers,
        )

        # Create bot access token
        token_resp = await client.post(
            f"/users/{bot_user_id}/tokens",
            json={"description": "Integration test token"},
            headers=headers,
        )
        if token_resp.status_code not in (200, 201):
            msg = f"Failed to create bot token: {token_resp.status_code} - {token_resp.text}"
            raise MattermostInitError(msg)
        token_data = token_resp.json()
        bot_token = token_data.get("token")
        if not bot_token:
            msg = "Token response missing 'token' field"
            raise MattermostInitError(msg)

        return {
            "url": base_url,
            "token": bot_token,
            "team_id": team_id,
            "admin_token": admin_token,
        }
