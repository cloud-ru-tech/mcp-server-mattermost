# User Tools

Tools for looking up users and checking their status in Mattermost.

---

## get_me

Get the current authenticated user's profile.

Returns user information including username, email, and status.
Use to get your own user ID for operations like create_direct_channel.

### Example prompts

- "Who am I logged in as?"
- "What's my user ID?"
- "Show my profile"

### Annotations

| Hint | Value |
|------|-------|
| `readOnlyHint` | true |
| `idempotentHint` | true |

### Parameters

None

### Returns

User object with `id`, `username`, `email`, `first_name`, `last_name`, `nickname`, `roles`.

### Mattermost API

[GET /api/v4/users/me](https://api.mattermost.com/#tag/users/operation/GetUser)

---

## get_user

Get a user's profile by their ID.

Returns user information including username, email, and status.
Use when you have the user ID.
For lookup by @username, use get_user_by_username instead.

### Example prompts

- "Get info for user abc123"
- "Look up this user's profile"

### Annotations

| Hint | Value |
|------|-------|
| `readOnlyHint` | true |
| `idempotentHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `user_id` | string | ✓ | — | User ID (26-character alphanumeric) |

### Returns

User object with `id`, `username`, `email`, `first_name`, `last_name`, `nickname`, `roles`.

### Mattermost API

[GET /api/v4/users/{user_id}](https://api.mattermost.com/#tag/users/operation/GetUser)

---

## get_user_by_username

Get a user's profile by their username.

Returns user information including username, email, and status.
Use when you know the @username but not the user ID.
For lookup by ID, use get_user instead.

### Example prompts

- "Find @john"
- "Get the profile for username alice"
- "Look up @manager"

### Annotations

| Hint | Value |
|------|-------|
| `readOnlyHint` | true |
| `idempotentHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `username` | string | ✓ | — | Username without @ (1-64 chars, lowercase) |

### Returns

User object with `id`, `username`, `email`, `first_name`, `last_name`, `nickname`, `roles`.

### Mattermost API

[GET /api/v4/users/username/{username}](https://api.mattermost.com/#tag/users/operation/GetUserByUsername)

---

## search_users

Search for users by name or username.

Searches across username, first name, last name, and nickname.
Use to find users when you don't know their exact username or ID.

### Example prompts

- "Search for John"
- "Find users named Smith"
- "Who has 'dev' in their name?"

### Annotations

| Hint | Value |
|------|-------|
| `readOnlyHint` | true |
| `idempotentHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `term` | string | ✓ | — | Search term (1-256 chars) |
| `team_id` | string | — | — | Limit search to a specific team |

### Returns

Array of matching user objects.

### Mattermost API

[POST /api/v4/users/search](https://api.mattermost.com/#tag/users/operation/SearchUsers)

---

## get_user_status

Get a user's online/offline status.

Returns: online, away, dnd (do not disturb), or offline.
Use to check if a user is available before sending a message.

### Example prompts

- "Is @john online?"
- "Check if the manager is available"
- "What's Alice's status?"

### Annotations

| Hint | Value |
|------|-------|
| `readOnlyHint` | true |
| `idempotentHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `user_id` | string | ✓ | — | User ID |

### Returns

Status object with `user_id`, `status` (online/away/dnd/offline), `last_activity_at`.

### Mattermost API

[GET /api/v4/users/{user_id}/status](https://api.mattermost.com/#tag/status/operation/GetUserStatus)
