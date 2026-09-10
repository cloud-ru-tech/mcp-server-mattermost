---
title: "Resolve conversation names and message links"
summary: "Reading by a human-facing channel name requires a separate lookup, and the client get_post method has no dedicated MCP tool for message references."
category: feature
created: 2026-09-10
files:
  - src/mcp_server_mattermost/tools/channels.py
  - src/mcp_server_mattermost/tools/users.py
  - src/mcp_server_mattermost/tools/messages.py
  - src/mcp_server_mattermost/client.py
---

## Problem and use case

Users refer to #channel names, DM participants, and message links rather than
internal IDs. Agents currently need separate lookups, and get_post exists at the
HTTP client layer without a dedicated MCP tool for reading a message reference.

## Expected behavior

Define a shared reference-resolution contract for relevant reading tools, keeping
explicit IDs valid. Scope channel names to an explicit team. Return actionable
ambiguity or not-found errors instead of guessing a team or participant.
Resolving a DM for reading must only find an existing accessible conversation;
creating a DM remains an explicit write/create workflow.

Expose a message-reading operation accepting a post ID or a Mattermost permalink.
Validate links against the configured server and supported deployment subpath,
extract the post ID, and read it through the authenticated API client. Do not
fetch arbitrary supplied URLs. Document accepted link formats and host aliases.

Define message versus thread retrieval explicitly. For a linked reply, preserve
the selected message identity and use its root relationship when thread context
is requested. A cache may accelerate resolution but cannot be required for
correctness or substitute for access checks.

## Acceptance criteria

- A valid ID, scoped channel name, and supported permalink resolve consistently.
- Tests cover duplicate channel names across teams, unknown users, missing DMs,
  reply links, deployment subpaths, malformed links, and foreign hosts.
- Reading a reference never creates a channel or modifies read state.
- Unauthorized references return a clear failure without content disclosure.
- Document the accepted forms and compatibility with existing ID-only calls.
