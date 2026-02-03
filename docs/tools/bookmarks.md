# Bookmark Tools

Tools for managing channel bookmarks: links and files pinned to channels for quick access.

> **Edition Requirements:** Channel Bookmarks require Entry, Professional, Enterprise, or Enterprise Advanced edition. Not available in Team Edition.
>
> **Minimum Version:** Mattermost v10.1+
>
> **Documentation:** [Manage channel bookmarks](https://docs.mattermost.com/collaborate/manage-channel-bookmarks.html) | [Editions and Offerings](https://docs.mattermost.com/product-overview/editions-and-offerings.html)

---

## list_bookmarks

List all bookmarks in a channel.

Returns bookmarks in sort order.
Use to see saved links and files pinned to a channel.
For searching messages, use search_messages instead.

### Example prompts

- "Show me the bookmarks in this channel"
- "What links are saved in #engineering?"
- "List channel bookmarks"

### Annotations

| Hint | Value |
|------|-------|
| `readOnlyHint` | true |
| `idempotentHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `channel_id` | string | ✓ | — | Channel ID (26-character alphanumeric) |
| `bookmarks_since` | integer | — | — | Timestamp to filter bookmarks updated since |

### Returns

Array of bookmark objects with `id`, `display_name`, `type`, `link_url`, `file_id`, `emoji`, `sort_order`.

### Mattermost API

[GET /api/v4/channels/{channel_id}/bookmarks](https://api.mattermost.com/#tag/bookmarks/operation/ListChannelBookmarks)

---

## create_bookmark

Create a channel bookmark.

Creates a link bookmark (URL) or file bookmark (attached file).
For link type, link_url is required.
For file type, file_id is required (from upload_file).

### Example prompts

- "Add a bookmark to the docs"
- "Save this link to the channel"
- "Bookmark the uploaded file"

### Annotations

| Hint | Value |
|------|-------|
| `destructiveHint` | false |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `channel_id` | string | ✓ | — | Channel ID |
| `display_name` | string | ✓ | — | Bookmark display name (1-255 chars) |
| `bookmark_type` | string | ✓ | — | Type: "link" or "file" |
| `link_url` | string | — | — | URL (required for link type) |
| `file_id` | string | — | — | File ID (required for file type) |
| `emoji` | string | — | — | Emoji icon |
| `image_url` | string | — | — | Preview image URL |

### Returns

Created bookmark object with `id`, `display_name`, `type`, `link_url`, `create_at`.

### Mattermost API

[POST /api/v4/channels/{channel_id}/bookmarks](https://api.mattermost.com/#tag/bookmarks/operation/CreateChannelBookmark)

---

## update_bookmark

Update a channel bookmark.

Partially updates bookmark properties.
Only provided fields are updated; others remain unchanged.

### Example prompts

- "Rename the bookmark to 'New Docs'"
- "Change the bookmark URL"
- "Update the bookmark emoji"

### Annotations

| Hint | Value |
|------|-------|
| `destructiveHint` | false |
| `idempotentHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `channel_id` | string | ✓ | — | Channel ID |
| `bookmark_id` | string | ✓ | — | Bookmark ID |
| `display_name` | string | — | — | New display name |
| `link_url` | string | — | — | New URL |
| `image_url` | string | — | — | New preview image URL |
| `emoji` | string | — | — | New emoji icon |

### Returns

Updated bookmark object.

### Mattermost API

[PATCH /api/v4/channels/{channel_id}/bookmarks/{bookmark_id}](https://api.mattermost.com/#tag/bookmarks/operation/UpdateChannelBookmark)

---

## delete_bookmark

Delete a channel bookmark.

Archives the bookmark (soft delete via delete_at timestamp).
The bookmark will no longer appear in the channel.

### Example prompts

- "Remove that bookmark"
- "Delete the old docs link"

### Annotations

| Hint | Value |
|------|-------|
| `destructiveHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `channel_id` | string | ✓ | — | Channel ID |
| `bookmark_id` | string | ✓ | — | Bookmark ID |

### Returns

Deleted bookmark object with `delete_at` timestamp set.

### Mattermost API

[DELETE /api/v4/channels/{channel_id}/bookmarks/{bookmark_id}](https://api.mattermost.com/#tag/bookmarks/operation/DeleteChannelBookmark)

---

## update_bookmark_sort_order

Reorder a channel bookmark.

Moves the bookmark to the specified position.
Other bookmarks are automatically adjusted.
Returns all affected bookmarks with updated positions.

### Example prompts

- "Move the docs bookmark to the top"
- "Reorder bookmarks"

### Annotations

| Hint | Value |
|------|-------|
| `destructiveHint` | false |
| `idempotentHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `channel_id` | string | ✓ | — | Channel ID |
| `bookmark_id` | string | ✓ | — | Bookmark ID |
| `new_sort_order` | integer | ✓ | — | New position (0-indexed) |

### Returns

Array of affected bookmark objects with updated `sort_order`.

### Mattermost API

[POST /api/v4/channels/{channel_id}/bookmarks/{bookmark_id}/sort_order](https://api.mattermost.com/#tag/bookmarks/operation/UpdateChannelBookmarkSortOrder)
