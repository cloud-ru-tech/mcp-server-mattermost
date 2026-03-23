# Channel Listing Redesign

## Problem

The `list_channels` tool uses `GET /api/v4/teams/{team_id}/channels` (Mattermost's
`GetPublicChannelsForTeam`), which returns **only public channels**. The tool's docstring
claims "List public and private channels" — a lie that causes LLM agents to miss private
channels entirely.

A user reported seeing 1 channel instead of 91 (GitHub Issue #3). A PR (#4) proposed
swapping the endpoint to `/users/me/teams/{team_id}/channels`, but was rejected because
it loses public channel discovery and adds DMs/GMs unexpectedly.

## Goals

- Fix the bug: users must be able to see all channels they belong to (O, P, D, G)
- Preserve public channel discovery (finding channels to join)
- Clear tool naming so LLM agents pick the right tool
- Integration tests that catch channel visibility bugs

## Non-Goals

- Group message creation (`POST /channels/group`) — separate feature
- Cross-team channel listing (`GET /users/{user_id}/channels`) — future work
- Backward compatibility for the old `list_channels` name — clean break, documented

## Design

### Overview

Split channel listing into two tools with distinct semantics:

| Tool | Endpoint | Pagination | Purpose |
|------|----------|------------|---------|
| `list_public_channels` | `GET /teams/{team_id}/channels` | page/per_page | Discovery of all public channels (including unjoined) |
| `list_my_channels` | `GET /users/me/teams/{team_id}/channels` | None (API returns all) | Channels the user belongs to (O, P, D, G) |

The old `list_channels` tool is removed. This is a breaking change documented in CHANGELOG.

### Client Layer (`client.py`)

Rename `get_channels` to `get_public_channels`. No behavior change — same endpoint,
same parameters, same response format.

Add `get_my_channels`:

```python
async def get_my_channels(self, team_id: str) -> list[dict[str, Any]]:
    """Get all channels the authenticated user belongs to in a team.

    Returns public, private, DM, and group channels.
    No pagination — API returns all channels at once.
    """
    result = await self.get(f"/users/me/teams/{team_id}/channels")
    return result if isinstance(result, list) else []
```

No `page`/`per_page` parameters — the Mattermost API endpoint does not support pagination.

### Tool Layer (`tools/channels.py`)

**`list_public_channels`** (renamed from `list_channels`):

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
    client: MattermostClient = Depends(get_client),
) -> list[Channel]:
    """List public channels available in a team.

    Returns all public channels for discovery, including ones you haven't joined.
    Useful for finding channels to join.
    For channels you are already a member of (including private), use list_my_channels.
    """
```

Identical behavior to old `list_channels`. Only name and docstring change.

**`list_my_channels`** (new):

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
    client: MattermostClient = Depends(get_client),
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

Key design decisions:
- **No pagination** — API does not support it; tool signature reflects this honestly
- **Client-side filtering** by `channel_types` — API does not support server-side type
  filtering. MCP best practice: filter before returning to LLM to avoid context bloat
- **Default: all types** — no surprise exclusions; agent narrows as needed
- **Cross-references in both docstrings** — each tool points to the other for disambiguation

### Filtering Rationale

The `/users/me/teams/{team_id}/channels` endpoint returns all channel types mixed together.
MCP community consensus (Slack MCP, GitHub MCP, philschmid.de, arcade.dev) is to filter
before returning to LLM rather than dumping raw data. Since Mattermost API does not support
server-side type filtering on this endpoint, we filter client-side in the tool layer. The
client layer returns raw data; the tool layer applies the filter.

### Pydantic Model

No changes to the `Channel` model. Both endpoints return the same Channel object schema.
The `type` field (already present) distinguishes O/P/D/G.

## Files Changed

| File | Change |
|------|--------|
| `src/mcp_server_mattermost/client.py` | Rename `get_channels` → `get_public_channels`; add `get_my_channels` |
| `src/mcp_server_mattermost/tools/channels.py` | Rename `list_channels` → `list_public_channels`; add `list_my_channels` |
| `tests/test_client.py` | Rename test; add `test_get_my_channels` |
| `tests/test_tools/test_channels.py` | Rename test class; add `TestListMyChannels` |
| `tests/test_tools/conftest.py` | Rename `get_channels` → `get_public_channels` in all mock fixtures (including `mock_client_auth_error`, `mock_client_rate_limited`); add `get_my_channels` |
| `tests/integration/test_channels.py` | Rename tests; add my_channels tests with O/P/D coverage |
| `tests/integration/conftest.py` | Update `cleanup_orphaned_resources` to use `list_public_channels`; add private channel cleanup via direct deletion in test teardown |
| `tests/test_tools/test_tool_tags.py` | Update tool name; update total tool count 36 → 37 |
| `tests/test_capability_meta.py` | Update tool name; update expected capabilities (READ count 19 → 20, total 36 → 37) |
| `tests/test_server.py` | Update tool count assertion 36 → 37 |
| `CHANGELOG.md` | Document breaking change and new tool |
| `docs/tools/channels.md` | Rewrite `list_channels` section → `list_public_channels`; add `list_my_channels` section with parameters, examples, API link |
| `docs/tools/index.md` | Replace `list_channels` → `list_public_channels` in channels table; add `list_my_channels` row; update counts (36 → 37 tools, 9 → 10 channel tools) |
| `docs/building-agents.md` | Replace `list_channels` with `list_public_channels` in annotations and capabilities examples |
| `README.md` | Replace `list_channels` in tool table |
| `tests/integration/README.md` | Update code examples and test checklists (`list_channels` → `list_public_channels`; add `list_my_channels` entries) |
| `AGENTS.md` | Replace `list_channels` → `list_public_channels` in code examples; clarify `Co-Authored-By` restriction to AI agents only |

## Testing Strategy

### Unit Tests

**Client tests (`test_client.py`):**
- `test_get_public_channels` — renamed, same behavior, updated mock URL
- `test_get_my_channels` — mock `GET /users/me/teams/team123/channels`, verify list return

**Tool tests (`test_tools/test_channels.py`):**
- `TestListPublicChannels` — renamed from `TestListChannels`, same assertions
- `TestListMyChannels`:
  - `test_returns_all_types` — mock returns O, P, D, G channels; all present in result
  - `test_filters_by_type` — mock returns O, P, D, G; call with `channel_types=["O", "P"]`; D and G excluded
  - `test_empty_result` — mock returns `[]`

### Integration Tests

**Renamed:**
- All `list_channels` references → `list_public_channels` in test names and calls

**New tests for `list_my_channels`:**
- `test_list_my_channels_includes_town_square` — bot is member of town-square (O)
- `test_list_my_channels_includes_private_channel` — create private channel (P), verify visible in `list_my_channels` and NOT in `list_public_channels`
- `test_list_my_channels_includes_direct_message` — create DM via `create_direct_channel` (D), verify visible
- `test_list_my_channels_filter_excludes_dm` — call with `channel_types=["O", "P"]`, verify DM excluded
- `test_list_my_channels_filter_only_private` — call with `channel_types=["P"]`, verify only private returned
- `test_list_my_channels_filter_only_dm` — call with `channel_types=["D"]`, verify only DM returned

**Group messages (G):** Not tested in integration (requires 3+ users; covered by unit test mocks).

### Cleanup Fixture

`cleanup_orphaned_resources` updated from `list_channels` to `list_public_channels`.
Behavior unchanged — it cleans up public test channels with `mcp-test-` prefix.

Private test channels created in new integration tests are cleaned up via direct
`DELETE /channels/{id}` in test teardown (using the existing `cleanup_channel` helper),
not through the cleanup fixture.

## Breaking Changes

- Tool `list_channels` removed, replaced by `list_public_channels` (same endpoint, same
  parameters, same behavior — only the name and docstring changed)
- Requires minor version bump
- Documented in CHANGELOG.md and release notes

## Design Details

### `channel_types` parameter

- Type: `list[Literal["O", "P", "D", "G"]] | None`
- Default: `None` (no filtering — return all types)
- Validation: `Field(min_length=1)` — empty list is always a user error, return
  validation error immediately rather than a silent empty result
- `None` = all types pattern is consistent with the project's only other list parameter
  (`file_ids: list[FileId] | None = None` in `messages.py`)

### `list_public_channels` pagination note

Add to docstring: "Results are paginated. Use page/per_page to retrieve all channels."
This helps LLM agents understand they may need to paginate for large teams.

## Contributor Attribution

This work incorporates the problem analysis from PR #4 by Daniil Svetlov.

- Create a new PR (not reuse #4) since the architecture differs significantly
- Add `Co-authored-by: Daniil Svetlov <svetlov@bpcbt.com>` trailer to commit
- Close PR #4 with a comment linking to the new PR
- Confirm the bug in issue #3 with a link to the spec

## AGENTS.md Update

Clarify the `Co-Authored-By` restriction to specify it applies to AI agents only:

```
Do not include `Co-Authored-By:` trailers for AI agents in commit messages.
Human contributor co-authorship trailers are welcome.
```
