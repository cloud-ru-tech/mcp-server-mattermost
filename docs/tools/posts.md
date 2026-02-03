# Post Tools

Tools for reactions, pins, and thread operations on Mattermost posts.

---

## add_reaction

Add an emoji reaction to a message.

Adds a reaction from the authenticated user.
Common emojis: thumbsup, thumbsdown, smile, heart, eyes.
Adding the same reaction twice has no additional effect.

### Example prompts

- "Add a thumbs up to that message"
- "React with 👍 to the announcement"
- "Add a heart reaction"

### Annotations

| Hint | Value |
|------|-------|
| `destructiveHint` | false |
| `idempotentHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `post_id` | string | ✓ | — | Post ID to react to |
| `emoji_name` | string | ✓ | — | Emoji name without colons (e.g., "thumbsup") |

### Returns

Reaction object with `user_id`, `post_id`, `emoji_name`, `create_at`.

### Mattermost API

[POST /api/v4/reactions](https://api.mattermost.com/#tag/reactions/operation/SaveReaction)

---

## remove_reaction

Remove your emoji reaction from a message.

Removes a reaction previously added by the authenticated user.
Removing a non-existent reaction has no effect.

### Example prompts

- "Remove my reaction from that message"
- "Take back my thumbs up"

### Annotations

| Hint | Value |
|------|-------|
| `destructiveHint` | false |
| `idempotentHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `post_id` | string | ✓ | — | Post ID |
| `emoji_name` | string | ✓ | — | Emoji name to remove |

### Returns

None

### Mattermost API

[DELETE /api/v4/users/{user_id}/posts/{post_id}/reactions/{emoji_name}](https://api.mattermost.com/#tag/reactions/operation/DeleteReaction)

---

## get_reactions

Get all reactions on a message.

Returns list of reactions with emoji names and user IDs.
Use to see who reacted to a message and with what emoji.

### Example prompts

- "Who reacted to that message?"
- "Show me the reactions on the announcement"
- "What emojis did people use?"

### Annotations

| Hint | Value |
|------|-------|
| `readOnlyHint` | true |
| `idempotentHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `post_id` | string | ✓ | — | Post ID |

### Returns

Array of reaction objects with `user_id`, `post_id`, `emoji_name`, `create_at`.

### Mattermost API

[GET /api/v4/posts/{post_id}/reactions](https://api.mattermost.com/#tag/reactions/operation/GetReactions)

---

## pin_message

Pin a message in a channel.

Pinned messages appear in the channel's pinned posts section.
Pinning an already pinned message has no additional effect.

### Example prompts

- "Pin that important announcement"
- "Pin this message for the team"

### Annotations

| Hint | Value |
|------|-------|
| `destructiveHint` | false |
| `idempotentHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `post_id` | string | ✓ | — | Post ID to pin |

### Returns

Pinned post object.

### Mattermost API

[POST /api/v4/posts/{post_id}/pin](https://api.mattermost.com/#tag/posts/operation/PinPost)

---

## unpin_message

Unpin a message from a channel.

Removes the message from the channel's pinned posts.
Unpinning a non-pinned message has no effect.

### Example prompts

- "Unpin that old announcement"
- "Remove the pin from that message"

### Annotations

| Hint | Value |
|------|-------|
| `destructiveHint` | false |
| `idempotentHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `post_id` | string | ✓ | — | Post ID to unpin |

### Returns

Unpinned post object.

### Mattermost API

[POST /api/v4/posts/{post_id}/unpin](https://api.mattermost.com/#tag/posts/operation/UnpinPost)

---

## get_thread

Get all messages in a thread.

Returns the root post and all replies in chronological order.
Use to read full conversation context before replying.

### Example prompts

- "Show me the full thread"
- "What are all the replies to that message?"
- "Get the thread context"

### Annotations

| Hint | Value |
|------|-------|
| `readOnlyHint` | true |
| `idempotentHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `post_id` | string | ✓ | — | Root post ID of the thread |

### Returns

Object with `posts` (map of post objects) and `order` (array of post IDs in order).

### Mattermost API

[GET /api/v4/posts/{post_id}/thread](https://api.mattermost.com/#tag/posts/operation/GetPostThread)
