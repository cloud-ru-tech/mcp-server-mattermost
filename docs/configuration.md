# Configuration

All configuration is done via environment variables with the `MATTERMOST_` prefix.

For authentication-related variables (`MATTERMOST_AUTH_MODE`, `MATTERMOST_TOKEN`,
all `MATTERMOST_OAUTH_*`), see [Authentication](authentication.md).

## Required Variables

| Variable | Description |
|----------|-------------|
| `MATTERMOST_URL` | Mattermost server URL (e.g., `https://mattermost.example.com`) |

## Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MATTERMOST_TIMEOUT` | 30 | Request timeout in seconds (1-300) |
| `MATTERMOST_MAX_RETRIES` | 3 | Maximum retry attempts for failed requests (0-10) |
| `MATTERMOST_VERIFY_SSL` | true | Verify SSL certificates |
| `MATTERMOST_EXTRA_CA_CERTS` | — | Path to extra PEM CAs appended to the default trust store |
| `MATTERMOST_LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `MATTERMOST_LOG_FORMAT` | json | Log format: `json` for production, `text` for development |
| `MATTERMOST_API_VERSION` | v4 | Mattermost API version |
| `MATTERMOST_HTTP_ALLOWED_HOSTS` | — | Extra allowed `Host` values for HTTP (JSON array or comma-separated) |
| `MATTERMOST_HTTP_ALLOWED_ORIGINS` | — | Extra allowed `Origin` values for HTTP (JSON array or comma-separated) |

## HTTP transport security

`static_token` over HTTP is never blocked, but it serves an unauthenticated endpoint acting with the shared
token — the server logs a warning at startup (louder on a non-loopback bind). For networked access, front it
with an authenticating proxy or use `client_token` / `oauth_proxy` (see [Authentication](authentication.md)).

The HTTP transport turns on DNS-rebinding protection automatically (`host_origin_protection="auto"`):

- **Loopback bind** (`127.0.0.1` / `localhost` / `::1`) — `Host` and `Origin` are validated. Normal MCP
  clients (loopback `Host`, no `Origin`) pass; an unknown `Host` gets `421`, a foreign `Origin` gets `403`.
- **Non-loopback bind** (`0.0.0.0`, LAN IP) — validation is **off** until you set an allowlist, so it does
  not protect a networked deployment on its own.

Declare allowlists with `MATTERMOST_HTTP_ALLOWED_HOSTS` / `MATTERMOST_HTTP_ALLOWED_ORIGINS` (JSON array or
comma-separated) — e.g. the public host behind a reverse proxy. `X-Forwarded-*` headers are not trusted.

**Troubleshooting:** `421 Misdirected Request` → add the client's `Host` to `MATTERMOST_HTTP_ALLOWED_HOSTS`.
`403 Forbidden Origin` → add the browser `Origin` to `MATTERMOST_HTTP_ALLOWED_ORIGINS`.

## Environment File

You can also use a `.env` file in the working directory:

```bash
MATTERMOST_URL=https://mattermost.example.com
MATTERMOST_TOKEN=your-token-here
MATTERMOST_TIMEOUT=60
MATTERMOST_LOG_LEVEL=DEBUG
```
