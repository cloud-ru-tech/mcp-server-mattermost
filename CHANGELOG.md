# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
