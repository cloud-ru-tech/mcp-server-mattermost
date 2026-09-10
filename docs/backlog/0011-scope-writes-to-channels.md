---
title: "Evaluate channel restrictions for write operations"
summary: "Client-side capability filtering selects tools but does not itself enforce that a bot writes only to designated channels."
category: other
created: 2026-09-10
files:
  - src/mcp_server_mattermost/config.py
  - src/mcp_server_mattermost/server.py
  - src/mcp_server_mattermost/deps.py
  - docs/building-agents.md
---

## Problem and deployment scenario

A bot may need broad read access while being allowed to publish only in designated
channels. Client-side capability profiles control tool selection, but do not
enforce resource-level restrictions on calls that reach the server.

## Design investigation

Evaluate an optional server-side write policy independently from capability
profiles, which remain client-side. Define whether configuration applies to the
whole deployment or each authenticated identity, including per-client tokens.
Specify behavior when the policy is absent and when its configuration is invalid.

Inventory channel-scoped mutations: message posting/editing/deletion, reactions,
pins, uploads, bookmarks, and membership changes. Decide explicitly how creation
operations and writes without a channel scope are handled. A policy must cover
indirect references such as post_id or bookmark_id by resolving the authoritative
channel under the caller's credentials before mutation.

Choose a centralized enforcement point and document coverage for stdio, HTTP,
and tools imported into another server. Tool visibility and alternate reference
forms must not bypass an enabled restriction. Failed channel resolution must not
permit a write. Cached metadata must not authorize access after permissions change.

## Acceptance criteria for the investigation

- Produce a policy contract, operation coverage matrix, and recommended enforcement
  point, including limits for embedded/library use.
- Document identity scope, configuration validation, and denial behavior.
- Define tests for allowed/denied direct channels, indirect IDs, multiple client
  identities, failed resolution, and changed access.
- Preserve client-defined capability profiles and distinguish filtering from
  enforcement in agent documentation.
- Record the decision and implementation scope before adding per-tool switches.
