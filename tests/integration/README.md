# Integration Tests

Integration tests for MCP Server Mattermost.

## Architecture

Tests run **through MCP protocol** using `fastmcp.Client` against real Mattermost server:

```text
pytest test
    │
    ▼
fastmcp.Client(mcp)          ← In-memory MCP transport
    │
    ▼
FastMCP Server               ← MCP protocol + Pydantic validation
    │
    ▼
MattermostClient             ← HTTP + retry logic
    │
    ▼
Mattermost Server            ← Testcontainers or external
```

**What gets tested:**

- MCP protocol (tools/list, tools/call)
- JSON-RPC serialization
- Pydantic input validation
- FastMCP tool routing
- MattermostClient HTTP logic
- Real Mattermost API

## Running Tests

```bash
# With Testcontainers (needs Docker)
uv run pytest tests/integration

# Against external server
export MATTERMOST_URL=https://your-server.com
export MATTERMOST_TOKEN=your-bot-token
uv run pytest tests/integration

# Specific module
uv run pytest tests/integration/test_channels.py -v
```

## Test Example

```python
async def test_list_channels(mcp_client, team):
    """Test through MCP protocol."""
    result = await mcp_client.call_tool(
        "list_channels",
        {"team_id": team["id"]},
    )

    channels = result.data
    assert any(ch["name"] == "town-square" for ch in channels)
```

## Test Prefix

All test resources use `mcp-test-` prefix for identification and cleanup.

---

# Test Scenarios Checklist

## Users

### Happy Path

- [ ] get_me: returns bot user with is_bot=true
- [ ] get_user: returns user by valid ID
- [ ] get_user_by_username: returns user by username
- [ ] search_users: finds user by partial name
- [ ] search_users: returns empty for non-matching term
- [ ] get_user_status: returns status (online/away/offline/dnd)

### Validation

- [x] get_user: ValidationError for short ID (< 26 chars)
- [x] get_user: ValidationError for ID with special characters
- [x] get_user: 404 for non-existent valid ID
- [x] get_user_by_username: ValidationError for empty username
- [x] get_user_by_username: ValidationError for username starting with digit
- [x] get_user_by_username: ValidationError for username with @
- [x] get_user_by_username: ValidationError for username starting with underscore
- [x] get_user_by_username: ValidationError for username > 64 chars
- [x] get_user_by_username: accepts valid special chars (dots, underscores, hyphens)
- [x] search_users: ValidationError for empty term
- [x] search_users: ValidationError for term > 256 chars
- [x] search_users: accepts Unicode search term

---

## Teams

### Happy Path

- [ ] list_teams: returns array with at least 1 team
- [ ] get_team: returns team by ID
- [ ] get_team_members: returns array including bot user

### Validation

- [ ] get_team: 404 for non-existent valid ID

---

## Channels

### Happy Path

- [ ] list_channels: returns public channels including town-square
- [ ] get_channel: returns channel by ID
- [ ] get_channel_by_name: returns channel by name
- [ ] create_channel: creates public channel (type=O)
- [ ] create_channel: creates private channel (type=P)
- [ ] get_channel_members: returns members including creator
- [ ] join_channel: joins public channel
- [ ] join_channel: idempotent (no error if already member)
- [ ] leave_channel: leaves channel successfully
- [ ] add_user_to_channel: adds user to channel
- [ ] add_user_to_channel: idempotent (no error if already member)
- [ ] create_direct_channel: creates DM between two users
- [ ] create_direct_channel: returns same channel if already exists
- [ ] create_direct_channel: returns same channel with reversed user order

### Validation — Channel Name

- [x] create_channel: ValidationError for empty name
- [x] create_channel: ValidationError for name < 2 chars
- [x] create_channel: ValidationError for name > 64 chars
- [x] create_channel: ValidationError for uppercase in name
- [x] create_channel: ValidationError for name starting with underscore
- [x] create_channel: ValidationError for name starting with hyphen
- [x] create_channel: ValidationError for name with special characters
- [x] create_channel: ValidationError for name with space
- [x] create_channel: accepts name starting with digit
- [x] create_channel: accepts name with allowed chars (lowercase, digits, underscore, hyphen)
- [x] create_channel: accepts name at max length (64 chars)

### Validation — Display Name

- [x] create_channel: ValidationError for empty display_name
- [x] create_channel: ValidationError for display_name > 64 chars
- [x] create_channel: accepts single char display_name
- [x] create_channel: accepts display_name with Unicode
- [x] create_channel: accepts display_name with emoji
- [x] create_channel: accepts display_name with special characters

### Validation — Channel Type

- [x] create_channel: ValidationError for invalid type (X)
- [x] create_channel: ValidationError for type as word (public)
- [x] create_channel: ValidationError for lowercase type (o)

### Validation — Purpose & Header

- [ ] create_channel: accepts empty purpose (default)
- [ ] create_channel: accepts purpose at max (250 chars)
- [ ] create_channel: ValidationError for purpose > 250 chars
- [ ] create_channel: accepts empty header (default)
- [ ] create_channel: accepts header at max (1024 chars)
- [ ] create_channel: ValidationError for header > 1024 chars
- [ ] create_channel: accepts all fields at max length simultaneously

### Pagination

- [x] list_channels: returns 1 item with per_page=1
- [ ] list_channels: returns up to 200 items with per_page=200
- [x] list_channels: returns empty array for page=9999
- [x] list_channels: ValidationError for per_page=0
- [x] list_channels: ValidationError for per_page > 200
- [x] list_channels: ValidationError for negative page

### Permissions & State

- [x] leave_channel: error for town-square (default channel)
- [ ] leave_channel: success for private channel
- [ ] join_channel: error for private channel after leaving
- [x] create_channel: error for duplicate channel name
- [x] get_channel: 404 for non-existent ID
- [x] create_direct_channel: 404 for non-existent user ID
- [ ] leave_channel: error for DM channel

### Private Channel Flow

- [ ] create private channel
- [ ] add user to private channel
- [ ] verify members in private channel
- [ ] post in private channel
- [ ] leave private channel
- [ ] get_channel returns 403 after leaving
- [ ] get_channel_messages returns 403 after leaving

---

## Messages

### Happy Path

- [ ] post_message: creates message with text
- [ ] post_message: creates reply with root_id
- [ ] post_message: creates message with file attachment
- [ ] post_message: creates message with multiple attachments
- [ ] get_channel_messages: returns messages in reverse chronological order
- [ ] get_channel_messages: finds specific message in results
- [ ] update_message: updates message content
- [ ] update_message: sets edit_at > 0
- [ ] delete_message: deletes message successfully
- [ ] search_messages: finds message by content
- [ ] search_messages: supports from: syntax
- [ ] search_messages: supports in: syntax
- [ ] search_messages: supports combined filters
- [ ] search_messages: supports phrase search with quotes
- [ ] search_messages: OR search returns >= AND results

### Validation — Message Content

- [x] post_message: accepts minimum message (1 char)
- [ ] post_message: accepts maximum message (16383 chars)
- [x] post_message: ValidationError for empty message
- [x] post_message: ValidationError for message > 16383 chars
- [ ] update_message: accepts message at max length

### Validation — Search Terms

- [x] search_messages: ValidationError for empty terms
- [x] search_messages: ValidationError for terms > 512 chars
- [ ] search_messages: accepts terms at max length
- [ ] search_messages: accepts special syntax operators

### Pagination

- [x] get_channel_messages: pagination with per_page=1
- [ ] get_channel_messages: collects all messages via pagination
- [x] get_channel_messages: ValidationError for per_page=0
- [x] get_channel_messages: ValidationError for per_page > 200
- [x] get_channel_messages: ValidationError for negative page

### Special Content

- [ ] post_message: preserves Markdown formatting
- [ ] post_message: preserves code blocks
- [ ] post_message: preserves @mention
- [ ] post_message: preserves Cyrillic text
- [ ] post_message: preserves emoji in text
- [ ] post_message: handles URL auto-linking
- [ ] search_messages: finds Cyrillic text

### Permissions

- [ ] update_message: 403 for other user's message
- [ ] delete_message: 403 for other user's message
- [x] update_message: error for deleted message

---

## Posts (Reactions, Pins, Threads)

### Reactions — Happy Path

- [ ] add_reaction: adds reaction to post
- [ ] add_reaction: idempotent (no error for duplicate)
- [ ] get_reactions: returns reactions array
- [ ] get_reactions: returns empty array for post without reactions
- [ ] remove_reaction: removes reaction
- [ ] remove_reaction: success for non-existent reaction (no-op)

### Reactions — Validation

- [x] add_reaction: ValidationError for empty emoji_name
- [x] add_reaction: ValidationError for emoji with colons
- [x] add_reaction: ValidationError for emoji with space
- [x] add_reaction: ValidationError for emoji > 64 chars
- [x] add_reaction: ValidationError for emoji with invalid chars (@, .)
- [x] add_reaction: accepts emoji with allowed chars (alphanumeric, _, -, +)
- [x] add_reaction: accepts emoji at max length (64 chars)
- [ ] add_reaction: error for deleted post

### Pins — Happy Path

- [ ] pin_message: pins message (is_pinned=true)
- [ ] pin_message: idempotent (no error for already pinned)
- [ ] unpin_message: unpins message (is_pinned=false)
- [ ] unpin_message: idempotent (no error for not pinned)

### Threads — Happy Path

- [ ] get_thread: returns thread with root + replies
- [ ] get_thread: returns only root for post without replies
- [ ] get_thread: returns chronological order in order array
- [ ] post reply: root_id points to original root (single-level)
- [ ] reply to reply: remaps to original root

### Threads — Operations

- [ ] pin thread reply
- [ ] react on thread reply
- [ ] update thread reply
- [ ] delete thread reply
- [ ] delete root post makes thread unavailable

---

## Files

### Happy Path

- [ ] upload_file: uploads file successfully
- [ ] upload_file: returns file ID
- [ ] get_file_info: returns file metadata (id, name, size)
- [ ] get_file_link: returns downloadable link
- [ ] post_message with file_ids: attaches file to message

### Validation

- [ ] upload_file: FileNotFoundError for non-existent path
- [ ] upload_file: IsADirectoryError for directory path
- [ ] upload_file: accepts custom filename parameter
- [ ] get_file_info: 404 for non-existent file ID

### File Types

- [ ] upload_file: accepts empty file (0 bytes) — document behavior
- [ ] upload_file: accepts single byte file
- [ ] upload_file: accepts binary file (PNG)
- [ ] upload_file: accepts file without extension
- [ ] upload_file: accepts large file (1MB)
- [ ] upload_file: detects correct mime_type for each type
- [ ] upload_file: accepts Unicode filename
- [ ] upload_file: accepts special chars in filename

### Multiple Files

- [ ] upload multiple files: returns unique IDs
- [ ] post with multiple file_ids: all attachments preserved
- [ ] duplicate file upload: returns different IDs (not deduplicated)

---

## DM Channels

### Happy Path

- [x] create_direct_channel: creates DM with type=D
- [ ] get_channel: returns DM info
- [ ] get_channel_members: returns exactly 2 members
- [x] post_message: posts to DM
- [x] get_channel_messages: returns DM messages
- [ ] update_message: updates DM message
- [ ] delete_message: deletes DM message

### Threading in DM

- [x] post reply in DM with root_id
- [ ] get_thread in DM returns all posts

### Reactions in DM

- [x] add_reaction in DM
- [ ] get_reactions in DM
- [ ] remove_reaction in DM
- [ ] pin_message in DM
- [ ] unpin_message in DM

### Search in DM

- [ ] search_messages: finds DM message
- [ ] search_messages with from:: finds DM message

### Edge Cases

- [ ] create_direct_channel: idempotent (returns same channel)
- [ ] create_direct_channel: reversed user order returns same channel
- [ ] create_direct_channel: self-DM — document behavior
- [ ] create_direct_channel: 404 for non-existent user
- [ ] leave_channel: error for DM
- [ ] file attachment in DM

---

## Combined & Stress Tests (Optional)

### Combined Operations

- [ ] post with empty file_ids array
- [ ] post with invalid file ID: ValidationError
- [ ] create channel with all fields at boundaries
- [ ] nested thread: root + 5 replies + reactions + pins

### Stress Tests

- [ ] bulk post 50 messages
- [ ] rapid reads 20x get_channel_messages
- [ ] bulk delete 50 messages
- [ ] pagination through 100+ messages
- [ ] deep thread with 100 replies

---

# Known Issues

1. **Group Channel Type Not Supported** — create_channel only supports O (public) and P (private), not G (group)
2. **Post After Leave Bug** — Bot can post to private channel after leaving (should be 403)
3. **Archive Channel Not Supported** — No archive_channel tool available

---

# Test Data Cleanup

Tests use fixtures with automatic cleanup:
- **Session-scoped:** team, bot_user, mcp_client (reused across all tests)
- **Function-scoped:** test_channel, test_post (created/deleted per test)
- **Orphan cleanup:** removes `mcp-test-*` resources before test run

## References

- [FastMCP Testing Guide](https://gofastmcp.com/development/tests)
- [MCP Best Practices](https://modelcontextprotocol.info/docs/best-practices/)
