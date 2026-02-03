# Quick Start

Get up and running in 2 minutes.

## Prerequisites

- Mattermost server with API access
- Bot account or personal access token

## Install

=== "uvx (recommended)"

    ```bash
    uvx mcp-server-mattermost
    ```

    No installation needed — runs directly.

=== "pip"

    ```bash
    pip install mcp-server-mattermost
    ```

=== "Docker"

    ```bash
    docker pull legard/mcp-server-mattermost
    ```

=== "From source"

    ```bash
    git clone https://github.com/legard/mcp-server-mattermost
    cd mcp-server-mattermost
    uv sync
    ```

## Get a Mattermost Token

1. Go to **System Console** → **Integrations** → **Bot Accounts**
2. Create a new bot or use an existing one
3. Copy the access token

!!! tip
    Personal access tokens also work: **Profile** → **Security** → **Personal Access Tokens**

## Configure Your MCP Client

=== "Claude Desktop"

    Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
    or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

    ```json
    {
      "mcpServers": {
        "mattermost": {
          "command": "uvx",
          "args": ["mcp-server-mattermost"],
          "env": {
            "MATTERMOST_URL": "https://your-mattermost-server.com",
            "MATTERMOST_TOKEN": "your-bot-token"
          }
        }
      }
    }
    ```

=== "Cursor"

    Add to `~/.cursor/mcp.json`:

    ```json
    {
      "mcpServers": {
        "mattermost": {
          "command": "uvx",
          "args": ["mcp-server-mattermost"],
          "env": {
            "MATTERMOST_URL": "https://your-mattermost-server.com",
            "MATTERMOST_TOKEN": "your-bot-token"
          }
        }
      }
    }
    ```

=== "Claude Code"

    ```bash
    claude mcp add mattermost \
      -e MATTERMOST_URL=https://your-mattermost-server.com \
      -e MATTERMOST_TOKEN=your-bot-token \
      -- uvx mcp-server-mattermost
    ```

=== "Opencode"

    Add to `opencode.json`:

    ```json
    {
      "mcp": {
        "mattermost": {
          "type": "local",
          "command": ["uvx", "mcp-server-mattermost"],
          "enabled": true,
          "environment": {
            "MATTERMOST_URL": "https://your-mattermost-server.com",
            "MATTERMOST_TOKEN": "your-bot-token"
          }
        }
      }
    }
    ```

## Verify

1. Restart your MCP client
2. Test with a simple query: "List my teams" or "What channels are available?"

The Mattermost tools are now available in your conversations.

## Next Steps

- [Configuration](configuration.md) — timeouts, retries, SSL options
- [Docker](docker.md) — container deployment and HTTP mode
- [Tools Reference](tools/index.md) — all 36 available tools
