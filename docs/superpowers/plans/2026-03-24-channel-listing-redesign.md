# Channel Listing Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `list_channels` into `list_public_channels` (discovery) and `list_my_channels` (user's joined channels with type filter) to fix GitHub Issue #3.

**Architecture:** Rename existing tool/client method for public channels, add new tool/client method for user-scoped channels. Client-side filtering by channel type in the tool layer. No pagination on the new endpoint (Mattermost API limitation).

**Tech Stack:** Python 3.10+, FastMCP 3, Pydantic, pytest + respx + pytest-asyncio

**Spec:** `docs/superpowers/specs/2026-03-23-channel-listing-redesign-design.md`

---

### Task 1: AGENTS.md — Clarify Co-Authored-By restriction

**Files:**
- Modify: `AGENTS.md:232`

- [ ] **Step 1: Update the Co-Authored-By line**

In `AGENTS.md`, find:
```
Do not include `Co-Authored-By:` trailers in commit messages.
```

Replace with:
```
Do not include `Co-Authored-By:` trailers for AI agents in commit messages.
Human contributor co-authorship trailers are welcome.
```

- [ ] **Step 2: Commit**

```bash
git add AGENTS.md
git commit -m "docs: clarify Co-Authored-By restriction applies to AI agents only"
```

---

### Task 2: Client layer — Rename get_channels and add get_my_channels

**Files:**
- Modify: `src/mcp_server_mattermost/client.py:428-448`

- [ ] **Step 1: Write the failing test for get_public_channels rename**

In `tests/test_client.py`, find `test_get_channels` (line 827). Rename it and update the mock URL and method call:

```python
async def test_get_public_channels(self, mock_settings):
    """get_public_channels() should return team's public channels."""
    from mcp_server_mattermost.config import get_settings

    settings = get_settings()
    client = MattermostClient(settings)

    route = respx.get("https://test.mattermost.com/api/v4/teams/team123/channels").mock(
        return_value=httpx.Response(200, json=[{"id": "ch123", "name": "general"}]),
    )

    async with client.lifespan():
        result = await client.get_public_channels("team123", page=0, per_page=60)

    assert result == [{"id": "ch123", "name": "general"}]
    assert route.calls[0].request.url.params["page"] == "0"
```

- [ ] **Step 2: Write the failing test for get_my_channels**

Add a new test in the same class `TestMattermostClientChannelsAPI`:

```python
@pytest.mark.asyncio
@respx.mock
async def test_get_my_channels(self, mock_settings):
    """get_my_channels() should return user's channels in a team."""
    from mcp_server_mattermost.config import get_settings

    settings = get_settings()
    client = MattermostClient(settings)

    route = respx.get("https://test.mattermost.com/api/v4/users/me/teams/team123/channels").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": "ch1", "name": "general", "type": "O"},
                {"id": "ch2", "name": "secret", "type": "P"},
            ],
        ),
    )

    async with client.lifespan():
        result = await client.get_my_channels("team123")

    assert len(result) == 2
    assert result[0]["id"] == "ch1"
    assert result[1]["type"] == "P"
    assert route.called
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_client.py::TestMattermostClientChannelsAPI::test_get_public_channels tests/test_client.py::TestMattermostClientChannelsAPI::test_get_my_channels -v`

Expected: FAIL — `get_public_channels` and `get_my_channels` not found on client.

- [ ] **Step 4: Implement — rename get_channels and add get_my_channels**

In `src/mcp_server_mattermost/client.py`, rename `get_channels` (line 428) to `get_public_channels` and update its docstring:

```python
async def get_public_channels(
    self,
    team_id: str,
    page: int = 0,
    per_page: int = 60,
) -> list[dict[str, Any]]:
    """Get public channels in a team for discovery.

    Returns all public channels, including ones the user hasn't joined.
    Results are paginated. Use page/per_page to retrieve all channels.

    Args:
        team_id: Team identifier
        page: Page number (0-indexed)
        per_page: Results per page (max 200)

    Returns:
        List of channel objects
    """
    result = await self.get(
        f"/teams/{team_id}/channels",
        params={"page": page, "per_page": per_page},
    )
    return result if isinstance(result, list) else []
```

Add `get_my_channels` right after `get_public_channels`:

```python
async def get_my_channels(self, team_id: str) -> list[dict[str, Any]]:
    """Get all channels the authenticated user belongs to in a team.

    Returns public, private, DM, and group channels.
    No pagination — API returns all channels at once.

    Args:
        team_id: Team identifier

    Returns:
        List of channel objects
    """
    result = await self.get(f"/users/me/teams/{team_id}/channels")
    return result if isinstance(result, list) else []
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_client.py::TestMattermostClientChannelsAPI::test_get_public_channels tests/test_client.py::TestMattermostClientChannelsAPI::test_get_my_channels -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/mcp_server_mattermost/client.py tests/test_client.py
git commit -m "feat: rename get_channels to get_public_channels, add get_my_channels

Co-authored-by: Daniil Svetlov <svetlov@bpcbt.com>"
```

---

### Task 3: Tool layer — Rename list_channels and add list_my_channels

**Files:**
- Modify: `src/mcp_server_mattermost/tools/channels.py:1-36`

- [ ] **Step 1: Write the failing test for list_public_channels rename**

In `tests/test_tools/test_channels.py`, rename `TestListChannels` class (line 60) to `TestListPublicChannels`. Update the test inside:

```python
class TestListPublicChannels:
    """Tests for list_public_channels tool."""

    async def test_list_public_channels_returns_channels(self, mock_client: AsyncMock) -> None:
        """Test successful channel listing returns Channel models."""
        mock_client.get_public_channels.return_value = [make_channel_data()]

        result = await channels.list_public_channels(
            team_id="tm1234567890123456789012",
            page=0,
            per_page=60,
            client=mock_client,
        )

        assert len(result) == 1
        assert isinstance(result[0], Channel)
        assert result[0].id == "ch1234567890123456789012"
        assert result[0].name == "general"
        mock_client.get_public_channels.assert_called_once_with(
            team_id="tm1234567890123456789012",
            page=0,
            per_page=60,
        )
```

- [ ] **Step 2: Write the failing tests for list_my_channels**

Add a new test class in `tests/test_tools/test_channels.py`:

```python
class TestListMyChannels:
    """Tests for list_my_channels tool."""

    async def test_list_my_channels_returns_all_types(self, mock_client: AsyncMock) -> None:
        """Test returns all channel types when channel_types is None."""
        mock_client.get_my_channels.return_value = [
            make_channel_data(channel_id="ch_o", name="public", type="O"),
            make_channel_data(channel_id="ch_p", name="private", type="P"),
            make_channel_data(channel_id="ch_d", name="dm", type="D"),
            make_channel_data(channel_id="ch_g", name="group", type="G"),
        ]

        result = await channels.list_my_channels(
            team_id="tm1234567890123456789012",
            client=mock_client,
        )

        assert len(result) == 4
        assert all(isinstance(ch, Channel) for ch in result)
        mock_client.get_my_channels.assert_called_once_with(team_id="tm1234567890123456789012")

    async def test_list_my_channels_filters_by_type(self, mock_client: AsyncMock) -> None:
        """Test filters channels when channel_types is specified."""
        mock_client.get_my_channels.return_value = [
            make_channel_data(channel_id="ch_o", name="public", type="O"),
            make_channel_data(channel_id="ch_p", name="private", type="P"),
            make_channel_data(channel_id="ch_d", name="dm", type="D"),
            make_channel_data(channel_id="ch_g", name="group", type="G"),
        ]

        result = await channels.list_my_channels(
            team_id="tm1234567890123456789012",
            channel_types=["O", "P"],
            client=mock_client,
        )

        assert len(result) == 2
        types = {ch.type for ch in result}
        assert types == {"O", "P"}

    async def test_list_my_channels_empty_result(self, mock_client: AsyncMock) -> None:
        """Test empty list when no channels."""
        mock_client.get_my_channels.return_value = []

        result = await channels.list_my_channels(
            team_id="tm1234567890123456789012",
            client=mock_client,
        )

        assert result == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_tools/test_channels.py::TestListPublicChannels tests/test_tools/test_channels.py::TestListMyChannels -v`

Expected: FAIL — `list_public_channels` and `list_my_channels` not found.

- [ ] **Step 4: Implement — rename list_channels and add list_my_channels**

In `src/mcp_server_mattermost/tools/channels.py`, add `Literal` to the typing import (line 3):

```python
from typing import Annotated, Literal
```

Rename `list_channels` function (line 20) to `list_public_channels`. Keep the existing `@tool(...)` decorator unchanged. Update docstring and client call:

```python
@tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.CHANNEL},
    meta={"capability": Capability.READ},
)
async def list_public_channels(
    team_id: TeamId,
    page: Annotated[int, Field(ge=0, description="Page number (0-indexed)")] = 0,
    per_page: Annotated[int, Field(ge=1, le=200, description="Results per page")] = 60,
    client: MattermostClient = Depends(get_client),  # noqa: B008
) -> list[Channel]:
    """List public channels available in a team.

    Returns all public channels for discovery, including ones you haven't joined.
    Results are paginated. Use page/per_page to retrieve all channels.
    Useful for finding channels to join.
    For channels you are already a member of (including private), use list_my_channels.
    """
    data = await client.get_public_channels(
        team_id=team_id,
        page=page,
        per_page=per_page,
    )
    return [Channel(**item) for item in data]
```

Add `list_my_channels` right after `list_public_channels` (before `get_channel`):

```python
@tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.CHANNEL},
    meta={"capability": Capability.READ},
)
async def list_my_channels(
    team_id: TeamId,
    channel_types: Annotated[
        list[Literal["O", "P", "D", "G"]] | None,
        Field(
            min_length=1,
            description=(
                "Channel types to include: O=public, P=private, "
                "D=direct message, G=group message. "
                "Omit to return all types."
            ),
        ),
    ] = None,
    client: MattermostClient = Depends(get_client),  # noqa: B008
) -> list[Channel]:
    """List channels you are a member of in a team.

    Returns your channels filtered by type. By default returns all types.
    Use channel_types to narrow results: ["O", "P"] for workspace channels
    without DMs, or ["D"] for direct messages only.
    For discovering public channels you haven't joined yet, use list_public_channels.
    """
    data = await client.get_my_channels(team_id=team_id)
    if channel_types is not None:
        data = [ch for ch in data if ch.get("type") in channel_types]
    return [Channel(**item) for item in data]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_tools/test_channels.py::TestListPublicChannels tests/test_tools/test_channels.py::TestListMyChannels -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/mcp_server_mattermost/tools/channels.py tests/test_tools/test_channels.py
git commit -m "feat: rename list_channels to list_public_channels, add list_my_channels tool

Co-authored-by: Daniil Svetlov <svetlov@bpcbt.com>"
```

---

### Task 4: Fix test fixtures and assertions

**Files:**
- Modify: `tests/test_tools/conftest.py:20,45`
- Modify: `tests/test_tools/test_channels.py:232-237` (error handling test)
- Modify: `tests/test_tools/test_tool_tags.py:9,84`
- Modify: `tests/test_capability_meta.py:12,183`
- Modify: `tests/test_server.py:65`

- [ ] **Step 1: Update mock fixtures in conftest.py**

In `tests/test_tools/conftest.py`:

Line 20 — rename `get_channels` to `get_public_channels`:
```python
client.get_public_channels.side_effect = AuthenticationError()
```

Line 45 — rename `get_channels` to `get_public_channels`:
```python
client.get_public_channels.side_effect = RateLimitError(retry_after=30)
```

- [ ] **Step 2: Update error handling test**

In `tests/test_tools/test_channels.py`, find `test_list_channels_auth_error` (line 232). Update:

```python
async def test_list_public_channels_auth_error(self, mock_client_auth_error: AsyncMock) -> None:
    """Test authentication error propagation."""
    with pytest.raises(AuthenticationError):
        await channels.list_public_channels(
            team_id="tm1234567890123456789012",
            client=mock_client_auth_error,
        )
```

- [ ] **Step 3: Update tool_tags test**

In `tests/test_tools/test_tool_tags.py`:

Line 9 — change `"list_channels"` to `"list_public_channels"` in the `_TOOL_TO_MODULE` dict. Also add `"list_my_channels"` to the same channels tool tuple.

Line 84 — change `== 36` to `== 37`.

- [ ] **Step 4: Update capability_meta test**

In `tests/test_capability_meta.py`:

Line 12 — change `"list_channels": Capability.READ` to `"list_public_channels": Capability.READ`. Add `"list_my_channels": Capability.READ` to the dict.

Line 183 — change `== 36` to `== 37`.

Also find the `test_capability_distribution` test (around line 190) and update the READ count assertion from `== 19` to `== 20`.

- [ ] **Step 5: Update server test**

In `tests/test_server.py`:

Line 65 — change `== 36` to `== 37` and update the message string.

- [ ] **Step 6: Run full test suite**

Run: `uv run pytest tests/ -v --ignore=tests/integration`

Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add tests/test_tools/conftest.py tests/test_tools/test_channels.py tests/test_tools/test_tool_tags.py tests/test_capability_meta.py tests/test_server.py
git commit -m "test: update fixtures and assertions for channel listing rename"
```

---

### Task 5: Lint and type check

**Files:** All modified source files

- [ ] **Step 1: Run ruff check**

Run: `uv run ruff check src tests`

Expected: No errors. If any, fix them.

- [ ] **Step 2: Run ruff format**

Run: `uv run ruff format src tests`

Expected: No changes (or auto-formatted).

- [ ] **Step 3: Run mypy**

Run: `uv run mypy src`

Expected: No errors. If `get_my_channels` or `list_my_channels` has type issues, fix them.

- [ ] **Step 4: Run full unit tests one more time**

Run: `uv run pytest tests/ -v --ignore=tests/integration`

Expected: ALL PASS

- [ ] **Step 5: Commit if any fixes were needed**

```bash
git add -u
git commit -m "fix: lint and type check fixes for channel listing redesign"
```

---

### Task 6: Documentation updates

**Files:**
- Modify: `docs/tools/channels.md:7-43`
- Modify: `docs/tools/index.md:3,9,28`
- Modify: `docs/building-agents.md`
- Modify: `README.md`
- Modify: `tests/integration/README.md`

- [ ] **Step 1: Update docs/tools/channels.md**

Replace the `## list_channels` section (lines 7-43) with `## list_public_channels`:

```markdown
## list_public_channels

List public channels available in a team.

Returns all public channels for discovery, including ones you haven't joined.
Results are paginated. Use page/per_page to retrieve all channels.
Useful for finding channels to join.
For channels you are already a member of (including private), use list_my_channels.

### Example prompts

- "What public channels are available?"
- "Show me channels I can join"
- "List public channels"

### Annotations

| Hint | Value |
|------|-------|
| `readOnlyHint` | true |
| `idempotentHint` | true |
| `capability` | read |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `team_id` | string | ✓ | — | Team ID (26-character alphanumeric) |
| `page` | integer | — | 0 | Page number (0-indexed) |
| `per_page` | integer | — | 60 | Results per page (1-200) |

### Returns

Array of channel objects with `id`, `name`, `display_name`, `type`, `purpose`.

### Mattermost API

[GET /api/v4/teams/{team_id}/channels](https://api.mattermost.com/#tag/channels/operation/GetPublicChannelsForTeam)
```

Add a new `## list_my_channels` section right after:

```markdown
---

## list_my_channels

List channels you are a member of in a team.

Returns your channels filtered by type. By default returns all types.
Use channel_types to narrow results: ["O", "P"] for workspace channels
without DMs, or ["D"] for direct messages only.
For discovering public channels you haven't joined yet, use list_public_channels.

### Example prompts

- "Show me my channels"
- "What channels am I in?"
- "List my private channels"

### Annotations

| Hint | Value |
|------|-------|
| `readOnlyHint` | true |
| `idempotentHint` | true |
| `capability` | read |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `team_id` | string | ✓ | — | Team ID (26-character alphanumeric) |
| `channel_types` | array of strings | — | null (all types) | Channel types to include: O, P, D, G (min 1 item) |

### Returns

Array of channel objects with `id`, `name`, `display_name`, `type`, `purpose`.

### Mattermost API

[GET /api/v4/users/{user_id}/teams/{team_id}/channels](https://api.mattermost.com/#tag/channels/operation/GetChannelsForTeamForUser)
```

- [ ] **Step 2: Update docs/tools/index.md**

Line 3: Change `36 tools` to `37 tools`.

Line 9: Change `9` to `10` in the Channels row.

Lines 28-29: Replace `list_channels` row with two rows:
```markdown
| `list_public_channels` | read | List public channels in a team |
| `list_my_channels` | read | List your joined channels (with type filter) |
```

- [ ] **Step 3: Update docs/building-agents.md**

Replace all occurrences of `list_channels` with `list_public_channels` in examples. Check lines around the annotations table, capabilities table, and JSON example.

- [ ] **Step 4: Update README.md**

Replace `list_channels` with `list_public_channels` in the tool table.

- [ ] **Step 5: Update tests/integration/README.md**

Update the code example: `"list_channels"` → `"list_public_channels"`.

Update checklists: rename `list_channels` entries to `list_public_channels`, add `list_my_channels` entries to the Happy Path section.

- [ ] **Step 6: Update AGENTS.md**

Replace `list_channels` with `list_public_channels` in the integration test code example and any tool description examples.

- [ ] **Step 7: Commit**

```bash
git add docs/ README.md AGENTS.md tests/integration/README.md
git commit -m "docs: update documentation for channel listing redesign"
```

---

### Task 7: CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Add entry to CHANGELOG.md**

Add a new section at the top (under the existing header format):

```markdown
## [Unreleased]

### Breaking Changes

- Renamed `list_channels` tool to `list_public_channels` — same behavior, clearer name

### Added

- New `list_my_channels` tool: returns channels the authenticated user belongs to
  (public, private, DM, group) with optional `channel_types` filter
```

- [ ] **Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: add channel listing redesign to CHANGELOG"
```

---

### Task 8: Integration tests (requires Docker)

**Files:**
- Modify: `tests/integration/test_channels.py`
- Modify: `tests/integration/conftest.py`

- [ ] **Step 1: Update cleanup fixture**

In `tests/integration/conftest.py`, find `cleanup_orphaned_resources`. Replace `list_channels` call with `list_public_channels`.

- [ ] **Step 2: Rename existing integration tests**

In `tests/integration/test_channels.py`, replace all occurrences of `"list_channels"` with `"list_public_channels"` in `call_tool` calls and test names.

- [ ] **Step 3: Add list_my_channels integration tests**

Add a new test class in `tests/integration/test_channels.py`:

```python
class TestListMyChannels:
    """list_my_channels tool tests via MCP protocol."""

    async def test_list_my_channels_includes_town_square(self, mcp_client, team):
        """list_my_channels: returns town-square (bot is a member)."""
        result = await mcp_client.call_tool(
            "list_my_channels",
            {"team_id": team["id"]},
        )

        channels = to_dict(result)
        channel_names = [ch["name"] for ch in channels]
        assert "town-square" in channel_names

    async def test_list_my_channels_includes_private_channel(self, mcp_client, team):
        """list_my_channels: returns private channels; list_public_channels does not."""
        name = make_test_name()
        channel_id = None

        try:
            create_result = await mcp_client.call_tool(
                "create_channel",
                {
                    "team_id": team["id"],
                    "name": name,
                    "display_name": f"Private {name}",
                    "channel_type": "P",
                },
            )
            channel = to_dict(create_result)
            channel_id = channel["id"]

            # Should appear in list_my_channels
            my_result = await mcp_client.call_tool(
                "list_my_channels",
                {"team_id": team["id"]},
            )
            my_channels = to_dict(my_result)
            my_ids = [ch["id"] for ch in my_channels]
            assert channel_id in my_ids

            # Should NOT appear in list_public_channels
            public_result = await mcp_client.call_tool(
                "list_public_channels",
                {"team_id": team["id"]},
            )
            public_channels = to_dict(public_result)
            public_ids = [ch["id"] for ch in public_channels]
            assert channel_id not in public_ids
        finally:
            if channel_id:
                await cleanup_channel(channel_id)

    async def test_list_my_channels_includes_direct_message(self, mcp_client, bot_user, team):
        """list_my_channels: returns DM channels."""
        # Create a self-DM (simplest way to get a DM channel)
        dm_result = await mcp_client.call_tool(
            "create_direct_channel",
            {"user_id_1": bot_user["id"], "user_id_2": bot_user["id"]},
        )
        dm_channel = to_dict(dm_result)

        my_result = await mcp_client.call_tool(
            "list_my_channels",
            {"team_id": team["id"]},
        )
        my_channels = to_dict(my_result)
        my_ids = [ch["id"] for ch in my_channels]
        assert dm_channel["id"] in my_ids

    async def test_list_my_channels_filter_excludes_dm(self, mcp_client, bot_user, team):
        """list_my_channels: channel_types=["O","P"] excludes DMs."""
        # Ensure a DM exists
        await mcp_client.call_tool(
            "create_direct_channel",
            {"user_id_1": bot_user["id"], "user_id_2": bot_user["id"]},
        )

        result = await mcp_client.call_tool(
            "list_my_channels",
            {"team_id": team["id"], "channel_types": ["O", "P"]},
        )
        channels = to_dict(result)
        types = {ch["type"] for ch in channels}
        assert "D" not in types
        assert "G" not in types

    async def test_list_my_channels_filter_only_private(self, mcp_client, team):
        """list_my_channels: channel_types=["P"] returns only private."""
        name = make_test_name()
        channel_id = None

        try:
            create_result = await mcp_client.call_tool(
                "create_channel",
                {
                    "team_id": team["id"],
                    "name": name,
                    "display_name": f"Private {name}",
                    "channel_type": "P",
                },
            )
            channel = to_dict(create_result)
            channel_id = channel["id"]

            result = await mcp_client.call_tool(
                "list_my_channels",
                {"team_id": team["id"], "channel_types": ["P"]},
            )
            channels = to_dict(result)
            assert all(ch["type"] == "P" for ch in channels)
            assert any(ch["id"] == channel_id for ch in channels)
        finally:
            if channel_id:
                await cleanup_channel(channel_id)

    async def test_list_my_channels_filter_only_dm(self, mcp_client, bot_user, team):
        """list_my_channels: channel_types=["D"] returns only DMs."""
        # Ensure a DM exists
        await mcp_client.call_tool(
            "create_direct_channel",
            {"user_id_1": bot_user["id"], "user_id_2": bot_user["id"]},
        )

        result = await mcp_client.call_tool(
            "list_my_channels",
            {"team_id": team["id"], "channel_types": ["D"]},
        )
        channels = to_dict(result)
        assert len(channels) >= 1
        assert all(ch["type"] == "D" for ch in channels)
```

- [ ] **Step 4: Run integration tests**

Run: `uv run pytest tests/integration/test_channels.py -v`

Expected: ALL PASS (requires Docker for Testcontainers)

- [ ] **Step 5: Commit**

```bash
git add tests/integration/
git commit -m "test: add integration tests for list_my_channels with private/DM coverage

Co-authored-by: Daniil Svetlov <svetlov@bpcbt.com>"
```
