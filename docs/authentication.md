# Authentication

The MCP server supports three authentication modes selected by the
`MATTERMOST_AUTH_MODE` environment variable. Each mode targets a different
deployment scenario.

## Choosing a mode

| Mode | Best for | Token source |
|------|----------|--------------|
| `static_token` (default) | Local stdio clients, bot accounts, single-user automation | Bot or personal access token in `MATTERMOST_TOKEN` |
| `client_token` | HTTP transport where each client already has a Mattermost token | `Authorization: Bearer <token>` from the MCP client |
| `oauth_proxy` | Remote HTTP MCP clients where each user signs in through Mattermost SSO | OAuth flow via Mattermost OAuth 2.0 Application |

## `static_token`

The simplest mode. The server uses one bot or personal access token for every
Mattermost API call. All MCP tool calls act as that single identity.

### When to use

- Local stdio with Claude Desktop, Cursor, or Claude Code
- Server-side automation where a single shared identity is acceptable
- Initial trial and quickstart

### Setup

1. Get a Mattermost token: **System Console → Integrations → Bot Accounts**, or
   **Profile → Security → Personal Access Tokens** for your own account.
2. Set `MATTERMOST_URL` and `MATTERMOST_TOKEN` and run the server. See
   [Quick Start](quickstart.md) for client-specific configuration.

### Token permissions

The token needs these Mattermost permissions for full functionality:

- `view_team` — list teams
- `list_team_channels` — list public channels
- `read_channel` — read channel messages
- `create_post` — send messages
- `delete_post` — delete messages
- `add_reaction` / `remove_reaction` — manage reactions
- `manage_channels` — create channels (optional)

Bot accounts get most permissions automatically. Personal access tokens inherit
the user's permissions.

## `client_token`

HTTP transport mode where each MCP client sends its own Mattermost token. The
server validates the token against `GET /api/v4/users/me` before invoking tools,
then uses that token for downstream Mattermost API calls.

### When to use

- HTTP deployments with multiple users who each hold a Mattermost token
- Programmatic integrations with rotating or per-request tokens
- Migration step before adopting `oauth_proxy`

### Setup

```bash
export MATTERMOST_URL=https://mattermost.example.com
export MATTERMOST_AUTH_MODE=client_token
mcp-server-mattermost
```

MCP clients send their token in the `Authorization: Bearer <mattermost-token>`
header on every request.

### Behavioral note

Requests without a validated bearer token return `401`. There is no fallback to
`MATTERMOST_TOKEN`, even if it is set. If you need a single shared identity,
use `static_token` instead.

The deprecated `MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS=true` is now an alias for
this mode. Prefer setting `MATTERMOST_AUTH_MODE=client_token` explicitly.

## `oauth_proxy`

Each MCP client authenticates with the MCP server through the standard MCP
OAuth flow. FastMCP `OAuthProxy` provides the OAuth Authorization Server
endpoints (`/register`, `/authorize`, `/token`) and proxies the browser login
to a Mattermost OAuth 2.0 Application. Mattermost performs the actual login
through its configured authentication provider (local accounts, SSO, Keycloak),
and the MCP server keeps the resulting Mattermost token to forward in
subsequent API calls on behalf of the user.

### When to use

- Remote HTTP MCP clients where each user must act as themselves in Mattermost
- Production deployments with audit requirements
- Setups where Mattermost SSO (Keycloak, Okta, etc.) is the source of truth

Do not set `MATTERMOST_TOKEN` in this mode; tool calls use the token obtained
from the authenticated user.

### Architecture

```text
MCP Client (Claude Code)
    │
    │  1. DCR + OAuth flow with the MCP server
    ▼
MCP Server (FastMCP OAuthProxy)
    │
    │  2. Browser redirect to Mattermost /oauth/authorize
    ▼
Mattermost OAuth Application
    │
    │  3. Local login or SSO (Keycloak, ...)
    ▼
Browser redirected to MCP Server /oauth/callback/mm
    │
    │  4. MCP Server stores upstream Mattermost token
    ▼
MCP Client receives MCP access token, calls tools normally
```

### Step 1 — Register the Mattermost OAuth App

In Mattermost, enable OAuth service provider support
(`ServiceSettings.EnableOAuthServiceProvider=true`, see
[Mattermost integration configuration docs](https://docs.mattermost.com/administration-guide/configure/integrations-configuration-settings.html#enable-oauth-2-0-service-provider)),
then register the App under **System Console → Integrations →
OAuth 2.0 Applications**.

| Field | Public client mode | Confidential client mode |
|-------|--------------------|--------------------------|
| Is Trusted | Yes | Yes |
| Is Public Client | Yes | No |
| Client Secret | Not used | Required (Mattermost generates it) |
| Callback URL | `{MCP public URL}/oauth/callback/mm` | `{MCP public URL}/oauth/callback/mm` |

The callback URL must match `MATTERMOST_OAUTH_MCP_PUBLIC_URL` +
`MATTERMOST_OAUTH_CALLBACK_PATH` exactly. Default callback path is
`/oauth/callback/mm`.

Display Name and Homepage are end-user-visible on the OAuth consent screen but
do not affect the flow. Set them to whatever your users will recognise.

Use **confidential** mode in production. Use **public** mode only when
Mattermost is configured for public OAuth clients, typically for development.

### Step 2 — Configure the MCP server

Confidential client (production):

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

Public client (development or public-OAuth setups):

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

`MATTERMOST_OAUTH_JWT_SIGNING_KEY` is required for public clients (FastMCP
needs a stable secret for signing its own JWTs because no upstream client
secret is available). Use a long, random value and keep it stable across
restarts.

#### URL roles

Three URLs serve different purposes:

| Variable | Reachable from | Purpose |
|----------|----------------|---------|
| `MATTERMOST_URL` | MCP server process | Server-to-server API calls and the OAuth token endpoint |
| `MATTERMOST_OAUTH_MATTERMOST_PUBLIC_URL` | User's browser | Browser redirect to `/oauth/authorize` |
| `MATTERMOST_OAUTH_MCP_PUBLIC_URL` | User's browser | OAuth metadata, callback, and DCR endpoints |

In Docker or Kubernetes, `MATTERMOST_URL` is often an internal service URL
(`http://mattermost:8065`). `MATTERMOST_OAUTH_MATTERMOST_PUBLIC_URL` must be
externally reachable; if it is left unset, it falls back to `MATTERMOST_URL`,
which usually fails when the internal URL is not browser-reachable.

### Step 3 — Connect the MCP client

The MCP client does not need to be registered in Mattermost. FastMCP handles
**Dynamic Client Registration** (DCR) locally between the MCP client and the
MCP server. The MCP client posts its own metadata (including its callback URL)
to the MCP server's `/register` endpoint and receives back a `client_id`.

For Claude Code:

```bash
claude mcp add --transport http mattermost https://mcp.example.com/mcp
```

Do not pass `--client-id` for this server. Claude Code uses DCR with the MCP
server, and the MCP server uses the fixed Mattermost OAuth App credentials
upstream.

If a previous connection cached tokens for a different OAuth mode, remove or
reconnect the MCP server in the client before retrying.

#### Allowed MCP client redirect URIs

By default the proxy accepts only loopback redirect URIs
(`http://localhost:*`, `http://127.0.0.1:*`). This covers Claude Code, Claude
Desktop, and most local IDE plugins. For non-loopback MCP clients (a hosted
web client, a remote agent, a browser-based client behind your own domain),
set `MATTERMOST_OAUTH_ALLOWED_REDIRECT_URIS` to a JSON array of glob patterns:

```bash
MATTERMOST_OAUTH_ALLOWED_REDIRECT_URIS='["https://*.example.com/*"]'
```

Clients whose registered redirect URI does not match any pattern are rejected
at DCR registration time.

### Keycloak and SSO

The MCP server does not register directly in Keycloak. Keycloak (or any other
SSO provider) is used by Mattermost itself for user login. Configure the
Keycloak-to-Mattermost login path in Mattermost first; then register the MCP
OAuth App in Mattermost as described above. Mattermost issues the OAuth token
that the MCP server uses for API calls.

### Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Browser shows "can't connect" after consent | `MATTERMOST_OAUTH_MATTERMOST_PUBLIC_URL` is unset and `MATTERMOST_URL` is internal | Set `MATTERMOST_OAUTH_MATTERMOST_PUBLIC_URL` to the externally reachable Mattermost URL |
| MCP client gets `400 Bad Request` at `/register` | Client's redirect URI is not in `MATTERMOST_OAUTH_ALLOWED_REDIRECT_URIS` | Add the client's domain to the allow-list |
| Mattermost rejects the authorize request | `MATTERMOST_OAUTH_MCP_PUBLIC_URL` + `MATTERMOST_OAUTH_CALLBACK_PATH` differs from the App's Callback URL | Make them match exactly, including trailing path |
| Settings refuses to load: "must use HTTPS unless localhost" | `MATTERMOST_OAUTH_MCP_PUBLIC_URL` is plain HTTP and not localhost | Use HTTPS in production, or test with `http://localhost:<port>` |
| Old MCP client cached the wrong tokens | Previous connection used a different auth mode | Remove and re-add the server in the MCP client |

## Configuration reference

All authentication-related environment variables. For non-auth settings
(timeouts, logging, SSL), see [Configuration](configuration.md).

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MATTERMOST_AUTH_MODE` | No | `static_token` | `static_token`, `client_token`, or `oauth_proxy` |
| `MATTERMOST_TOKEN` | Conditional | — | Required for `static_token`. Bot or personal access token |
| `MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS` | No | false | Deprecated alias for `MATTERMOST_AUTH_MODE=client_token`. Conflicts with an explicit `MATTERMOST_AUTH_MODE` set to anything else |
| `MATTERMOST_OAUTH_CLIENT_ID` | Conditional | — | Required for `oauth_proxy`. Mattermost OAuth App ID |
| `MATTERMOST_OAUTH_CLIENT_TYPE` | No | `confidential` | `public` or `confidential` |
| `MATTERMOST_OAUTH_CLIENT_SECRET` | Conditional | — | Required for confidential OAuth Apps |
| `MATTERMOST_OAUTH_JWT_SIGNING_KEY` | Conditional | — | Required for public OAuth Apps; optional for confidential |
| `MATTERMOST_OAUTH_MCP_PUBLIC_URL` | Conditional | — | Required for `oauth_proxy`. Public base URL of this MCP server. Must be HTTPS unless localhost |
| `MATTERMOST_OAUTH_MATTERMOST_PUBLIC_URL` | No | `MATTERMOST_URL` | Browser-facing Mattermost URL for OAuth redirects |
| `MATTERMOST_OAUTH_CALLBACK_PATH` | No | `/oauth/callback/mm` | Callback path registered in the Mattermost OAuth App |
| `MATTERMOST_OAUTH_REQUIRE_CONSENT` | No | true | Show the FastMCP consent screen before redirecting to Mattermost |
| `MATTERMOST_OAUTH_ALLOWED_REDIRECT_URIS` | No | `["http://localhost:*", "http://127.0.0.1:*"]` | JSON array of glob patterns for MCP client redirect URIs accepted via DCR |
| `MATTERMOST_OAUTH_FALLBACK_ACCESS_TOKEN_EXPIRY_SECONDS` | No | — | Fallback access token TTL in seconds (≥1). Used only when Mattermost omits `expires_in` in the token response |

!!! warning "Security considerations"
    In `client_token` and `oauth_proxy` modes, any user who can reach the MCP
    server's HTTP endpoint and has a valid Mattermost account can execute MCP
    tools under their own identity. Protect the MCP server with network-level
    access controls such as a firewall, VPN, or trusted reverse proxy.
