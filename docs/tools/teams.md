# Team Tools

Tools for accessing team information in Mattermost.

---

## list_teams

List teams the current user belongs to.

Returns team name, description, and settings.
Use this to discover available teams before listing channels.

### Example prompts

- "What teams am I in?"
- "List my teams"
- "Show available teams"

### Annotations

| Hint | Value |
|------|-------|
| `readOnlyHint` | true |
| `idempotentHint` | true |
| `capability` | read |

### Parameters

None

### Returns

Array of team objects with `id`, `name`, `display_name`, `description`, `type`.

### Mattermost API

[GET /api/v4/users/me/teams](https://api.mattermost.com/#tag/teams/operation/GetTeamsForUser)

---

## get_team

Get team details by ID.

Returns team name, description, and settings.
Use when you have the team ID and need detailed information.

### Example prompts

- "Get details for team abc123"
- "Show me information about this team"

### Annotations

| Hint | Value |
|------|-------|
| `readOnlyHint` | true |
| `idempotentHint` | true |
| `capability` | read |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `team_id` | string | ✓ | — | Team ID (26-character alphanumeric) |

### Returns

Team object with `id`, `name`, `display_name`, `description`, `type`, `company_name`, `allowed_domains`.

### Mattermost API

[GET /api/v4/teams/{team_id}](https://api.mattermost.com/#tag/teams/operation/GetTeam)

---

## get_team_members

Get members of a team.

Returns list of users who belong to the team.
Use to discover users before sending direct messages or mentions.

### Example prompts

- "Who is in this team?"
- "List team members"
- "Show me everyone on the engineering team"

### Annotations

| Hint | Value |
|------|-------|
| `readOnlyHint` | true |
| `idempotentHint` | true |
| `capability` | read |

### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `team_id` | string | ✓ | — | Team ID |
| `page` | integer | — | 0 | Page number (0-indexed) |
| `per_page` | integer | — | 60 | Results per page (1-200) |

### Returns

Array of team member objects with `team_id`, `user_id`, `roles`.

### Mattermost API

[GET /api/v4/teams/{team_id}/members](https://api.mattermost.com/#tag/teams/operation/GetTeamMembers)
