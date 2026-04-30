# Docker

Run MCP Server Mattermost in a Docker container.

## Quick Start

```bash
docker pull legard/mcp-server-mattermost
```

## Stdio Mode (Default)

Standard mode for MCP clients like Claude Desktop:

```bash
docker run -i --rm \
  -e MATTERMOST_URL=https://your-mattermost.com \
  -e MATTERMOST_TOKEN=your-token \
  legard/mcp-server-mattermost
```

### Claude Desktop Configuration

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

## HTTP Mode (Production)

For production deployments with health checks:

```bash
docker run -d -p 8000:8000 \
  -e MCP_TRANSPORT=http \
  -e MCP_HOST=0.0.0.0 \
  -e MATTERMOST_URL=https://your-mattermost.com \
  -e MATTERMOST_TOKEN=your-token \
  legard/mcp-server-mattermost
```

Health check endpoint:

```bash
curl http://localhost:8000/health
```

## HTTP Mode with Mattermost OAuth Proxy

Use `oauth_proxy` when HTTP MCP clients should sign in with their own Mattermost
identity. The MCP server acts as the OAuth server for MCP clients and proxies the
browser login to a Mattermost OAuth 2.0 Application.

### Mattermost App

Create a Mattermost OAuth 2.0 Application with this callback:

```text
https://mcp.example.com/oauth/callback/mm
```

Production settings:

| Mattermost OAuth App field | Value |
|----------------------------|-------|
| Is Trusted | Yes |
| Is Public Client | No |
| Callback URLs | `https://mcp.example.com/oauth/callback/mm` |

Keep the generated client ID and client secret.

### Docker Run

```bash
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
```

For public-client mode, omit the client secret and provide a stable JWT signing key:

```bash
docker run -d --name mattermost-mcp -p 8000:8000 \
  -e MCP_TRANSPORT=http \
  -e MCP_HOST=0.0.0.0 \
  -e MCP_PORT=8000 \
  -e MATTERMOST_AUTH_MODE=oauth_proxy \
  -e MATTERMOST_URL=https://mattermost.example.com \
  -e MATTERMOST_OAUTH_MATTERMOST_PUBLIC_URL=https://mattermost.example.com \
  -e MATTERMOST_OAUTH_MCP_PUBLIC_URL=https://mcp.example.com \
  -e MATTERMOST_OAUTH_CLIENT_ID=your-mattermost-oauth-app-id \
  -e MATTERMOST_OAUTH_CLIENT_TYPE=public \
  -e MATTERMOST_OAUTH_JWT_SIGNING_KEY=change-me-to-a-stable-key \
  legard/mcp-server-mattermost
```

### Client Connection

Claude Code:

```bash
claude mcp add --transport http mattermost https://mcp.example.com/mcp
```

Do not pass a fixed `--client-id` for this server. FastMCP Dynamic Client Registration
accepts the MCP client's loopback callback and maps it to the fixed Mattermost callback.

## Environment Variables

### Mattermost Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MATTERMOST_URL` | Yes | — | Mattermost server URL |
| `MATTERMOST_AUTH_MODE` | No | `static_token` | Authentication mode: `static_token`, `client_token`, or `oauth_proxy` |
| `MATTERMOST_TOKEN` | Conditional | — | Required for `static_token` mode |
| `MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS` | No | false | Deprecated alias for `MATTERMOST_AUTH_MODE=client_token` |
| `MATTERMOST_OAUTH_CLIENT_ID` | Conditional | — | Mattermost OAuth App client ID for `oauth_proxy` |
| `MATTERMOST_OAUTH_CLIENT_TYPE` | Conditional | `confidential` | `public` or `confidential` OAuth App |
| `MATTERMOST_OAUTH_CLIENT_SECRET` | Conditional | — | Required for confidential OAuth Apps |
| `MATTERMOST_OAUTH_MCP_PUBLIC_URL` | Conditional | — | Public base URL of this MCP server |
| `MATTERMOST_OAUTH_MATTERMOST_PUBLIC_URL` | No | `MATTERMOST_URL` | Browser-facing Mattermost URL |
| `MATTERMOST_OAUTH_CALLBACK_PATH` | No | `/oauth/callback/mm` | Callback path registered in the Mattermost OAuth App |
| `MATTERMOST_OAUTH_JWT_SIGNING_KEY` | Conditional | — | Required for public OAuth Apps |
| `MATTERMOST_OAUTH_REQUIRE_CONSENT` | No | true | Show the FastMCP consent screen before redirecting to Mattermost |
| `MATTERMOST_TIMEOUT` | No | 30 | Request timeout in seconds |
| `MATTERMOST_MAX_RETRIES` | No | 3 | Max retry attempts |
| `MATTERMOST_VERIFY_SSL` | No | true | Verify SSL certificates |
| `MATTERMOST_LOG_LEVEL` | No | INFO | Logging level |
| `MATTERMOST_LOG_FORMAT` | No | json | Log format: `json` or `text` |

### Transport Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `stdio` | Transport mode: `stdio` or `http` |
| `MCP_HOST` | `127.0.0.1` | HTTP bind host (use `0.0.0.0` in Docker) |
| `MCP_PORT` | `8000` | HTTP port |

## Healthcheck Behavior

The Dockerfile includes a healthcheck that probes `/health` endpoint. This only works
in HTTP mode (`MCP_TRANSPORT=http`).

**In stdio mode:**

- Healthcheck fails (no HTTP server running)
- Container status shows `unhealthy`
- This is harmless for normal `docker run` — the container works fine

**When this becomes a problem:**

- Docker Compose with `restart: on-failure` or `restart: always`
- Docker Swarm (restarts unhealthy containers automatically)

**Solution:** Add `--no-healthcheck` flag:

```bash
docker run -i --rm --no-healthcheck \
  -e MATTERMOST_URL=https://your-mattermost.com \
  -e MATTERMOST_TOKEN=your-token \
  legard/mcp-server-mattermost
```

Or override in compose file:

```yaml
services:
  mattermost-mcp:
    image: legard/mcp-server-mattermost
    healthcheck:
      disable: true
```

## Build from Source

```bash
git clone https://github.com/cloud-ru-tech/mcp-server-mattermost
cd mcp-server-mattermost
docker build -t mcp-server-mattermost .
```
