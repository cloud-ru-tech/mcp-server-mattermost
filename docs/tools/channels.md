# Channel Tools

Tools for managing Mattermost channels: listing, creating, joining, and member management.

---

## list_channels

List public and private channels in a team.

Returns channels that the authenticated user has access to.
Use this to discover available channels for posting messages.

### Example prompts

- "Show me all channels in my team"
- "What channels are available?"
- "List channels"

### Annotations

| Hint | Value |
|------|-------|
| `readOnlyHint` | true |
| `idempotentHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `team_id` | string | ✓ | — | Team ID (26-character alphanumeric) |
| `page` | integer | — | 0 | Page number (0-indexed) |
| `per_page` | integer | — | 60 | Results per page (1-200) |

### Returns

Array of channel objects with `id`, `name`, `display_name`, `type`, `purpose`.

### Mattermost API

[GET /api/v4/teams/{team_id}/channels](https://api.mattermost.com/#tag/channels/operation/GetPublicChannelsForTeam)

---

## get_channel

Get detailed information about a specific channel.

Returns channel metadata including name, purpose, header, and member count.
Use when you have the channel ID.
For lookup by channel name, use get_channel_by_name instead.

### Example prompts

- "Get details for channel abc123"
- "Show me information about this channel"

### Annotations

| Hint | Value |
|------|-------|
| `readOnlyHint` | true |
| `idempotentHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `channel_id` | string | ✓ | — | Channel ID (26-character alphanumeric) |

### Returns

Channel object with `id`, `name`, `display_name`, `type`, `purpose`, `header`, `total_msg_count`.

### Mattermost API

[GET /api/v4/channels/{channel_id}](https://api.mattermost.com/#tag/channels/operation/GetChannel)

---

## get_channel_by_name

Get a channel by its name within a team.

Returns channel metadata including name, purpose, header, and member count.
Use when you know the channel name but not the ID.
For lookup by ID, use get_channel instead.

### Example prompts

- "Find the #general channel"
- "Get the engineering channel"

### Annotations

| Hint | Value |
|------|-------|
| `readOnlyHint` | true |
| `idempotentHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `team_id` | string | ✓ | — | Team ID |
| `channel_name` | string | ✓ | — | Channel name (lowercase, no spaces, 1-64 chars) |

### Returns

Channel object with `id`, `name`, `display_name`, `type`, `purpose`, `header`.

### Mattermost API

[GET /api/v4/teams/{team_id}/channels/name/{channel_name}](https://api.mattermost.com/#tag/channels/operation/GetChannelByName)

---

## create_channel

Create a new channel in a team.

Creates either a public (O) or private (P) channel.
The authenticated user becomes the channel admin.
Each call creates a new channel; use get_channel_by_name to check if it exists.

### Example prompts

- "Create a new channel called project-x"
- "Make a private channel for the security team"

### Annotations

| Hint | Value |
|------|-------|
| `destructiveHint` | false |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `team_id` | string | ✓ | — | Team ID |
| `name` | string | ✓ | — | URL-friendly name (lowercase, no spaces, 1-64 chars) |
| `display_name` | string | ✓ | — | Human-readable name (1-64 chars) |
| `channel_type` | string | — | "O" | "O" (public) or "P" (private) |
| `purpose` | string | — | "" | Channel purpose (max 250 chars) |
| `header` | string | — | "" | Channel header (max 1024 chars) |

### Returns

Created channel object with `id`, `name`, `display_name`, `type`, `create_at`.

### Mattermost API

[POST /api/v4/channels](https://api.mattermost.com/#tag/channels/operation/CreateChannel)

---

## join_channel

Join a public channel.

Adds the authenticated user to the channel.
Cannot be used to join private channels.
Joining a channel you're already in has no additional effect.

### Example prompts

- "Join the #announcements channel"
- "Add me to the general channel"

### Annotations

| Hint | Value |
|------|-------|
| `destructiveHint` | false |
| `idempotentHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `channel_id` | string | ✓ | — | Channel ID |

### Returns

Channel member object with `channel_id`, `user_id`, `roles`.

### Mattermost API

[POST /api/v4/channels/{channel_id}/members](https://api.mattermost.com/#tag/channels/operation/AddChannelMember)

---

## leave_channel

Leave a channel.

Removes the authenticated user from the channel.
Cannot leave Town Square or other default channels.
Can rejoin public channels later with join_channel.

### Example prompts

- "Leave the #random channel"
- "Remove me from the old-project channel"

### Annotations

| Hint | Value |
|------|-------|
| `destructiveHint` | false |
| `idempotentHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `channel_id` | string | ✓ | — | Channel ID |

### Returns

None

### Mattermost API

[DELETE /api/v4/channels/{channel_id}/members/{user_id}](https://api.mattermost.com/#tag/channels/operation/RemoveUserFromChannel)

---

## get_channel_members

Get members of a channel.

Returns list of users who are members of the channel.
Use to see who can receive messages in a channel.

### Example prompts

- "Who is in the #engineering channel?"
- "List members of this channel"

### Annotations

| Hint | Value |
|------|-------|
| `readOnlyHint` | true |
| `idempotentHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `channel_id` | string | ✓ | — | Channel ID |
| `page` | integer | — | 0 | Page number (0-indexed) |
| `per_page` | integer | — | 60 | Results per page (1-200) |

### Returns

Array of channel member objects with `user_id`, `channel_id`, `roles`.

### Mattermost API

[GET /api/v4/channels/{channel_id}/members](https://api.mattermost.com/#tag/channels/operation/GetChannelMembers)

---

## add_user_to_channel

Add a user to a channel.

Requires permission to manage channel members.
Adding a user who is already in the channel has no additional effect.

### Example prompts

- "Add @john to the #project channel"
- "Invite the new team member to engineering"

### Annotations

| Hint | Value |
|------|-------|
| `destructiveHint` | false |
| `idempotentHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `channel_id` | string | ✓ | — | Channel ID |
| `user_id` | string | ✓ | — | User ID to add |

### Returns

Channel member object with `channel_id`, `user_id`, `roles`.

### Mattermost API

[POST /api/v4/channels/{channel_id}/members](https://api.mattermost.com/#tag/channels/operation/AddChannelMember)

---

## create_direct_channel

Create a direct message channel between two users.

Returns an existing DM channel if one already exists between the users.
Use this to get a channel ID for sending private messages.
Then use post_message with the returned channel_id to send messages.

### Example prompts

- "Start a DM with @alice"
- "Create a direct message channel with the manager"

### Annotations

| Hint | Value |
|------|-------|
| `destructiveHint` | false |
| `idempotentHint` | true |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `user_id_1` | string | ✓ | — | First user ID |
| `user_id_2` | string | ✓ | — | Second user ID |

### Returns

Direct channel object with `id`, `type` ("D"), `name`.

### Mattermost API

[POST /api/v4/channels/direct](https://api.mattermost.com/#tag/channels/operation/CreateDirectChannel)
