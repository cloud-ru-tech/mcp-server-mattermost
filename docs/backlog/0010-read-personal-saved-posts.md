---
title: "Expose personal saved messages"
summary: "Existing bookmark tools manage channel bookmarks, but agents cannot retrieve the authenticated user's personal saved-message list."
category: feature
created: 2026-09-10
files:
  - src/mcp_server_mattermost/tools/bookmarks.py
  - src/mcp_server_mattermost/tools/posts.py
  - src/mcp_server_mattermost/client.py
---

## Problem and use case

A user asking "Show the messages I saved for later" needs a personal list. Existing
bookmark tools operate on shared channel bookmarks and cannot answer that request.
Their descriptions should remain distinct from the new personal-message workflow.

## Expected behavior

Add a read-only listing operation scoped to the authenticated user's saved posts.
Verify the flagged-posts endpoint against supported server versions and map its
behavior to the user-visible saved list before finalizing the tool contract.
Support pagination and optional team/channel filters where the API supports them.

Return usable post identifiers and content, with enough context for subsequent
message or thread retrieval. Define result ordering and continuation. A bounded
page must not imply that every saved message has been returned. When the API
cannot reveal inaccessible or deleted saved items, document that visibility
limitation rather than inventing missing-item counts.

Use the caller's identity without accepting an arbitrary user by default. Do not
modify saved state or read markers. Saving, unsaving, reminders, and completion
states are separate possible extensions and are outside this listing task.

## Acceptance criteria

- A user can list their accessible saved messages and continue through pages.
- Tests cover an empty list, multiple pages, supported filters, removed channel
  access, and authentication failures.
- Channel bookmarks are neither returned nor changed by this operation.
- Tool naming and descriptions distinguish personal saved messages from bookmarks
  and pinned channel posts.
- Document tested versions, response shape, ordering, and visibility limitations.

Reference: [Mattermost posts specification](https://github.com/mattermost/mattermost/blob/master/api/v4/source/posts.yaml),
GET /users/{user_id}/posts/flagged.
