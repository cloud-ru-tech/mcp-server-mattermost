# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Shared HTTP connection pool: the Mattermost HTTP client is created once and
  reused across all tool calls (sequential and concurrent), eliminating per-call
  TCP/TLS handshakes and TIME_WAIT churn. Pool limits are configurable via
  `MATTERMOST_MAX_CONNECTIONS` (default 100),
  `MATTERMOST_MAX_KEEPALIVE_CONNECTIONS` (default 20), and
  `MATTERMOST_KEEPALIVE_EXPIRY` (default 30.0s). The bearer token is sent
  per-request and is never stored in the shared client's default headers, so a
  single pool safely serves multiple users without mixing tokens. Token
  verification in `client_token`/`oauth_proxy` mode goes through the same pool
  and therefore obeys the same limits.
- Embedded and library use share the pool too. It is owned by the server
  lifespan but reached through an internal registry rather than the lifespan
  context, so adding these tools to your own FastMCP server (`add_tool`,
  `import_server`, `mount`) or driving `get_client()` directly keeps working
  exactly as before — and now pools connections as well, with no lifespan
  wiring on your side.

### Changed
- `MATTERMOST_KEEPALIVE_EXPIRY` defaults to 30s rather than httpx's 5s. An agent
  typically spends 5-30s between two tool calls; at 5s every one of them
  redialled, which defeated the point of the pool. Measured: with a 7s gap, 5s
  opens a second connection and 30s reuses the first.
- The pool imposes a process-wide ceiling of `MATTERMOST_MAX_CONNECTIONS`
  in-flight requests, which per-call clients did not have. Requests beyond it
  wait, and on timeout report the pool and the variable to raise instead of a
  misleading "upstream request timed out".
- Transport errors on `GET`/`HEAD`/`OPTIONS`/`PUT`/`DELETE` are now retried
  immediately (within `MATTERMOST_MAX_RETRIES`). Pooled sockets can be closed by
  the server while idle between two tool calls; `POST` is never replayed, and
  read/write timeouts are still not retried.
- Setting only `MATTERMOST_MAX_CONNECTIONS` below the keepalive default no
  longer aborts startup naming a variable you never set — the keepalive cap is
  clamped to it. An explicit conflict between the two is still an error.
- Log lifecycle: the pool logs one INFO when created and one when closed, and
  warns when `MATTERMOST_MAX_KEEPALIVE_CONNECTIONS=0` or
  `MATTERMOST_KEEPALIVE_EXPIRY=0` disables connection reuse. The per-call
  "Initializing Mattermost API client" line moved to DEBUG.

### Fixed
- File uploads now send the correct `multipart/form-data` Content-Type. The
  client previously carried a default `Content-Type: application/json` header
  that httpx did not override for multipart requests. Every other request is
  unchanged and still sends `application/json`.
- A second, still-open session no longer breaks when the first one disconnects.
  FastMCP closes a server's lifespan stack on the first session's exit without
  waiting for the others; the pool is now retired rather than closed outright,
  so in-flight requests finish and the next call gets a fresh pool.
- Server shutdown attempts both the pool teardown and the auth provider
  teardown, and reports both failures rather than discarding the first.
- `Post.file_ids` defaults to an empty list — Mattermost ≤ v10.4.0 omits the key on posts
  without attachments, which broke parsing in every tool that returns posts
  ([#27](https://github.com/cloud-ru-tech/mcp-server-mattermost/issues/27))
- Allowlists accept bracketed IPv6 literals (`[::1]`), which previously aborted startup with a JSON
  parser error; a value reducing to an empty list is now treated as unset rather than as an allowlist
  matching nothing.
- Raised the `pydantic-settings` floor to `>=2.7`. The declared `>=2.0` allowed versions without
  `NoDecode`, where the package failed to import at all — on stdio as well as HTTP.

### Security
- The shared HTTP pool is transport-only: its cookie jar is disabled, so a
  `Set-Cookie` from one user's response is never stored and replayed on another
  user's request through the pool (`client_token`/`oauth_proxy` modes). This now
  covers token verification too, which previously used a client of its own.
- The pool is never published in the FastMCP lifespan context. FastMCP
  shallow-merges composed lifespans, so a context key can be overwritten by
  another lifespan — whose client would then be handed the Mattermost token.
- Upgraded FastMCP to 3.4.4 — fixes CVE-2026-27124 (GHSA-rww4-4w9c-7733, missing consent check in the
  OAuth proxy callback), plus CVE-2026-32871 (authenticated SSRF) and CVE-2025-64340 (command injection)
  present in the previous 3.0.2. Floor raised to `fastmcp>=3.4.4,<4`; 3.4.3 is the first release with the
  Host/Origin protection this transport relies on.
- Remediated 20 known advisories (8 HIGH, 9 MEDIUM, 3 LOW) in transitive and dev/docs dependencies:
  `cryptography`, `pyjwt`, `mcp`, `urllib3`, `pydantic-settings`, `requests`, `idna`, `pytest`,
  `pygments`, `pymdown-extensions`.
- Added a blocking SCA gate: Trivy scans `uv.lock` and every published image architecture, failing on
  *fixable* HIGH/CRITICAL. Fixable LOW/MEDIUM are reported but do not block, as are vulnerabilities with
  no fix available. Exceptions only via `.trivyignore` with a documented reason and review date.
- `static_token` over HTTP now warns at startup instead of refusing to start — louder on a non-loopback
  bind, where the unauthenticated endpoint acting with the shared token is reachable by network peers.
  Container upgrades are no longer broken by this check.
- Added opt-in DNS-rebinding protection via `MATTERMOST_HTTP_HOST_ORIGIN_PROTECTION`
  (`off` / `auto` / `strict`), with `MATTERMOST_HTTP_ALLOWED_HOSTS` / `MATTERMOST_HTTP_ALLOWED_ORIGINS`
  allowlists. **Off unless set**, so upgrading rejects nothing that worked before, and FastMCP's own
  `FASTMCP_HTTP_HOST_ORIGIN_PROTECTION` still applies. Configured through FastMCP's settings rather than
  `mcp.run()` kwargs, so it also covers `fastmcp run`, a standalone ASGI server, and the app mounted into
  a parent application — previously none of those were protected. Rejections are logged with the
  offending `Host`/`Origin` and the variable that would accept it. See
  [HTTP transport security](docs/configuration.md#http-transport-security).

### Deprecated
- Host/Origin protection defaults to off; **in 1.0.0 the default becomes `auto`** (#30). Set
  `MATTERMOST_HTTP_HOST_ORIGIN_PROTECTION` explicitly now — `=off` included — and that upgrade changes
  nothing for you.

## [0.5.1] - 2026-07-07

### Added
- `MATTERMOST_EXTRA_CA_CERTS` — path to a PEM file with additional CA
  certificates (corporate/private CAs). Unlike `SSL_CERT_FILE` /
  `REQUESTS_CA_BUNDLE`, which *replace* the trust store, the extra CAs are
  appended to the default bundle, so publicly-signed hosts keep working. The
  combined bundle applies to all outgoing HTTPS requests, including the OAuth
  proxy's token exchange with the identity provider.

## [0.5.0] - 2026-05-26

### Added
- `get_channel_messages` now supports two new mutually-exclusive modes:
  - `unread_only=True` — fetches the user's unread window via Mattermost's
    `/users/me/channels/{id}/posts/unread` endpoint, with `limit_before` /
    `limit_after` bounds and a `collapsed_threads` flag for CRT-on users.
  - `since=<unix_ms>` — fetches posts modified after a timestamp via `?since=`,
    suitable for incremental sync.
- `PostList` now exposes `truncated: bool` — `True` when the response hit Mattermost's
  response cap (`1000` for `?since=`, `limit_before + limit_after` for `/posts/unread`,
  `per_page` for default pagination).
- `docs/examples.md` — restored "Morning Catch-Up" example, now end-to-end with the new
  unread-window flow, and added a "Bot Monitor Loop" recipe with two patterns
  (simple `unread_only` + `mark_channel_viewed`, and at-least-once `since` + watermark).
- `list_my_channels` accepts an `only_unread` filter to return only channels
  with unread messages.
- `mark_channel_viewed(channel_id)` — new tool that marks a channel as viewed
  for the authenticated user. Resets the channel-member unread counters and
  advances `last_viewed_at`. Documented usage: explicit user intent or a
  bot-monitoring loop that owns the read state.
- New `MATTERMOST_AUTH_MODE` setting selects one of three authentication strategies per server process: `static_token` (default), `client_token`, or `oauth_proxy`.
- `oauth_proxy` mode using FastMCP `OAuthProxy` with Mattermost OAuth 2.0 Applications. Supports both confidential and public client modes; PKCE forwarded upstream in both cases.
- New OAuth-related settings: `MATTERMOST_OAUTH_CLIENT_ID`, `MATTERMOST_OAUTH_CLIENT_SECRET`, `MATTERMOST_OAUTH_CLIENT_TYPE`, `MATTERMOST_OAUTH_MCP_PUBLIC_URL`, `MATTERMOST_OAUTH_MATTERMOST_PUBLIC_URL`, `MATTERMOST_OAUTH_CALLBACK_PATH`, `MATTERMOST_OAUTH_JWT_SIGNING_KEY`, `MATTERMOST_OAUTH_REQUIRE_CONSENT`, `MATTERMOST_OAUTH_ALLOWED_REDIRECT_URIS`, `MATTERMOST_OAUTH_FALLBACK_ACCESS_TOKEN_EXPIRY_SECONDS`.
- New `docs/authentication.md` page covering all three auth modes, Mattermost OAuth App registration, MCP client connection, troubleshooting, and the full env-var reference.

### Changed
- `list_my_channels` now returns four unread counters for each channel:
  `unread_msg_count` / `mention_count` use non-root semantics — replies in
  threads are counted, matching the channel badge when Collapsed Reply Threads
  is off; `unread_msg_count_root` / `mention_count_root` count only root posts,
  matching the badge when Collapsed Reply Threads is on.
- `get_channel_messages`: tightened `limit_after` validation to `1-200`
  (Mattermost rejects `limit_after=0` with HTTP 400; the previous `ge=0` bound
  surfaced an unclear server error).
- Rewrote `get_channel_messages` and `mark_channel_viewed` docstrings to be
  self-contained and compact: intent → mode mapping up front, footgun-only
  notes (`last_viewed_at == 0` bootstrap quirk, `since`-mode tombstones,
  `truncated` semantics), implementation detail moved to Field descriptions
  to keep agent context budget small.
- The Docker image now installs the package at build time. Container startup invokes the venv binary directly instead of going through `uv run`, eliminating a redundant `uv sync` on every start.
- **Behavioral change:** in `client_token` mode (and the new `oauth_proxy` mode), requests without a validated bearer token now fail with `AuthenticationError` instead of silently falling back to `MATTERMOST_TOKEN`. If you previously relied on the bot-token fallback for unauthenticated requests, switch to `MATTERMOST_AUTH_MODE=static_token` and remove `MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS`.
- **Behavioral change:** setting both `MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS=true` and `MATTERMOST_AUTH_MODE` to a non-`client_token` value now raises a configuration error at startup. Previously the legacy flag was silently ignored when both were set with conflicting values.
- **Behavioral change:** `mcp_server_mattermost.server` module import now performs full configuration validation eagerly. Tools or test fixtures that imported the module before configuring environment variables may need to be updated.

### Deprecated
- `MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS=true` is now an alias for `MATTERMOST_AUTH_MODE=client_token`. Prefer setting `MATTERMOST_AUTH_MODE` explicitly.

## [0.4.0] - 2026-03-24

### Breaking Changes
- Renamed `list_channels` tool to `list_public_channels` — same behavior, clearer name

### Added
- New `list_my_channels` tool: returns channels the authenticated user belongs to
  (public, private, DM, group) with optional `channel_types` filter
- Per-client token authentication: `MATTERMOST_ALLOW_HTTP_CLIENT_TOKENS` env var enables
  HTTP clients to pass their own Mattermost token via `Authorization: Bearer <token>`.
  The token is validated against the Mattermost API (`GET /api/v4/users/me`) on each
  connection. When disabled (default), the server uses `MATTERMOST_TOKEN` from environment.
- `MattermostTokenVerifier` class (`auth.py`): custom FastMCP 3 `TokenVerifier` that
  validates Mattermost bearer tokens and injects them into the request context.

### Fixed
- Suppress `KeyboardInterrupt` traceback on server shutdown
- Added `wsproto` to dependencies (required for WebSocket transport)

## [0.3.0] - 2026-02-25

### Changed

- **BREAKING:** Migrated from FastMCP 2 to FastMCP 3
  - Tool registration: `@mcp.tool()` → `@tool()` from `fastmcp.tools`
  - Auto-discovery via `FileSystemProvider` replaces manual tool imports
  - Lifespan uses `@lifespan` decorator from `fastmcp.server.lifespan`
  - DI providers moved from `server.py` to new `deps.py` module
  - Removed `# type: ignore[arg-type]` — FastMCP 3 has proper DI typing

## [0.2.0] - 2026-02-09

### Added

- Tool capability metadata (`read`, `write`, `create`, `delete`) for agent-based tool filtering

### Fixed

- Lifespan context manager now uses try/finally for reliable resource cleanup
- Added retry logic to `upload_file` method
- Parse HTTP-date format in Retry-After header (previously caused ValueError)

### Changed

- Refactored MattermostClient: DRY HTTP logging, improved error diagnostics, unified retry logic
- Migrated documentation hosting to Read the Docs
- Added best practices guide, usage examples with screenshots, and scenario prompts
- New project icon replacing ASCII-art logo

### Tests

- Added unit tests for bookmarks tools

## [0.1.3] - 2026-02-05

### Fixed

- Logo now displays correctly on PyPI (use absolute URL)

## [0.1.2] - 2026-02-05

### Changed

- Migrated repository to cloud-ru-tech organization
- Updated all documentation URLs to new GitHub org

## [0.1.1] - 2026-02-03

### Changed

- Reorganized README for better discoverability
- Added Quick Start page with tabbed installation instructions
- Clarified healthcheck behavior for stdio mode in documentation

### Removed

- Removed unused requirements.txt file

## [0.1.0] - 2026-02-02

### Added

- Initial release
- MCP server for Mattermost with 36 tools across 7 categories
- Channel management (list, create, join, leave, members)
- Message operations (post, search, edit, delete)
- Rich message attachments (Slack-style) with colors, fields, and images
- Reactions and pins
- Thread support
- User and team information
- File upload and download links
- Channel bookmarks
- Async HTTP client with retry and rate limit handling
- Docker support (stdio and HTTP modes)
