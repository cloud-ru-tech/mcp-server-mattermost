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
- `src/mcp_server_mattermost/server.py` - FastMCP instance creation, lifespan, FileSystemProvider
- `src/mcp_server_mattermost/deps.py` - Dependency injection providers (get_client)
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

## Tool Capability Metadata

Each tool declares a `capability` in `meta` for agent-based filtering:

- `read` — retrieves data, no side effects (get, list, search)
- `write` — modifies state within existing resources (post, update, join, pin, react, upload)
- `create` — creates new top-level entities (channels, DMs)
- `delete` — permanently destroys a resource

Use `Capability` enum from `enums.py` — never raw strings:

```python
from fastmcp.tools import tool
from mcp_server_mattermost.enums import Capability, ToolTag

@tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.CHANNEL},
    meta={"capability": Capability.READ},
)
async def list_channels(...):
```

Classification rules:
- `create` = only for new standalone entities (channels, DMs)
- `write` = all other modifications, including "create" operations on dependent resources
  (bookmarks, messages, reactions, files exist only inside a channel)
- `delete` = resource permanently ceases to exist
- Each tool gets exactly one capability

Profiles are defined client-side, not server-side. The server provides capability labels,
clients assemble profiles from them:

```python
PROFILES = {
    "reader":  {"read"},
    "writer":  {"read", "write"},
    "manager": {"read", "write", "create"},
    "admin":   {"read", "write", "create", "delete"},
}
```

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
from fastmcp.dependencies import Depends
from mcp_server_mattermost.deps import get_client

client: MattermostClient = Depends(get_client),  # noqa: B008
```

The `# noqa: B008` suppresses ruff's flake8-bugbear warning "Do not perform function calls
in argument defaults". This is intentional — `Depends()` is a FastMCP/FastAPI DI marker,
not a mutable default. The function call happens at request time, not at function definition.

## Versioning

This project uses manual versioning:

1. Update version in `pyproject.toml`
2. Update `__version__` fallback in `src/mcp_server_mattermost/__init__.py`
3. Update `CHANGELOG.md` with changes
4. Commit: `git commit -m "chore: bump version to X.Y.Z"`
5. Tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
6. Push: `git push origin main --tags`
7. Create GitHub Release from tag → triggers PyPI publish

## Pre-commit Checklist

Before committing, always run the full lint suite and fix any issues:

```bash
uv run ruff check src tests   # lint
uv run ruff format src tests  # format
uv run mypy src               # type check
uv run pytest                 # tests
```

Do NOT commit code that has lint, type, or test errors.

## Lessons Learned

- When using markdown (images, lists, bold) inside HTML blocks (`<div>`, `<details>`) in MkDocs — add `md_in_html` extension and `markdown` attribute on the HTML tag, otherwise content renders as plain text
- When adding CSS class to an image in MkDocs — use `attr_list` extension with `![alt](path){ .classname }` instead of wrapping in `<div class="...">`. Cleaner, no HTML needed
