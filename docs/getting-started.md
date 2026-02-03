# Getting Started

## Prerequisites

- Python 3.10+
- Mattermost server with API access
- Bot account or personal access token

## Installation

### Using uvx (recommended)

```bash
uvx mcp-server-mattermost
```

### Using pip

```bash
pip install mcp-server-mattermost
```

### From source

```bash
git clone https://github.com/legard/mcp-server-mattermost
cd mcp-server-mattermost
uv sync
uv run mcp-server-mattermost
```

### Using Docker

```bash
# Pull from registry (when published)
docker pull mcp-server-mattermost

# Or build locally
git clone https://github.com/legard/mcp-server-mattermost
cd mcp-server-mattermost
docker build -t mcp-server-mattermost .
```

## Get a Mattermost Token

1. Go to **System Console** → **Integrations** → **Bot Accounts**
2. Create a new bot or use an existing one
3. Copy the access token

## Configure Claude Desktop

Add to your Claude Desktop config:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

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

## Configure Cursor

Add to Cursor MCP settings:

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

## Configure Claude Desktop (Docker)

For running via Docker container:

```json
{
  "mcpServers": {
    "mattermost": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "MATTERMOST_URL=https://your-mattermost-server.com",
        "-e", "MATTERMOST_TOKEN=your-bot-token",
        "mcp-server-mattermost"
      ]
    }
  }
}
```

## Verify Installation

Restart your MCP client. The Mattermost tools should now be available.

Test with a simple query like "List my teams" or "What channels are available?"
