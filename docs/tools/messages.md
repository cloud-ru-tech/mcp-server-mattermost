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

Get recent messages from a channel.

Returns messages in reverse chronological order (newest first).
Use for reading channel conversation history.
For searching messages by keywords across channels, use search_messages instead.

### Example prompts

- "Show me the last 10 messages in #general"
- "What's the recent conversation in engineering?"
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
| `channel_id` | string | ✓ | — | Channel ID |
| `page` | integer | — | 0 | Page number (0-indexed) |
| `per_page` | integer | — | 60 | Results per page (1-200) |

### Returns

Object with `posts` (map of post objects) and `order` (array of post IDs).

### Mattermost API

[GET /api/v4/channels/{channel_id}/posts](https://api.mattermost.com/#tag/posts/operation/GetPostsForChannel)

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
