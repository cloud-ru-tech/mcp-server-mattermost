# Quick Start

Get up and running in 2 minutes.

## Prerequisites

- Mattermost server with API access
- Bot account or personal access token for local stdio mode
- Mattermost OAuth 2.0 Application for HTTP `oauth_proxy` mode

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
    git clone https://github.com/cloud-ru-tech/mcp-server-mattermost
    cd mcp-server-mattermost
    uv sync
    ```

## Choose an Authentication Mode

| Mode | Best for | Mattermost setup |
|------|----------|------------------|
| `static_token` | Local stdio clients, bot accounts, simple single-user setup | Bot token or personal access token |
| `client_token` | HTTP clients with Mattermost user tokens | Client sends `Authorization: Bearer <token>` |
| `oauth_proxy` | Remote HTTP MCP clients where every user signs in with SSO | Mattermost OAuth 2.0 Application |

The rest of this page shows `static_token` first because it is the fastest local setup.
Use [Mattermost OAuth Proxy](#mattermost-oauth-proxy) for Claude Code or other remote
HTTP clients that should authenticate users through Mattermost SSO.

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

## Mattermost OAuth Proxy

Use this mode when the MCP server runs as an HTTP service and each user should access
Mattermost with their own SSO-backed identity.

### 1. Register the OAuth App in Mattermost

In Mattermost, enable OAuth service provider support, then create an app under
**Integrations** -> **OAuth 2.0 Applications**.

Recommended production settings:

| Field | Value |
|-------|-------|
| Is Trusted | Yes |
| Is Public Client | No |
| Display Name | Mattermost MCP |
| Homepage | `https://mcp.example.com` |
| Callback URLs | `https://mcp.example.com/oauth/callback/mm` |

Save the generated client ID and client secret.

For development public-client setups, set **Is Public Client** to **Yes**, leave the
client secret empty, and register the callback URL for the MCP server URL you run.

### 2. Run the MCP Server

Confidential production example:

    docker run -d --name mattermost-mcp -p 8000:8000 \
      -e MCP_TRANSPORT=http \
      -e MCP_HOST=0.0.0.0 \
      -e MCP_PORT=8000 \
      -e MATTERMOST_AUTH_MODE=oauth_proxy \
      -e MATTERMOST_URL=https://mattermost.internal \
      -e MATTERMOST_OAUTH_MATTERMOST_PUBLIC_URL=https://mattermost.example.com \
      -e MATTERMOST_OAUTH_MCP_PUBLIC_URL=https://mcp.example.com \
      -e MATTERMOST_OAUTH_CLIENT_ID=your-mattermost-oauth-app-id \
      -e MATTERMOST_OAUTH_CLIENT_TYPE=confidential \
      -e MATTERMOST_OAUTH_CLIENT_SECRET=your-mattermost-oauth-app-secret \
      legard/mcp-server-mattermost

`MATTERMOST_URL` must be reachable from the MCP server.
`MATTERMOST_OAUTH_MATTERMOST_PUBLIC_URL` must be reachable from the user's browser.

### 3. Connect Claude Code

    claude mcp add --transport http mattermost https://mcp.example.com/mcp

Do not pass `--client-id` for this server. Claude Code uses Dynamic Client Registration
with the MCP server, and the MCP server uses the fixed Mattermost OAuth App credentials
upstream.

### 4. Complete Login

On first use, Claude Code opens the browser. The flow is:

1. Claude Code registers itself with the MCP server.
2. The MCP server redirects the browser to Mattermost OAuth.
3. Mattermost performs local login or SSO through Keycloak.
4. Mattermost returns to `/oauth/callback/mm` on the MCP server.
5. Claude Code receives its MCP access token and can call tools.

## Next Steps

- [Configuration](configuration.md) — timeouts, retries, SSL options
- [Docker](docker.md) — container deployment and HTTP mode
- [Tools Reference](tools/index.md) — all 36 available tools
