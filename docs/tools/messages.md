# Message Tools

Tools for sending, reading, searching, and managing messages in Mattermost.

---

## post_message

Post a message to a Mattermost channel.

Send text messages with Markdown support.
Use root_id to reply in a thread.
Use file_ids to attach uploaded files.
Use attachments for rich formatted content with colors, fields, and images.
To read all messages in a thread, use get_thread.

### Example prompts

- "Send 'Hello team!' to #general"
- "Post a status update in the engineering channel"
- "Reply to that message in the thread"
- "Send a message with a red alert attachment"

### Annotations

| Hint | Value |
|------|-------|
| `destructiveHint` | false |
| `capability` | write |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `channel_id` | string | ✓ | — | Channel ID to post to |
| `message` | string | ✓ | — | Message content, supports Markdown (1-16383 chars) |
| `root_id` | string | — | — | Root post ID for threading |
| `file_ids` | array | — | — | File IDs to attach (from upload_file) |
| `attachments` | array | — | — | Rich message attachments (see Attachments section) |

### Attachment Examples

```json
// Status alert
{"color": "danger", "title": "Build Failed", "text": "Tests failed on main"}

// Success notification
{"color": "good", "title": "Deployed", "text": "v1.2.3 is live"}

// With structured fields
{
  "title": "Ticket #123",
  "fields": [
    {"title": "Status", "value": "Open", "short": true},
    {"title": "Priority", "value": "High", "short": true}
  ]
}
```

### Returns

Post object with `id`, `channel_id`, `message`, `create_at`, `user_id`.

### Mattermost API

[POST /api/v4/posts](https://api.mattermost.com/#tag/posts/operation/CreatePost)

---

## get_channel_messages

Read messages from a channel — either the most recent batch, the user's unread window, or messages modified after a given timestamp.

Three mutually-exclusive modes:

- **Default** — paginated reverse-chronological history. The default behaviour
  for "show me the channel".
- **`unread_only=True`** — the user's unread window via `/posts/unread`. Returns
  up to `limit_after` unread posts plus `limit_before` context posts.
  Deterministic ordering; edits of older posts do not appear.
- **`since=<ms>`** — posts with `update_at > since`, ordered by `create_at`.
  Includes edits of older posts. Intended for incremental sync where the
  caller tracks its own watermark, not for direct human use.

For keyword search across channels, use `search_messages`.
To read a thread in full, use `get_thread`.

### Example prompts

- "Show me the last 10 messages in #general"
- "What's new in #engineering?"
- "Catch me up on #releases — what did I miss?"
- "Read the channel history"

### Annotations

| Hint | Value |
|------|-------|
| `readOnlyHint` | true |
| `idempotentHint` | true |
| `capability` | read |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `channel_id` | string | ✓ | — | Channel ID (26-character alphanumeric) |
| `unread_only` | boolean | — | false | Use the unread-window mode. Mutually exclusive with `since` and pagination. |
| `since` | integer | — | — | Unix timestamp in milliseconds (≥ 10¹²). Returns posts with `update_at > since`. Mutually exclusive with `unread_only` and pagination. |
| `page` | integer | — | 0 | Page number, 0-indexed. Default mode only. |
| `per_page` | integer | — | 60 | Page size, 1–200. Default mode only. |
| `limit_before` | integer | — | 0 | Context posts before the first unread, 0–200. `unread_only` mode only. |
| `limit_after` | integer | — | 60 | Unread posts to return, 1–200. `unread_only` mode only. |
| `collapsed_threads` | boolean | — | false | Set true if [CRT][crt-end-user] is enabled. Valid only with `unread_only` or `since`. Team default is CRT off. |

### Returns

Object with:

- `posts` — map of post objects keyed by post ID.
- `order` — array of post IDs in reverse-chronological order.
- `truncated` — boolean. True when the response hit the per-mode cap and more
  posts likely exist beyond this batch (default: `len(order) >= per_page`;
  `unread_only`: `>= limit_before + limit_after`; `since`: `>= 1000`, the
  server hard-cap).

### Behavior notes

- **Collapsed Reply Threads (CRT)** changes how unread counts and thread
  replies surface. With CRT off (team default), `unread_msg_count` from
  `list_my_channels` and this tool's response in any mode both count thread
  replies. With CRT on, pass `collapsed_threads=true` and fetch full threads
  via `get_thread` when needed. See the [end-user overview][crt-end-user] for
  what CRT does in the UI, and the [administrator guide][crt-admin] for how
  it is enabled on a server.
- `since` mode is the only one that surfaces edits of older posts. A post
  with `create_at <= since AND update_at > since` is an edit; filter by
  `create_at` if you only want new messages.
- `since` mode is capped at 1000 posts server-side. When the cap is hit
  (`truncated=true`), the returned posts are not guaranteed to be
  consecutive — there can be gaps between them and posts not in the
  response. Prefer `unread_only=true` for a deterministic windowed read.
- For watermark-based sync, read `ChannelWithUnreads.last_viewed_at` from
  `list_my_channels` and pass it as `since`.

[crt-end-user]: https://docs.mattermost.com/end-user-guide/collaborate/organize-conversations.html
[crt-admin]: https://support.mattermost.com/hc/en-us/articles/6880701948564-Administrator-s-guide-to-enabling-Collapsed-Reply-Threads

### Mattermost API

- [GET /api/v4/channels/{channel_id}/posts](https://api.mattermost.com/#tag/posts/operation/GetPostsForChannel) — default and `since` modes.
- [GET /api/v4/users/{user_id}/channels/{channel_id}/posts/unread](https://api.mattermost.com/#tag/posts/operation/GetPostsAroundLastUnread) — `unread_only` mode.

---

## search_messages

Search for messages matching specific criteria across channels.

Searches message content within a team.
Supports Mattermost search syntax (from:, in:, before:, after:).
For simply reading recent channel messages, use get_channel_messages instead.

### Example prompts

- "Search for messages about the deployment"
- "Find messages from @john about the bug"
- "Search for 'API error' in the last week"

### Annotations

| Hint | Value |
|------|-------|
| `readOnlyHint` | true |
| `idempotentHint` | true |
| `capability` | read |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `team_id` | string | ✓ | — | Team ID to search in |
| `terms` | string | ✓ | — | Search terms, supports Mattermost syntax (1-512 chars) |
| `is_or_search` | boolean | — | false | Use OR instead of AND for multiple terms |

### Returns

Object with `posts` (map of matching post objects) and `order` (array of post IDs).

### Mattermost API

[POST /api/v4/teams/{team_id}/posts/search](https://api.mattermost.com/#tag/posts/operation/SearchPosts)

---

## update_message

Edit an existing message.

Can only edit your own messages (unless admin).
The message will show as edited.
Original content is replaced; edit history is not preserved.
Use attachments to add or update rich formatted content.

### Example prompts

- "Edit my last message to say..."
- "Fix the typo in that message"
- "Update the announcement"
- "Add an attachment to that message"

### Annotations

| Hint | Value |
|------|-------|
| `destructiveHint` | false |
| `capability` | write |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `post_id` | string | ✓ | — | Post ID to edit |
| `message` | string | ✓ | — | New message content (1-16383 chars) |
| `attachments` | array | — | — | Rich message attachments (see post_message for examples) |

### Returns

Updated post object with `id`, `message`, `edit_at`.

### Mattermost API

[PUT /api/v4/posts/{post_id}](https://api.mattermost.com/#tag/posts/operation/UpdatePost)

---

## delete_message

Delete a message permanently.

Can only delete your own messages (unless admin).
Deleted messages cannot be recovered.
All reactions and thread context will be lost.

### Example prompts

- "Delete that message"
- "Remove my last post"

### Annotations

| Hint | Value |
|------|-------|
| `destructiveHint` | true |
| `capability` | delete |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `post_id` | string | ✓ | — | Post ID to delete |

### Returns

None

### Mattermost API

[DELETE /api/v4/posts/{post_id}](https://api.mattermost.com/#tag/posts/operation/DeletePost)

---

## Attachment Format

Rich message attachments allow formatted content with colors, fields, author info, and images. Based on Slack attachment format.

### Attachment Fields

| Field | Type | Description |
|-------|------|-------------|
| `fallback` | string | Plain-text summary for notifications |
| `color` | string | Left border: `good`, `warning`, `danger`, or `#RRGGBB` hex |
| `pretext` | string | Text above attachment |
| `text` | string | Main content (supports Markdown) |
| `author_name` | string | Author display name |
| `author_link` | string | Author profile URL (requires `author_name`) |
| `author_icon` | string | Author avatar URL |
| `title` | string | Attachment title |
| `title_link` | string | Title hyperlink URL (requires `title`) |
| `fields` | array | Structured data fields (see below) |
| `image_url` | string | Main image URL |
| `thumb_url` | string | Thumbnail image URL (75x75) |
| `footer` | string | Footer text (max 300 chars) |
| `footer_icon` | string | Footer icon URL |

### Field Object

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Field label/header |
| `value` | string/number | Field content |
| `short` | boolean | Display inline with other short fields (default: false) |

### Full Example

```json
{
  "color": "#FF5733",
  "pretext": "New deployment notification",
  "author_name": "CI/CD Bot",
  "author_icon": "https://example.com/bot-icon.png",
  "title": "Production Deployment",
  "title_link": "https://github.com/org/repo/releases/v1.2.3",
  "text": "Version 1.2.3 deployed successfully",
  "fields": [
    {"title": "Environment", "value": "Production", "short": true},
    {"title": "Duration", "value": "45s", "short": true},
    {"title": "Changes", "value": "5 commits", "short": true},
    {"title": "Author", "value": "@developer", "short": true}
  ],
  "footer": "Deployed via GitHub Actions",
  "ts": 1706886000
}
```
