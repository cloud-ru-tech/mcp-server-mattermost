<div align="center">

<img src="https://raw.githubusercontent.com/cloud-ru-tech/mcp-server-mattermost/main/assets/logo.svg" alt="mcp-server-mattermost" width="120">

# mcp-server-mattermost

Let AI assistants read, search, and post in your Mattermost workspace

37 tools · Channels · Messages · Reactions · Threads · Files · Users

[![MCP Server](https://img.shields.io/badge/MCP-Server-blue)](https://modelcontextprotocol.io/)
[![PyPI version](https://badge.fury.io/py/mcp-server-mattermost.svg)](https://pypi.org/project/mcp-server-mattermost/)
[![Docker Pulls](https://img.shields.io/docker/pulls/legard/mcp-server-mattermost)](https://hub.docker.com/r/legard/mcp-server-mattermost)
[![Tests](https://github.com/cloud-ru-tech/mcp-server-mattermost/workflows/CI/badge.svg)](https://github.com/cloud-ru-tech/mcp-server-mattermost/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docs](https://img.shields.io/badge/docs-Read%20the%20Docs-blue)](https://mcp-server-mattermost.readthedocs.io/)

</div>

## Features

**Channels** — list, create, join, manage channels and DMs<br>
**Messages** — send, search, edit, delete with rich attachments<br>
**Reactions & Threads** — emoji reactions, pins, full thread history<br>
**Users & Teams** — lookup, search, status<br>
**Files** — upload, metadata, download links<br>
**Bookmarks** — save links and files in channels (Entry+ edition)

## Example Queries

Once configured, you can ask your AI assistant:

- "List all channels and find where the deployment discussion is happening"
- "Send a build status alert to #engineering with a red attachment"
- "Search for messages about the outage last week and summarize"
- "Summarize this thread and post the key decisions"
- "Find who worked on the authentication bug last week"
- "Upload the report.pdf to #general and share the link"

## Available Tools

<details>
<summary>Channels (10 tools)</summary>

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `list_public_channels` | List public channels in a team | `team_id` ✓ |
| `list_my_channels` | List channels you are a member of | `team_id` ✓ |
| `get_channel` | Get channel details by ID | `channel_id` ✓ |
| `get_channel_by_name` | Get channel by name | `team_id`, `channel_name` ✓ |
| `create_channel` | Create a new channel | `team_id`, `name`, `display_name` ✓ |
| `join_channel` | Join a public channel | `channel_id` ✓ |
| `leave_channel` | Leave a channel | `channel_id` ✓ |
| `get_channel_members` | List channel members | `channel_id` ✓ |
| `add_user_to_channel` | Add user to channel | `channel_id`, `user_id` ✓ |
| `create_direct_channel` | Create DM channel | `user_id_1`, `user_id_2` ✓ |

</details>

<details>
<summary>Messages (5 tools)</summary>

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `post_message` | Send a message to a channel | `channel_id`, `message` ✓, `attachments` |
| `get_channel_messages` | Get recent messages | `channel_id` ✓ |
| `search_messages` | Search messages by term | `team_id`, `terms` ✓ |
| `update_message` | Edit a message | `post_id`, `message` ✓, `attachments` |
| `delete_message` | Delete a message | `post_id` ✓ |

</details>

<details>
<summary>Reactions & Threads (6 tools)</summary>

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `add_reaction` | Add emoji reaction | `post_id`, `emoji_name` ✓ |
| `remove_reaction` | Remove emoji reaction | `post_id`, `emoji_name` ✓ |
| `get_reactions` | Get all reactions on a post | `post_id` ✓ |
| `pin_message` | Pin a message | `post_id` ✓ |
| `unpin_message` | Unpin a message | `post_id` ✓ |
| `get_thread` | Get thread messages | `post_id` ✓ |

</details>

<details>
<summary>Users (5 tools)</summary>

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `get_me` | Get current user info | — |
| `get_user` | Get user by ID | `user_id` ✓ |
| `get_user_by_username` | Get user by username | `username` ✓ |
| `search_users` | Search users | `term` ✓ |
| `get_user_status` | Get online status | `user_id` ✓ |

</details>

<details>
<summary>Teams (3 tools)</summary>

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `list_teams` | List your teams | — |
| `get_team` | Get team details | `team_id` ✓ |
| `get_team_members` | List team members | `team_id` ✓ |

</details>

<details>
<summary>Files (3 tools)</summary>

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `upload_file` | Upload a file | `channel_id`, `file_path` ✓ |
| `get_file_info` | Get file metadata | `file_id` ✓ |
| `get_file_link` | Get download link | `file_id` ✓ |

</details>

<details>
<summary>Bookmarks (5 tools) — Requires Entry+ edition</summary>

> **Note:** Requires Entry, Professional, Enterprise, or Enterprise Advanced edition
> (not available in Team Edition). Minimum version: v10.1.

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `list_bookmarks` | List channel bookmarks | `channel_id` ✓ |
| `create_bookmark` | Create link or file bookmark | `channel_id`, `display_name`, `bookmark_type` ✓ |
| `update_bookmark` | Update bookmark properties | `channel_id`, `bookmark_id` ✓ |
| `delete_bookmark` | Delete a bookmark | `channel_id`, `bookmark_id` ✓ |
| `update_bookmark_sort_order` | Reorder bookmark | `channel_id`, `bookmark_id`, `new_sort_order` ✓ |

</details>

## Quick Start

1. Get a [Mattermost bot token](https://developers.mattermost.com/integrate/admin-guide/admin-bot-accounts/)
2. Add to your MCP client config:

```json
{
  "mcpServers": {
    "mattermost": {
      "command": "uvx",
      "args": ["mcp-server-mattermost"],
      "env": {
        "MATTERMOST_URL": "https://your-server.com",
        "MATTERMOST_TOKEN": "your-token"
      }
    }
  }
}
```

3. Restart your client

> **[Full setup guide](https://mcp-server-mattermost.readthedocs.io/quickstart/)** — Claude Desktop, Cursor, Claude Code, Opencode, Docker, pip

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MATTERMOST_URL` | Yes | — | Mattermost server URL |
| `MATTERMOST_TOKEN` | Conditional | — | Bot or personal access token. MATTERMOST_TOKEN is required only when per-client token authentication (MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS) is not enabled. |
| `MATTERMOST_TIMEOUT` | No | 30 | Request timeout in seconds |
| `MATTERMOST_MAX_RETRIES` | No | 3 | Max retry attempts |
| `MATTERMOST_VERIFY_SSL` | No | true | Verify SSL certificates |
| `MATTERMOST_LOG_LEVEL` | No | INFO | Logging level |
| `MATTERMOST_LOG_FORMAT` | No | json | Log output format: `json` or `text` |
| `MATTERMOST_API_VERSION` | No | v4 | Mattermost API version |
| `MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS` | No | false | Allow HTTP clients to use their own Mattermost tokens |

## Docker

### Stdio mode (default)

```bash
docker run -i --rm \
  -e MATTERMOST_URL=https://your-mattermost.com \
  -e MATTERMOST_TOKEN=your-token \
  legard/mcp-server-mattermost
```

<details>
<summary>Claude Desktop config</summary>

```json
{
  "mcpServers": {
    "mattermost": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "MATTERMOST_URL=https://your-mattermost.com",
        "-e", "MATTERMOST_TOKEN=your-token",
        "legard/mcp-server-mattermost"
      ]
    }
  }
}
```

</details>

### HTTP mode (production)

```bash
docker run -d -p 8000:8000 \
  -e MCP_TRANSPORT=http \
  -e MCP_HOST=0.0.0.0 \
  -e MATTERMOST_URL=https://your-mattermost.com \
  -e MATTERMOST_TOKEN=your-token \
  legard/mcp-server-mattermost
```

Health check: `curl http://localhost:8000/health`

### Environment Variables (Docker)

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `stdio` | Transport: `stdio` or `http` |
| `MCP_HOST` | `127.0.0.1` | HTTP bind host (use `0.0.0.0` in Docker) |
| `MCP_PORT` | `8000` | HTTP port |

## Documentation

📖 **[mcp-server-mattermost.readthedocs.io](https://mcp-server-mattermost.readthedocs.io/)**

- [Quick Start](https://mcp-server-mattermost.readthedocs.io/quickstart/) — Installation and setup
- [Configuration](https://mcp-server-mattermost.readthedocs.io/configuration/) — Environment variables
- [Tools Reference](https://mcp-server-mattermost.readthedocs.io/tools/) — Detailed API documentation
- [llms.txt](https://github.com/cloud-ru-tech/mcp-server-mattermost/blob/main/llms.txt) — AI-readable documentation index

## Development

```bash
# Clone and install
git clone https://github.com/cloud-ru-tech/mcp-server-mattermost
cd mcp-server-mattermost
uv sync --dev

# Run unit tests
uv run pytest

# Run integration tests (requires Docker or external Mattermost)
uv run pytest tests/integration -v

# Type checking
uv run mypy src/

# Linting
uv run ruff check src/ tests/

# Run locally
MATTERMOST_URL=https://... MATTERMOST_TOKEN=... uv run mcp-server-mattermost
```

### Integration Tests

Integration tests run against a real Mattermost server via Docker (Testcontainers) or external server.

```bash
# With Docker (Testcontainers) — automatic setup
uv run pytest tests/integration -v

# Against external Mattermost server
export MATTERMOST_URL=https://your-server.com
export MATTERMOST_TOKEN=your-bot-token
uv run pytest tests/integration -v

# Run specific test module
uv run pytest tests/integration/test_channels.py -v
```

Integration tests are excluded from the default `pytest` run. Unit tests run with:

```bash
uv run pytest  # Unit tests only
```

## Debugging

Use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector) to debug:

```bash
npx @modelcontextprotocol/inspector uvx mcp-server-mattermost
```

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with [FastMCP](https://gofastmcp.com/) · [Mattermost API v4](https://api.mattermost.com/)

</div>
