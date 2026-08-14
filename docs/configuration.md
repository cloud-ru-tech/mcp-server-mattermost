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
| `MATTERMOST_HTTP_HOST_ORIGIN_PROTECTION` | — | Host/Origin protection: `off`, `auto`, or `strict` (unset: FastMCP's own default, off) |
| `MATTERMOST_HTTP_ALLOWED_HOSTS` | — | Extra allowed `Host` values for HTTP (JSON array or comma-separated) |
| `MATTERMOST_HTTP_ALLOWED_ORIGINS` | — | Extra allowed `Origin` values for HTTP (JSON array or comma-separated) |

## HTTP transport security

`static_token` over HTTP serves an unauthenticated endpoint acting with the shared token — the server warns
but never blocks. See [Authentication → HTTP transport](authentication.md#http-transport) for that auth
posture and its remediation. This section covers the transport-level Host/Origin protection, which applies
to every auth mode.

DNS-rebinding protection is **off unless you turn it on** — an upgrade never starts rejecting traffic that
worked before. Set `MATTERMOST_HTTP_HOST_ORIGIN_PROTECTION`:

| Value | Effect |
|-------|--------|
| unset | Defers to FastMCP's own `FASTMCP_HTTP_HOST_ORIGIN_PROTECTION`, which is off by default |
| `off` | Never validate, overriding `FASTMCP_HTTP_HOST_ORIGIN_PROTECTION` |
| `auto` | Validate per connection, by the local address it arrived on |
| `strict` | Validate every connection, whatever address it arrived on |

The setting applies to every way of serving the app — the `mcp-server-mattermost --http` command,
`fastmcp run`, a standalone ASGI server, and this app mounted into a parent Starlette/FastAPI application.

Declare allowlists with `MATTERMOST_HTTP_ALLOWED_HOSTS` / `MATTERMOST_HTTP_ALLOWED_ORIGINS` (JSON array or
comma-separated) — e.g. the public host behind a reverse proxy. They have no effect while protection is off;
the server logs a warning when it sees that combination.

Under `auto`, each connection is classified by the **local address it arrived on**, not by the bind address.
Cells name the headers that get validated; column heads drop the `MATTERMOST_HTTP_` prefix.

| Connection arrived on | No allowlist | `ALLOWED_HOSTS` set | `ALLOWED_ORIGINS` only |
|-----------------------|--------------|---------------------|------------------------|
| `127.0.0.1`, `localhost`, `::1` | `Host` + `Origin` | `Host` + `Origin` | `Host` + `Origin` |
| LAN or public address | none, unless the request carries `Host: localhost` — then `Origin` | `Host` + `Origin` | `Origin` |

**A loopback bind is a special case of the first row.** On `MCP_HOST=127.0.0.1` (the default) FastMCP adds
the bind address to the allowlist, so with `auto` every connection has its `Host` validated — a reverse proxy
that forwards a public `Host` needs it in `MATTERMOST_HTTP_ALLOWED_HOSTS`. The same holds for a proxy or
health checker reaching a `0.0.0.0` bind over `127.0.0.1`.

Accepted in every configuration: `Host: 127.0.0.1` / `localhost` / `::1`, the local address the connection
arrived on, and any loopback `Origin` when `Host` is loopback. A request with no `Origin` header — every
non-browser MCP client — is never rejected on `Origin`.

Allowlist entries are `fnmatch` glob patterns, which is looser than it looks:

- `*.example.com` does **not** match the apex `example.com`. List both if you need both.
- `*` crosses dots, so `*.example.com` matches `a.b.example.com` — and `evil.attacker.com.example.com`.
  Prefer exact hostnames over wildcards where you can.
- A bare `*` matches everything, disabling the check for that header.

`X-Forwarded-Host` is ignored and the arrival address is never taken from a header, so a proxy cannot talk
the guard into trusting a hostname. `X-Forwarded-Proto` **is** honored: uvicorn's proxy-header handling is on
by default for peers in `forwarded_allow_ips` (loopback unless `FORWARDED_ALLOW_IPS` says otherwise) and it
sets the scheme used for the same-origin comparison.

Four behaviors behind a surprising `421`/`403`:

- `MATTERMOST_HTTP_ALLOWED_ORIGINS` **alone** drops the same-origin exemption for non-loopback arrivals: a
  same-origin browser request then gets `403` unless its origin is listed. Set
  `MATTERMOST_HTTP_ALLOWED_HOSTS` as well, or list every origin the browser sends.
- `Host` matching ignores the port, `Origin` matching includes it. `https://app.example.com` means port 443,
  so list `https://app.example.com:8443` explicitly.
- A request arriving off-loopback but carrying `Host: localhost` has its `Origin` validated even with no
  allowlist set — a proxy using `proxy_set_header Host localhost` needs its `Origin` listed.
- Behind a proxy terminating TLS, the browser sends `Origin: https://…` while the server still sees scheme
  `http`, so the same-origin exemption misses. See the troubleshooting table below.

Every rejection is logged at `WARNING` with the offending `Host`/`Origin` and the variable to add it to; the
response body itself stays a bare `421`/`403`.

**Troubleshooting**

| Symptom | Fix |
|---------|-----|
| `421 Misdirected Request` | Add the client's `Host` to `MATTERMOST_HTTP_ALLOWED_HOSTS` |
| `403 Forbidden Origin` | Add the browser `Origin`, with port, to `MATTERMOST_HTTP_ALLOWED_ORIGINS` |
| `403` behind a TLS-terminating proxy, `Origin` looks correct | Have the proxy send `X-Forwarded-Proto: https`, and set `FORWARDED_ALLOW_IPS` to the proxy's address if it is not on loopback |
| Allowlist appears to be ignored | `MATTERMOST_HTTP_HOST_ORIGIN_PROTECTION` is unset or `off` |

## Environment File

You can also use a `.env` file in the working directory:

```bash
MATTERMOST_URL=https://mattermost.example.com
MATTERMOST_TOKEN=your-token-here
MATTERMOST_TIMEOUT=60
MATTERMOST_LOG_LEVEL=DEBUG
```
