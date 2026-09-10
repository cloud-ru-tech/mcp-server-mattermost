---
title: "Evaluate compact message responses for agents"
summary: "Full post responses can carry substantial service metadata, while useful integration content remains nested in attachments and other extra fields."
category: other
created: 2026-09-10
files:
  - src/mcp_server_mattermost/models/post.py
  - src/mcp_server_mattermost/models/base.py
  - src/mcp_server_mattermost/tools/messages.py
---

## Problem and use case

An agent summarizing a conversation receives service metadata alongside message
content. Useful integration notifications may be nested in attachments. The
current extra="allow" models preserve such fields, but do not organize them for
concise reading. A smaller response could help, provided it retains meaning.

## Investigation and candidate behavior

Compare the existing response with an optional compact structured representation
for history, search, and threads. Candidate fields include post and author IDs,
text, time, channel, thread root, file references, and readable attachment titles,
text, and fields. Preserve links and meaningful formatting in integration content.

Keep full responses available. Define treatment of edits, deleted posts, reactions,
and system events before selecting fields. An explicit system-event filter must
not make a filtered empty page appear to end pagination. Continuation and
completeness metadata belong at response level, independent of visible messages.

Use representative conversations, long threads, and CI or monitoring notifications.
Measure response bytes, tokens under a named tokenizer, and factual answer quality
on the same inputs. Compare omitted facts and incorrect attributions as well as
size reduction. Coordinate with the agent workflow evaluation task.

## Acceptance criteria

- Produce a documented schema candidate, fixtures, and a reproducible comparison.
- Identify which fields are essential for attribution, navigation, and follow-up
  calls; demonstrate that the candidate preserves them.
- Report measured tradeoffs and recommend adoption, revision, or no change.
- If adopted, keep the format opt-in and verify compatibility with existing calls.
- Tests cover attachment-only content and pages emptied by system-event filtering.

This task evaluates a format; no compression benefit or replacement of the
existing response format is assumed in advance.
