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

### Channels

| Tool | Description |
|------|-------------|
| `list_channels` | List channels in a team |
| `get_channel` | Get channel details by ID |
| `get_channel_by_name` | Get channel by name |
| `create_channel` | Create a new channel |
| `join_channel` | Join a public channel |
| `leave_channel` | Leave a channel |
| `get_channel_members` | List channel members |
| `add_user_to_channel` | Add user to channel |
| `create_direct_channel` | Create DM channel |

### Messages

| Tool | Description |
|------|-------------|
| `post_message` | Send a message to a channel |
| `get_channel_messages` | Get recent messages |
| `search_messages` | Search messages by term |
| `update_message` | Edit a message |
| `delete_message` | Delete a message |

### Reactions & Threads

| Tool | Description |
|------|-------------|
| `add_reaction` | Add emoji reaction |
| `remove_reaction` | Remove emoji reaction |
| `get_reactions` | Get all reactions on a post |
| `pin_message` | Pin a message |
| `unpin_message` | Unpin a message |
| `get_thread` | Get thread messages |

### Users

| Tool | Description |
|------|-------------|
| `get_me` | Get current user info |
| `get_user` | Get user by ID |
| `get_user_by_username` | Get user by username |
| `search_users` | Search users |
| `get_user_status` | Get online status |

### Teams

| Tool | Description |
|------|-------------|
| `list_teams` | List your teams |
| `get_team` | Get team details |
| `get_team_members` | List team members |

### Files

| Tool | Description |
|------|-------------|
| `upload_file` | Upload a file |
| `get_file_info` | Get file metadata |
| `get_file_link` | Get download link |

### Bookmarks

| Tool | Description |
|------|-------------|
| `list_bookmarks` | List channel bookmarks |
| `create_bookmark` | Create bookmark |
| `update_bookmark` | Update bookmark |
| `delete_bookmark` | Delete bookmark |
| `update_bookmark_sort_order` | Reorder bookmark |

!!! note "Bookmarks require Entry+ edition"
    Bookmark tools require Mattermost Entry, Professional, or Enterprise edition (v10.1+).
