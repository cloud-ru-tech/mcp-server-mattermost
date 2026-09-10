---
title: "Make search completeness and date filters explicit"
summary: "search_messages exposes terms and is_or_search but no pagination controls, making broad searches difficult to continue or assess for completeness."
category: feature
created: 2026-09-10
files:
  - src/mcp_server_mattermost/tools/messages.py
  - src/mcp_server_mattermost/client.py
---

## Problem and use case

An agent searching a busy team can receive a bounded result without controls to
continue the search. It cannot confidently distinguish "all matches" from "the
returned matches". Date filters also require knowledge of query syntax and time
boundaries.

## Expected behavior

Establish result caps, ordering, and continuation behavior for the supported
Mattermost versions and search backends before extending search_messages. Verify
page/per_page support rather than assuming it: the referenced specification
labels these search controls as Elasticsearch-only.

Expose continuation where supported. Otherwise make the limitation visible and
provide an actionable way to narrow the query. Distinguish known incomplete,
known complete, and unknown completeness where the API cannot establish it.
Do not infer an exact total solely from the returned item count.

Add structured channel, author, and absolute date filters while retaining raw
terms. Specify how filters combine and reject conflicting inputs. Define the
timezone, inclusive/exclusive date boundaries, and valid formats. Return errors
that identify the invalid filter. Keep creation-date searches separate from since,
which represents post changes and may include edits to older messages.

## Acceptance criteria

- Document a tested backend/version behavior matrix and any unverified cases.
- Broad searches expose supported continuation or an explicit limitation.
- Tests cover multiple pages, empty results, response caps, invalid filters,
  timezone boundaries, and conflicting raw and structured filters.
- Existing raw-term searches remain usable without new required arguments.
- Tool descriptions tell agents how to continue or narrow incomplete searches.

Reference: [Mattermost posts specification](https://github.com/mattermost/mattermost/blob/master/api/v4/source/posts.yaml).
