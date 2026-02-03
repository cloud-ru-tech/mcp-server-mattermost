# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP server for Mattermost integration. Exposes Mattermost REST API operations as MCP tools
for AI assistants (Claude Desktop, Cursor).

**Architecture:**

```text
MCP Client (Claude Desktop, Cursor)
    ↓ (stdio JSON-RPC)
FastMCP Server
    ├── Tools Layer (channels, messages, posts, users, teams, files, bookmarks)
    ├── Pydantic Models (validation + schema generation)
    └── MattermostClient (async HTTP with retry)
        ↓ (HTTPS)
Mattermost Server (REST API v4)
```

## Documentation References

- **FastMCP**: <https://gofastmcp.com/llms.txt> - Use for implementation details when working with FastMCP
- **Mattermost API**: <https://api.mattermost.com/> - REST API v4 reference

## Commands

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run specific test file
uv run pytest tests/test_config.py -v

# Lint
uv run ruff check src tests

# Format
uv run ruff format src tests

# Type check
uv run mypy src

# Run the server
uv run mcp-server-mattermost
```

## Code Style

- Python 3.10+ (use `list[]`, `dict[]`, `X | None` syntax)
- 120-character line length
- Google-style docstrings
- Type hints required (mypy strict mode)
- Two blank lines after imports
- Ruff with ALL rules enabled (see pyproject.toml for exceptions)

## Key Source Files

- `src/mcp_server_mattermost/__init__.py` - Package entry, exports `main()` and `__version__`
- `src/mcp_server_mattermost/server.py` - FastMCP instance creation
- `src/mcp_server_mattermost/client.py` - Async HTTP client with retry logic
- `src/mcp_server_mattermost/config.py` - Settings via pydantic-settings (env vars prefixed `MATTERMOST_`)
- `src/mcp_server_mattermost/exceptions.py` - Exception hierarchy (`MattermostMCPError` base)
- `src/mcp_server_mattermost/logging.py` - Logging setup (stderr per MCP spec)
- `src/mcp_server_mattermost/middleware.py` - FastMCP middleware for error handling
- `src/mcp_server_mattermost/tools/` - MCP tool implementations by category
- `src/mcp_server_mattermost/models/` - Pydantic models for validation

## Configuration

Required environment variables:
- `MATTERMOST_URL` - Mattermost server URL
- `MATTERMOST_TOKEN` - Bot or user access token

Optional:
- `MATTERMOST_TIMEOUT` (default: 30)
- `MATTERMOST_MAX_RETRIES` (default: 3)
- `MATTERMOST_VERIFY_SSL` (default: true)
- `MATTERMOST_LOG_LEVEL` (default: INFO)
- `MATTERMOST_LOG_FORMAT` (default: json) - Log format: 'json' for production, 'text' for development
- `MATTERMOST_API_VERSION` (default: v4)

## Testing

### Unit Tests

Tests use pytest with pytest-asyncio. Test fixtures in `tests/conftest.py`:
- `clean_env` - Removes MATTERMOST_* env vars for test isolation
- `mock_settings` - Sets valid test environment variables

Use respx for mocking httpx requests.

### Integration Tests

Integration tests in `tests/integration/` use **fastmcp.Client for in-memory MCP testing**.

**Key insight:** FastMCP provides `Client(server)` that connects directly to server instance
via in-memory transport — no subprocess, no network overhead, full MCP protocol.

```python
from fastmcp import Client
from mcp_server_mattermost.server import mcp

async def test_list_channels(mattermost_env):
    async with Client(mcp) as client:
        result = await client.call_tool("list_channels", {"team_id": team_id})
        assert any(ch["name"] == "town-square" for ch in result.data)
```

**What this tests:**
- MCP protocol (tools/list, tools/call, JSON-RPC)
- Pydantic validation at tool layer
- FastMCP routing
- MattermostClient HTTP logic
- Real Mattermost API

**References:**
- [FastMCP Testing Guide](https://gofastmcp.com/development/tests)
- [Stop Vibe-Testing Your MCP Server](https://www.jlowin.dev/blog/stop-vibe-testing-mcp-servers)

**Run integration tests:**

```bash
# With Testcontainers (needs Docker)
uv run pytest tests/integration

# Against external server
export MATTERMOST_URL=https://your-server.com
export MATTERMOST_TOKEN=your-bot-token
uv run pytest tests/integration
```

## MCP Tool Annotations

FastMCP defaults (important to remember):
- `readOnlyHint`: **false** — explicitly set `True` for read-only operations
- `destructiveHint`: **true** — explicitly set `False` for reversible write operations
- `idempotentHint`: **false** — explicitly set `True` if repeated call = no-op

Operation classification:
- **Read-only** → `readOnlyHint=True, idempotentHint=True`
- **Write idempotent** (join, add_reaction, pin) → `destructiveHint=False, idempotentHint=True`
- **Write non-idempotent** (post_message, create_channel) → `destructiveHint=False`
- **Destructive** (delete_message) → no annotations needed (default true)

"Destructive" = irreversible loss of data.

## MCP Tool Description Best Practices

Description formula: **WHAT it does + WHEN to use + DISAMBIGUATION**

```python
# Disambiguation example between similar tools:
"""Get recent messages from a channel.

Returns messages in reverse chronological order.
Use for reading channel conversation history.
For searching by keywords, use search_messages instead.  # ← disambiguation
"""
```

## Code Patterns

### FastMCP Dependency Injection

All tool functions use this pattern:

```python
client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
```

The `# noqa: B008` suppresses ruff's flake8-bugbear warning "Do not perform function calls
in argument defaults". This is intentional — `Depends()` is a FastMCP/FastAPI DI marker,
not a mutable default. The function call happens at request time, not at function definition.

## Versioning

This project uses manual versioning:

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md` with changes
3. Commit: `git commit -m "chore: bump version to X.Y.Z"`
4. Tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
5. Push: `git push origin main --tags`
6. Create GitHub Release from tag → triggers PyPI publish
