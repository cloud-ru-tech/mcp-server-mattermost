# MCP Server Mattermost

Let AI assistants read, search, and post in your Mattermost workspace.

## Features

- **Channels** — list, create, join, manage channels and DMs
- **Messages** — send, search, edit, delete with rich attachments
- **Reactions & Threads** — emoji reactions, pins, full thread history
- **Users & Teams** — lookup, search, status
- **Files** — upload, metadata, download links
- **Bookmarks** — save links and files in channels (Entry+ edition)

## Quick Start

### 1. Install

```bash
uvx mcp-server-mattermost
```

Or with pip:

```bash
pip install mcp-server-mattermost
```

### 2. Get a Mattermost Token

1. Go to **System Console** → **Integrations** → **Bot Accounts**
2. Create a new bot or use an existing one
3. Copy the access token

### 3. Configure Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

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

### 4. Restart Claude Desktop

The Mattermost tools will now be available in your conversations.

## Example Queries

Once configured, you can ask your AI assistant:

- "List all channels and find where the deployment discussion is happening"
- "Send a build status alert to #engineering with a red attachment"
- "Search for messages about the outage last week and summarize"
- "Reply in the thread with the test results"
- "Who's online in my team right now?"

## Links

- [GitHub Repository](https://github.com/legard/mcp-server-mattermost)
- [PyPI Package](https://pypi.org/project/mcp-server-mattermost/)
- [Mattermost API](https://api.mattermost.com/)
