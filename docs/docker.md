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

For networked HTTP use per-client auth: `client_token` (below) or `oauth_proxy` (below). `static_token`
over HTTP serves an unauthenticated endpoint and only warns — it does not block; see
[Authentication → HTTP transport](authentication.md#http-transport):

```bash
docker run -d -p 8000:8000 \
  -e MCP_TRANSPORT=http \
  -e MCP_HOST=0.0.0.0 \
  -e MATTERMOST_AUTH_MODE=client_token \
  -e MATTERMOST_URL=https://your-mattermost.com \
  -e MATTERMOST_HTTP_HOST_ORIGIN_PROTECTION=auto \
  -e MATTERMOST_HTTP_ALLOWED_HOSTS=mcp.example.com \
  legard/mcp-server-mattermost
```

In `client_token` mode every MCP client must send its own Mattermost token as
`Authorization: Bearer <token>`; requests without one get `401`.

A published-port container receives connections on its bridge address, which `auto` does not validate on its
own — declare `MATTERMOST_HTTP_ALLOWED_HOSTS` (the public hostname clients use) to turn the check on there.
See [HTTP transport security](configuration.md#http-transport-security).

Health check endpoint:

```bash
curl http://localhost:8000/health
```

### Keeping `static_token` behind an auth proxy

A `static_token` server behind an authenticating proxy starts on any bind (the warning is expected here —
the proxy provides authentication). To also make the server **unreachable except through the proxy**,
co-locate the proxy in the same network namespace and bind the MCP server to loopback (the proxy publishes
the port):

The two containers share one network namespace, so they need different ports: the proxy publishes 8000 and
forwards to the MCP server on 8001.

```yaml
services:
  auth-proxy:
    image: your-auth-proxy
    ports: ["8000:8000"]                 # upstream: 127.0.0.1:8001
  mattermost-mcp:
    image: legard/mcp-server-mattermost
    network_mode: "service:auth-proxy"   # shares localhost with the proxy
    environment:
      MCP_TRANSPORT: http
      MCP_HOST: 127.0.0.1
      MCP_PORT: 8001
      MATTERMOST_URL: https://your-mattermost.com
      MATTERMOST_TOKEN: your-token
      MATTERMOST_HTTP_HOST_ORIGIN_PROTECTION: auto
```

Every connection here arrives over loopback, so with `auto` the `Host` and `Origin` are validated. If the
proxy forwards the public `Host`, add it to `MATTERMOST_HTTP_ALLOWED_HOSTS`, or the server answers `421`.
`X-Forwarded-Host` is never trusted; `X-Forwarded-Proto` is honored from loopback peers, which the proxy is
here.

## HTTP Mode with Mattermost OAuth Proxy

For production deployments where each user signs in with their own Mattermost
identity, run with `MATTERMOST_AUTH_MODE=oauth_proxy`:

```bash
docker run -d -p 8000:8000 \
  -e MCP_TRANSPORT=http \
  -e MCP_HOST=0.0.0.0 \
  -e MATTERMOST_AUTH_MODE=oauth_proxy \
  -e MATTERMOST_URL=https://mattermost.internal \
  -e MATTERMOST_OAUTH_MATTERMOST_PUBLIC_URL=https://mattermost.example.com \
  -e MATTERMOST_OAUTH_MCP_PUBLIC_URL=https://mcp.example.com \
  -e MATTERMOST_OAUTH_CLIENT_ID=your-mattermost-oauth-app-id \
  -e MATTERMOST_OAUTH_CLIENT_TYPE=confidential \
  -e MATTERMOST_OAUTH_CLIENT_SECRET=your-mattermost-oauth-app-secret \
  legard/mcp-server-mattermost
```

See [Authentication / oauth_proxy](authentication.md#oauth_proxy) for Mattermost
OAuth App registration, the public-client variant, and MCP client connection.

## Environment Variables

For authentication-related variables (`MATTERMOST_AUTH_MODE`, `MATTERMOST_TOKEN`,
all `MATTERMOST_OAUTH_*`), see [Authentication](authentication.md#configuration-reference).

### Mattermost Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MATTERMOST_URL` | Yes | — | Mattermost server URL |
| `MATTERMOST_TIMEOUT` | No | 30 | Request timeout in seconds |
| `MATTERMOST_MAX_RETRIES` | No | 3 | Max retry attempts |
| `MATTERMOST_VERIFY_SSL` | No | true | Verify SSL certificates |
| `MATTERMOST_EXTRA_CA_CERTS` | No | — | Path to mounted PEM CAs appended to the default trust store |
| `MATTERMOST_LOG_LEVEL` | No | INFO | Logging level |
| `MATTERMOST_LOG_FORMAT` | No | json | Log format: `json` or `text` |

For private or corporate CAs, mount the PEM bundle and point
`MATTERMOST_EXTRA_CA_CERTS` at the in-container path:

```bash
docker run -i --rm \
  -v /etc/ssl/certs/corporate-ca.pem:/certs/corporate-ca.pem:ro \
  -e MATTERMOST_URL=https://your-mattermost.com \
  -e MATTERMOST_TOKEN=your-token \
  -e MATTERMOST_EXTRA_CA_CERTS=/certs/corporate-ca.pem \
  legard/mcp-server-mattermost
```

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
