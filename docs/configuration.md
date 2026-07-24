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

`static_token` over HTTP serves an unauthenticated endpoint acting with the shared token — the server warns
but never blocks. See [Authentication → HTTP transport](authentication.md#http-transport) for that auth
posture and its remediation. This section covers the transport-level Host/Origin protection, which applies
to every auth mode.

The HTTP transport turns on DNS-rebinding protection automatically (`host_origin_protection="auto"`). Each
connection is classified by the **local address it arrived on**, not by the bind address: a server bound to
`0.0.0.0` validates a request that reaches it through `127.0.0.1` and skips one that reaches it through a
LAN address.

Declare allowlists with `MATTERMOST_HTTP_ALLOWED_HOSTS` / `MATTERMOST_HTTP_ALLOWED_ORIGINS` (JSON array or
comma-separated) — e.g. the public host behind a reverse proxy. Cells name the headers that get validated;
column heads drop the `MATTERMOST_HTTP_` prefix.

| Connection arrived on | No allowlist | `ALLOWED_HOSTS` set | `ALLOWED_ORIGINS` only |
|-----------------------|--------------|---------------------|------------------------|
| `127.0.0.1`, `localhost`, `::1` | `Host` + `Origin` | `Host` + `Origin` | `Host` + `Origin` |
| LAN or public address | none | `Host` + `Origin` | `Origin` |

Accepted in every configuration: `Host: 127.0.0.1` / `localhost` / `::1`, the local address the connection
arrived on, and any loopback `Origin` when `Host` is loopback. A request with no `Origin` header — every
non-browser MCP client — is never rejected on `Origin`. Allowlist entries are glob patterns
(`*.example.com`). `X-Forwarded-*` headers are not trusted.

**Upgrade note:** a same-host reverse proxy or health checker that connects over `127.0.0.1` while
preserving a public `Host`/`Origin` is validated even on a `0.0.0.0` bind — list its values in
`MATTERMOST_HTTP_ALLOWED_HOSTS` / `MATTERMOST_HTTP_ALLOWED_ORIGINS`.

Three behaviors behind a surprising `421`/`403`:

- `MATTERMOST_HTTP_ALLOWED_ORIGINS` **alone** drops the same-origin exemption for non-loopback arrivals: a
  same-origin browser request then gets `403` unless its origin is listed. Set
  `MATTERMOST_HTTP_ALLOWED_HOSTS` as well, or list every origin the browser sends.
- `Host` matching ignores the port, `Origin` matching includes it. `https://app.example.com` means port 443,
  so list `https://app.example.com:8443` explicitly.
- A request arriving off-loopback but carrying `Host: localhost` has its `Origin` validated even with no
  allowlist set — a proxy using `proxy_set_header Host localhost` needs its `Origin` listed.

**Troubleshooting**

| Symptom | Fix |
|---------|-----|
| `421 Misdirected Request` | Add the client's `Host` to `MATTERMOST_HTTP_ALLOWED_HOSTS` |
| `403 Forbidden Origin` | Add the browser `Origin`, with port, to `MATTERMOST_HTTP_ALLOWED_ORIGINS` |

## Environment File

You can also use a `.env` file in the working directory:

```bash
MATTERMOST_URL=https://mattermost.example.com
MATTERMOST_TOKEN=your-token-here
MATTERMOST_TIMEOUT=60
MATTERMOST_LOG_LEVEL=DEBUG
```
