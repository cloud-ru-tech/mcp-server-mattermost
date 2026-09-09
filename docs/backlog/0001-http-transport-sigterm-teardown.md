---
title: "HTTP transport: lifespan teardown does not run on SIGTERM"
summary: On `--http`, a SIGTERM shutdown never finishes the lifespan, so the shared
  HTTP pool and the auth provider are not closed and no shutdown logs are written.
  `docker stop` sends exactly SIGTERM. Both stdio and SIGINT work.
category: bug
created: 2026-09-04
files:
  - src/mcp_server_mattermost/__init__.py
  - src/mcp_server_mattermost/server.py
  - src/mcp_server_mattermost/http_pool.py
---

Not our bug: it reproduces on bare `FastMCP` with an empty lifespan, without a single
line of project code. Verified on 3.4.4.

**Matrix:**

| Entry point | Signal | Teardown |
| --- | --- | --- |
| `mcp.run(transport="http")` — what `main()` does | SIGTERM | never runs, not even `finally` |
| `mcp.run(transport="http")` | SIGINT | runs fully |
| `uvicorn.run(mcp.http_app())` | SIGTERM | runs fully |
| stdio (`mcp.run(transport="stdio")`) | EOF on stdin | runs fully |

On SIGTERM uvicorn logs `Waiting for application shutdown.` and then immediately
`Finished server process` — it does not wait for the lifespan.

**Consequences:** `HTTP connection pool closed` and `Mattermost MCP server shutdown
complete` are never written, and `_close_auth_provider` is never called. The OS reclaims
the sockets when the process exits, so nothing leaks beyond the process — what breaks is
graceful shutdown itself, for anything anyone puts in the lifespan, not just the pool.

**Reproduce:**

```bash
MATTERMOST_URL=http://127.0.0.1:59999 MATTERMOST_TOKEN=t MATTERMOST_LOG_FORMAT=text \
  uv run mcp-server-mattermost --http --port 8811 2>&1 | tee /tmp/probe.log &
sleep 6 && kill -TERM $(pgrep -f "mcp-server-mattermost --http" | tail -1)
grep "connection pool" /tmp/probe.log   # expect a created/closed pair; only created appears
```

**Verify any fix on all three paths:** `--http`, stdio, `fastmcp run`. Candidates — run
uvicorn ourselves via `mcp.http_app()` instead of `mcp.run(transport="http")`, or file an
issue against PrefectHQ/fastmcp.
