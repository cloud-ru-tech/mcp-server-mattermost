# Configuration

All configuration is done via environment variables with the `MATTERMOST_` prefix.

## Required Variables

| Variable | Description |
|----------|-------------|
| `MATTERMOST_URL` | Mattermost server URL (e.g., `https://mattermost.example.com`) |

## Conditional Variables

| Variable | Description |
|----------|-------------|
| `MATTERMOST_TOKEN` | Bot or personal access token. MATTERMOST_TOKEN is required only when per-client token authentication (MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS) is not enabled. |

## Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MATTERMOST_TIMEOUT` | 30 | Request timeout in seconds (1-300) |
| `MATTERMOST_MAX_RETRIES` | 3 | Maximum retry attempts for failed requests (0-10) |
| `MATTERMOST_VERIFY_SSL` | true | Verify SSL certificates |
| `MATTERMOST_LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `MATTERMOST_LOG_FORMAT` | json | Log format: `json` for production, `text` for development |
| `MATTERMOST_API_VERSION` | v4 | Mattermost API version |
| `MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS` | false | Allow HTTP clients to authenticate with their own Mattermost tokens |

## Environment File

You can also use a `.env` file in the working directory:

```bash
MATTERMOST_URL=https://mattermost.example.com
MATTERMOST_TOKEN=your-token-here
MATTERMOST_TIMEOUT=60
MATTERMOST_LOG_LEVEL=DEBUG
```

## Per-Client Token Authentication

By default, the server uses the `MATTERMOST_TOKEN` environment variable for all API requests. When `MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS` is set to `true`, HTTP clients (e.g., over SSE transport) can pass their own Mattermost token via the `Authorization: Bearer <token>` header.

**How it works:**

1. The client sends a bearer token in the `Authorization` header
2. The server validates the token by calling `GET /api/v4/users/me` on the Mattermost server
3. If valid, the client's token is used for all subsequent API requests in that session
4. If invalid, the server responds with `401 Unauthorized`

This is useful in multi-user environments where each user should act under their own Mattermost identity rather than a shared bot account.

!!! note
    This feature only applies to HTTP-based transports (SSE, StreamableHTTP). When using stdio transport (e.g., Claude Desktop), the server always uses `MATTERMOST_TOKEN`.

## Token Permissions

The bot token needs these permissions for full functionality:

| Permission | Required For |
|------------|--------------|
| `create_post` | Sending messages |
| `read_channel` | Reading channel messages |
| `manage_channel_members` | Adding users to channels |
| `create_direct_channel` | Creating DM channels |
| `upload_files` | File uploads |

For read-only usage, only `read_channel` permission is needed.
