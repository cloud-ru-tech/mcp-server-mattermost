---
title: "Enrich message responses with author identities"
summary: "History, search, and thread responses expose author IDs without resolving names, requiring additional agent calls to understand who said what."
category: feature
created: 2026-09-10
files:
  - src/mcp_server_mattermost/models/post.py
  - src/mcp_server_mattermost/tools/messages.py
  - src/mcp_server_mattermost/tools/posts.py
  - src/mcp_server_mattermost/client.py
---

## Problem and use case

When asked who proposed a change or approved a deployment, an agent receives posts
with user_id values and must retrieve profiles separately. The same author can
appear in many posts and across history, search, and thread responses.

## Expected behavior

Add optional author enrichment to these reading operations using a consistent
response contract. Retain post IDs, author IDs, ordering, pagination, and existing
post fields. A users map keyed by user ID is a candidate representation that
avoids repeating profiles for every message.

Return the minimum useful identity fields, such as username and display name.
Collect unique author IDs across the returned posts, including contextual thread
roots, and fetch profiles in batches. Deduplicate lookups within the operation.
Define batch limits against the supported Mattermost API. A persistent cache is
not required for this feature.

If enrichment fails, retain the messages and unresolved IDs and expose that
identity information is incomplete. Do not invent names or silently assign one
user's identity to another. Use the same authenticated context as the post read.

## Acceptance criteria

- Existing calls remain compatible when enrichment is not requested.
- History, search, and thread results use the same identity representation.
- Multiple posts by one author do not cause one HTTP request per post.
- Missing or inaccessible profiles do not discard otherwise readable messages.
- Tests cover repeated authors, contextual roots, partial profile responses, and
  profile lookup failures.
- A representative comparison records added payload size and avoided agent calls.

Reference: [Mattermost batch user lookup](https://docs.mattermost.com/api/reference/get-users-by-ids).
