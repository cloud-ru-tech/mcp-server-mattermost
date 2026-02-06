# Configuration

All configuration is done via environment variables with the `MATTERMOST_` prefix.

## Required Variables

| Variable | Description |
|----------|-------------|
| `MATTERMOST_URL` | Mattermost server URL (e.g., `https://mattermost.example.com`) |
| `MATTERMOST_TOKEN` | Bot or personal access token |

## Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MATTERMOST_TIMEOUT` | 30 | Request timeout in seconds (1-300) |
| `MATTERMOST_MAX_RETRIES` | 3 | Maximum retry attempts for failed requests (0-10) |
| `MATTERMOST_VERIFY_SSL` | true | Verify SSL certificates |
| `MATTERMOST_LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `MATTERMOST_LOG_FORMAT` | json | Log format: `json` for production, `text` for development |
| `MATTERMOST_API_VERSION` | v4 | Mattermost API version |

## Environment File

You can also use a `.env` file in the working directory:

```bash
MATTERMOST_URL=https://mattermost.example.com
MATTERMOST_TOKEN=your-token-here
MATTERMOST_TIMEOUT=60
MATTERMOST_LOG_LEVEL=DEBUG
```

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
