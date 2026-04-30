# Configuration

All configuration is done via environment variables with the `MATTERMOST_` prefix.

## Required Variables

| Variable | Description |
|----------|-------------|
| `MATTERMOST_URL` | Mattermost server URL (e.g., `https://mattermost.example.com`) |

## Conditional Variables

| Variable | Description |
|----------|-------------|
| `MATTERMOST_TOKEN` | Bot or personal access token. Required only when `MATTERMOST_AUTH_MODE=static_token`. |
| `MATTERMOST_OAUTH_CLIENT_ID` | Mattermost OAuth App client ID. Required when `MATTERMOST_AUTH_MODE=oauth_proxy`. |
| `MATTERMOST_OAUTH_CLIENT_SECRET` | Mattermost OAuth App secret. Required for confidential OAuth Apps. |
| `MATTERMOST_OAUTH_MCP_PUBLIC_URL` | Public base URL of this MCP server. Required for `oauth_proxy`. |

## Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MATTERMOST_TIMEOUT` | 30 | Request timeout in seconds (1-300) |
| `MATTERMOST_MAX_RETRIES` | 3 | Maximum retry attempts for failed requests (0-10) |
| `MATTERMOST_VERIFY_SSL` | true | Verify SSL certificates |
| `MATTERMOST_LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `MATTERMOST_LOG_FORMAT` | json | Log format: `json` for production, `text` for development |
| `MATTERMOST_API_VERSION` | v4 | Mattermost API version |
| `MATTERMOST_AUTH_MODE` | static_token | Authentication mode: `static_token`, `client_token`, or `oauth_proxy` |
| `MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS` | false | Deprecated alias for `MATTERMOST_AUTH_MODE=client_token` |
| `MATTERMOST_OAUTH_CLIENT_TYPE` | confidential | Mattermost OAuth App type: `public` or `confidential` |
| `MATTERMOST_OAUTH_MATTERMOST_PUBLIC_URL` | `MATTERMOST_URL` | Browser-facing Mattermost URL for OAuth redirects |
| `MATTERMOST_OAUTH_CALLBACK_PATH` | `/oauth/callback/mm` | Callback path registered in the Mattermost OAuth App |
| `MATTERMOST_OAUTH_JWT_SIGNING_KEY` | — | Required for public OAuth Apps; optional for confidential OAuth Apps |
| `MATTERMOST_OAUTH_REQUIRE_CONSENT` | true | Show the FastMCP consent screen before redirecting to Mattermost |
| `MATTERMOST_OAUTH_FALLBACK_ACCESS_TOKEN_EXPIRY_SECONDS` | — | Fallback token TTL |

## Environment File

You can also use a `.env` file in the working directory:

```bash
MATTERMOST_URL=https://mattermost.example.com
MATTERMOST_TOKEN=your-token-here
MATTERMOST_TIMEOUT=60
MATTERMOST_LOG_LEVEL=DEBUG
```

## Authentication Modes

`MATTERMOST_AUTH_MODE` selects one authentication strategy per server process.

### `static_token`

Default mode. The server uses `MATTERMOST_TOKEN` for every Mattermost API request.
Use this for stdio, bot accounts, and single-user deployments.

### `client_token`

HTTP clients send their own Mattermost token in `Authorization: Bearer <token>`.
The server validates it through `GET /api/v4/users/me` and then uses that token for
Mattermost API calls.

`MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS=true` is a deprecated alias for this mode.

### `oauth_proxy`

Remote MCP clients authenticate with the MCP server through the standard MCP OAuth flow.
FastMCP `OAuthProxy` provides the OAuth Authorization Server endpoints for MCP clients
(`/register`, `/authorize`, `/token`) and proxies the browser login to Mattermost OAuth.
Mattermost performs login through its configured authentication provider, for example
Keycloak SSO, and the MCP server stores the resulting Mattermost user token as an
upstream token.

Use this mode when each MCP client must act as the Mattermost user who approved the
OAuth flow. Do not set `MATTERMOST_TOKEN` in this mode; tool calls use the token obtained
from the authenticated user.

#### Mattermost OAuth App

Mattermost must have OAuth service provider support enabled. In the Mattermost System
Console, check the integration setting named **Enable OAuth 2.0 Service Provider**. On
self-hosted Mattermost this maps to `ServiceSettings.EnableOAuthServiceProvider=true`.
See the Mattermost integration configuration docs for the upstream setting:
<https://docs.mattermost.com/administration-guide/configure/integrations-configuration-settings.html#enable-oauth-2-0-service-provider>.

Create the OAuth app in Mattermost under **Integrations** -> **OAuth 2.0 Applications**.
The callback URL is fixed from Mattermost's point of view:

```text
{MATTERMOST_OAUTH_MCP_PUBLIC_URL}{MATTERMOST_OAUTH_CALLBACK_PATH}
```

For example:

```text
https://mcp.example.com/oauth/callback/mm
```

Mattermost OAuth App settings:

| Setting | Public client mode | Confidential client mode |
|---------|--------------------|--------------------------|
| Is Trusted | Yes | Yes |
| Is Public Client | Yes | No |
| Client Secret | Empty | Required |
| Callback URL | `{MCP public URL}/oauth/callback/mm` | `{MCP public URL}/oauth/callback/mm` |
| PKCE | S256 | S256 |

Use confidential mode for production when Mattermost provides a client secret. Use public
mode only for development or environments where the Mattermost OAuth App is explicitly
created as a public client; public mode requires a stable `MATTERMOST_OAUTH_JWT_SIGNING_KEY`.

#### MCP Server Environment

Confidential production example:

```bash
MCP_TRANSPORT=http
MCP_HOST=0.0.0.0
MCP_PORT=8000

MATTERMOST_AUTH_MODE=oauth_proxy
MATTERMOST_URL=https://mattermost.internal
MATTERMOST_OAUTH_MATTERMOST_PUBLIC_URL=https://mattermost.example.com
MATTERMOST_OAUTH_MCP_PUBLIC_URL=https://mcp.example.com
MATTERMOST_OAUTH_CLIENT_ID=<mattermost-oauth-app-id>
MATTERMOST_OAUTH_CLIENT_TYPE=confidential
MATTERMOST_OAUTH_CLIENT_SECRET=<mattermost-oauth-app-secret>
```

Public-client example:

```bash
MCP_TRANSPORT=http
MCP_HOST=0.0.0.0
MCP_PORT=8000

MATTERMOST_AUTH_MODE=oauth_proxy
MATTERMOST_URL=https://mattermost.example.com
MATTERMOST_OAUTH_MATTERMOST_PUBLIC_URL=https://mattermost.example.com
MATTERMOST_OAUTH_MCP_PUBLIC_URL=https://mcp.example.com
MATTERMOST_OAUTH_CLIENT_ID=<mattermost-oauth-app-id>
MATTERMOST_OAUTH_CLIENT_TYPE=public
MATTERMOST_OAUTH_JWT_SIGNING_KEY=<stable-signing-key>
```

`MATTERMOST_URL` is the URL reachable by the MCP server process. In Docker this is often
an internal service URL such as `http://mattermost:8065`. `MATTERMOST_OAUTH_MATTERMOST_PUBLIC_URL`
is the URL opened in the user's browser during OAuth login.

#### MCP Client Registration

The MCP client does not need to be registered in Mattermost. FastMCP handles Dynamic Client
Registration locally between the MCP client and this server. For Claude Code, do not pass a
fixed `--client-id` for this server; let Claude Code register dynamically so its loopback
callback, such as `http://localhost:<port>/callback`, is accepted by the MCP server.

Connect Claude Code to a remote HTTP server with:

```bash
claude mcp add --transport http mattermost https://mcp.example.com/mcp
```

If a previous connection attempted a different OAuth mode and cached tokens, remove or
reconnect the MCP server in the client before retrying.

#### Keycloak and SSO

The MCP server does not register directly in Keycloak. Keycloak is used by Mattermost for
SSO login, and Mattermost issues the OAuth token that the MCP server uses for API calls.
Configure the Keycloak-to-Mattermost login path in Mattermost first; then register the MCP
OAuth App in Mattermost as described above.

!!! warning "Security Considerations"
    In `client_token` and `oauth_proxy` modes, any user who can reach the MCP server's
    HTTP endpoint and has a valid Mattermost account can execute MCP tools under their
    own identity. Protect the MCP server with network-level access controls such as a
    firewall, VPN, or trusted reverse proxy.

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
