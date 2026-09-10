---
title: "Aggregate unread messages across channels"
summary: "An agent must list unread channels and call get_channel_messages for each one to answer what the user missed across their conversations."
category: feature
created: 2026-09-10
files:
  - src/mcp_server_mattermost/tools/channels.py
  - src/mcp_server_mattermost/tools/messages.py
  - src/mcp_server_mattermost/client.py
  - tests/integration/test_unread_flow.py
---

## Problem and use case

To answer "What did I miss?", an agent currently lists unread channels and fetches
each channel's unread window separately. It must also coordinate limits, ordering,
and failures. This repeated orchestration belongs in a bounded reading operation.

## Expected behavior

Provide an aggregate inbox for an explicit team using existing unread counters
and unread-window methods. Support channel type selection, maximum channels, and
maximum messages per channel. Define deterministic ordering, with direct messages
first and an explicit tie-breaker. A mentions filter should select channels with
mentions; it must not claim that every returned message mentions the user.

Return per-channel identity, unread counters, selected messages, and completeness
metadata. Distinguish total unread counts from fetched message counts. Report
channels omitted by limits, capped message windows, and individual fetch errors.
If channel discovery fails, report failure rather than a successful empty inbox.

Bound concurrent fetches and total work. Preserve cancellation and existing retry
behavior. Respect Collapsed Reply Threads semantics. Never advance read markers,
including to bootstrap never-viewed channels; report that limitation explicitly.
Bot unread state is not a durable processing checkpoint.

## Acceptance criteria

- A single tool call returns bounded unread context from multiple channels.
- Empty inboxes are distinguishable from failed or incomplete reads.
- One channel failure preserves other results and marks the response partial.
- Limits and ordering are deterministic and documented.
- Tests cover channel filters, mentions semantics, CRT modes, never-viewed
  channels, partial failures, cancellation, and unchanged read markers.
