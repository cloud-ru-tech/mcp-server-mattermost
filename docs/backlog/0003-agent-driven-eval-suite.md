---
title: "Agent-driven eval suite for tool-selection scenarios"
summary: Integration tests script every tool call, so nothing checks how a real LLM agent uses the
  server — whether it follows server instructions, picks the right tool, or wastes calls on
  validation errors.
category: feature
created: 2026-10-22
files:
  - tests/integration/conftest.py
  - src/mcp_server_mattermost/server.py
---

**Problem:** `tests/integration/` drives the server through `fastmcp.Client` with hand-written calls.
Behaviour that depends on the model — reading instructions, omitting or passing arguments, choosing
discovery calls — is untested.

**Shape:**
- Scenario file: user prompt, server env, expectations on the tool-call trace
  (e.g. "no `list_teams`", "`create_channel` hit team X", "no validation errors").
- Runner: `claude -p` with a temporary `--mcp-config` or the Claude Agent SDK, against the server
  from the working tree and the Testcontainers Mattermost.
- Assertions from server logs (`request_id`, `default_team_resolved`), not from model text.
- Separate pytest marker, outside regular CI: needs an API key, costs money, non-deterministic —
  run each scenario N times and assert a pass rate.

**First scenarios:** `MATTERMOST_DEFAULT_TEAM_ID` set — no `list_teams`, no `team_id` passed;
unset — `list_teams` first, no validation-error round trip.
