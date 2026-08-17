"""String constants for user-facing messages."""

# Empty result messages
NO_CHANNELS_FOUND = "No channels found"
NO_MESSAGES_FOUND = "No messages found"
NO_POSTS_FOUND = "No posts found"
NO_USERS_FOUND = "No users found"
NO_TEAMS_FOUND = "No teams found"
NO_FILES_FOUND = "No files found"
NO_REACTIONS_FOUND = "No reactions found"

# Success messages
CHANNEL_CREATED = "Channel created successfully"
CHANNEL_JOINED = "Channel joined successfully"
CHANNEL_LEFT = "Channel left successfully"
USER_ADDED_TO_CHANNEL = "User added to channel successfully"
MESSAGE_POSTED = "Message posted successfully"
MESSAGE_DELETED = "Message deleted successfully"
REACTION_ADDED = "Reaction added successfully"
REACTION_REMOVED = "Reaction removed successfully"
PIN_ADDED = "Message pinned successfully"
PIN_REMOVED = "Message unpinned successfully"
FILE_UPLOADED = "File uploaded successfully"

# API response wrapper keys (from Mattermost Go source)
# See: https://github.com/mattermost/mattermost/blob/master/server/public/model/channel_bookmark.go
UPDATE_BOOKMARK_RESPONSE_KEY = "updated"
