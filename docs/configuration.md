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
| `MATTERMOST_ALLOW_UNAUTHENTICATED_HTTP` | false | Allow `static_token` over HTTP — loopback bind only. See [Authentication](authentication.md#static_token) |
| `MATTERMOST_HTTP_ALLOWED_HOSTS` | — | Extra allowed `Host` values for HTTP (JSON array or comma-separated) |
| `MATTERMOST_HTTP_ALLOWED_ORIGINS` | — | Extra allowed `Origin` values for HTTP (JSON array or comma-separated) |

## HTTP transport security

The HTTP transport enables DNS-rebinding protection automatically (`host_origin_protection="auto"`):
loopback deployments reject unknown `Host`/`Origin` headers, while non-loopback binds are unaffected
until you declare an allowlist. Set `MATTERMOST_HTTP_ALLOWED_HOSTS` / `MATTERMOST_HTTP_ALLOWED_ORIGINS`
to enforce strict validation for a networked deployment (e.g. the public host behind a reverse proxy).
`X-Forwarded-*` headers are not trusted automatically.

## Environment File

You can also use a `.env` file in the working directory:

```bash
MATTERMOST_URL=https://mattermost.example.com
MATTERMOST_TOKEN=your-token-here
MATTERMOST_TIMEOUT=60
MATTERMOST_LOG_LEVEL=DEBUG
```
