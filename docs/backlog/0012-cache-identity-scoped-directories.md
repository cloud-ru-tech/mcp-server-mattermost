---
title: "Evaluate caching for user and channel lookups"
summary: "Author enrichment and reference resolution can repeatedly fetch the same metadata, while a shared directory cache could expose data across client identities."
category: other
created: 2026-09-10
files:
  - src/mcp_server_mattermost/client.py
  - src/mcp_server_mattermost/deps.py
  - src/mcp_server_mattermost/config.py
---

## Problem and workload

Author enrichment and human-reference resolution can repeatedly retrieve the same
profiles and channel metadata. Caching may reduce latency and API calls, but the
server supports different client identities whose accessible data can differ.

## Investigation and candidate design

Measure repeated lookup frequency, latency, and HTTP request counts on representative
workflows. Compare request-local deduplication with bounded in-memory cross-request
caching before considering disk persistence. Recommend no persistent cache if the
measured benefit does not justify its lifecycle and isolation costs.

For a shared cache, define keys including server and authorization context, size
limits, TTL, eviction, and behavior on token or permission changes. Do not put raw
tokens in filenames or logs. Scope negative lookups as carefully as successful
ones. A cached profile or channel must never substitute for API authorization.

Define concurrent refresh coalescing, cancellation, and failure behavior. Distinguish
an authoritative empty result from a failed or partial fetch. Known-ID reads must
work without a preloaded directory. Decide whether stale metadata may be returned
and how staleness is exposed; stale entries must not authorize mutations.

Only if disk storage is justified, define atomic writes, restricted permissions,
format versioning, corruption recovery, and deletion behavior.

## Acceptance criteria

- Produce a reproducible baseline and comparison with an adoption recommendation.
- Document cache scope, keys, limits, freshness, and invalidation semantics.
- Verify isolation across servers and client identities, including negative results.
- Test concurrent misses, refresh failures, eviction, cancellation, token changes,
  and permission revocation for any implemented cache.
- Cache failure or an empty directory does not disable direct API reads.
- Separate measured benefits from assumptions in the recorded decision.
