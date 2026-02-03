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

## Environment Variables

### Mattermost Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MATTERMOST_URL` | Yes | — | Mattermost server URL |
| `MATTERMOST_TOKEN` | Yes | — | Bot or personal access token |
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

## Container Orchestration

When running in Kubernetes or Docker Swarm, disable the healthcheck for stdio mode:

```bash
docker run -i --rm --no-healthcheck \
  -e MATTERMOST_URL=https://your-mattermost.com \
  -e MATTERMOST_TOKEN=your-token \
  legard/mcp-server-mattermost
```

The healthcheck only works in HTTP mode.

## Build from Source

```bash
git clone https://github.com/legard/mcp-server-mattermost
cd mcp-server-mattermost
docker build -t mcp-server-mattermost .
```
