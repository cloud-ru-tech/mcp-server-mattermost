# Tools Overview

MCP Server Mattermost provides 36 tools organized into 7 categories.

## Categories

| Category | Tools | Description |
|----------|-------|-------------|
| [Channels](channels.md) | 9 | List, create, join, manage channels and DMs |
| [Messages](messages.md) | 5 | Send, search, edit, delete messages |
| [Reactions & Threads](posts.md) | 6 | Emoji reactions, pins, thread history |
| [Users](users.md) | 5 | Lookup, search, status |
| [Teams](teams.md) | 3 | List teams, members |
| [Files](files.md) | 3 | Upload, metadata, download links |
| [Bookmarks](bookmarks.md) | 5 | Channel bookmarks (Entry+ edition) |

## Quick Reference

The **Capability** column shows each tool's access level (`read`, `write`, `create`, `delete`).
This is metadata for client-side filtering — it does not affect runtime behavior.
See [Building Agents](../building-agents.md) for how to use capabilities
to filter tools by agent profile.

### Channels

| Tool | Capability | Description |
|------|------------|-------------|
| `list_channels` | read | List channels in a team |
| `get_channel` | read | Get channel details by ID |
| `get_channel_by_name` | read | Get channel by name |
| `create_channel` | create | Create a new channel |
| `join_channel` | write | Join a public channel |
| `leave_channel` | write | Leave a channel |
| `get_channel_members` | read | List channel members |
| `add_user_to_channel` | write | Add user to channel |
| `create_direct_channel` | create | Create DM channel |

### Messages

| Tool | Capability | Description |
|------|------------|-------------|
| `post_message` | write | Send a message to a channel |
| `get_channel_messages` | read | Get recent messages |
| `search_messages` | read | Search messages by term |
| `update_message` | write | Edit a message |
| `delete_message` | delete | Delete a message |

### Reactions & Threads

| Tool | Capability | Description |
|------|------------|-------------|
| `add_reaction` | write | Add emoji reaction |
| `remove_reaction` | write | Remove emoji reaction |
| `get_reactions` | read | Get all reactions on a post |
| `pin_message` | write | Pin a message |
| `unpin_message` | write | Unpin a message |
| `get_thread` | read | Get thread messages |

### Users

| Tool | Capability | Description |
|------|------------|-------------|
| `get_me` | read | Get current user info |
| `get_user` | read | Get user by ID |
| `get_user_by_username` | read | Get user by username |
| `search_users` | read | Search users |
| `get_user_status` | read | Get online status |

### Teams

| Tool | Capability | Description |
|------|------------|-------------|
| `list_teams` | read | List your teams |
| `get_team` | read | Get team details |
| `get_team_members` | read | List team members |

### Files

| Tool | Capability | Description |
|------|------------|-------------|
| `upload_file` | write | Upload a file |
| `get_file_info` | read | Get file metadata |
| `get_file_link` | read | Get download link |

### Bookmarks

| Tool | Capability | Description |
|------|------------|-------------|
| `list_bookmarks` | read | List channel bookmarks |
| `create_bookmark` | write | Create bookmark |
| `update_bookmark` | write | Update bookmark |
| `delete_bookmark` | delete | Delete bookmark |
| `update_bookmark_sort_order` | write | Reorder bookmark |

!!! note "Bookmarks require Entry+ edition"
    Bookmark tools require Mattermost Entry, Professional, or Enterprise edition (v10.1+).
