# Examples

Practical examples of using MCP Server Mattermost with AI assistants.

## Sending Alerts

### Build Status Alert

> "Send a build failed alert to #engineering with red color"

The AI will use `post_message` with attachments:

```json
{
  "channel_id": "engineering-channel-id",
  "message": "",
  "attachments": [{
    "color": "danger",
    "title": "Build Failed",
    "text": "Pipeline failed on main branch",
    "fields": [
      {"title": "Branch", "value": "main", "short": true},
      {"title": "Commit", "value": "abc1234", "short": true}
    ]
  }]
}
```

### Deployment Notification

> "Notify #releases that v2.1.0 is deployed to production"

```json
{
  "channel_id": "releases-channel-id",
  "message": "",
  "attachments": [{
    "color": "good",
    "title": "Deployment Complete",
    "text": "Version 2.1.0 deployed to production",
    "footer": "Deployed via CI/CD"
  }]
}
```

## Monitoring Channels

### Daily Summary

> "Summarize what happened in #general today"

The AI will:

1. Use `get_channel_by_name` to find the channel
2. Use `get_channel_messages` to fetch recent messages
3. Analyze and summarize the conversation

### Find Discussions

> "Search for messages about the database migration"

The AI will use `search_messages`:

```json
{
  "team_id": "your-team-id",
  "terms": "database migration"
}
```

## Team Management

### Check Who's Online

> "Who's online in my team right now?"

The AI will:

1. Use `get_team_members` to list team members
2. Use `get_user_status` for each member
3. Report online/offline status

### Find a Person

> "Find John's Mattermost account"

The AI will use `search_users`:

```json
{
  "term": "john"
}
```

## Thread Conversations

### Reply in Thread

> "Reply to that message saying the fix is deployed"

The AI will use `post_message` with `root_id`:

```json
{
  "channel_id": "channel-id",
  "message": "The fix has been deployed to production.",
  "root_id": "original-post-id"
}
```

### Get Thread History

> "Show me the full thread"

The AI will use `get_thread` with the root post ID.

## File Sharing

### Upload and Share

> "Upload report.pdf to #general"

The AI will:

1. Use `upload_file` to upload the file
2. Use `post_message` with `file_ids` to share it

### Get Download Link

> "Get the download link for that file"

The AI will use `get_file_link` with the file ID.

## Channel Management

### Create Project Channel

> "Create a private channel called project-phoenix for the new project"

The AI will use `create_channel`:

```json
{
  "team_id": "team-id",
  "name": "project-phoenix",
  "display_name": "Project Phoenix",
  "channel_type": "P",
  "purpose": "Discussion channel for Project Phoenix"
}
```

### Direct Message

> "Send a DM to @alice asking about the meeting"

The AI will:

1. Use `get_user_by_username` to find Alice's user ID
2. Use `get_me` to get the bot's user ID
3. Use `create_direct_channel` to create/get the DM channel
4. Use `post_message` to send the message

## Reactions

### React to Message

> "Add a thumbs up to that message"

The AI will use `add_reaction`:

```json
{
  "post_id": "message-id",
  "emoji_name": "+1"
}
```

### Pin Important Message

> "Pin that announcement"

The AI will use `pin_message` with the post ID.
