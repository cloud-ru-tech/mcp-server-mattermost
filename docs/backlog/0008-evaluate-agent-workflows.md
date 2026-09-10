---
title: "Evaluate MCP workflows with a real model"
summary: "Protocol and API tests do not establish whether a model selects the right tools, notices incomplete results, or completes tasks with few calls."
category: other
created: 2026-09-10
files:
  - tests/integration/test_unread_flow.py
  - docs/building-agents.md
---

## Problem and use case

Protocol and API tests verify that tools execute correctly, but cannot show
whether a model chooses the right tools or recognizes an incomplete result.
Changes to descriptions and response formats need a repeatable task-level check.

## Expected evaluation suite

Build a separately invoked suite using controlled Mattermost data and a real
model. Initial scenarios should cover author attribution in a thread, attachment
inspection, unread summaries across channels, and incomplete search reporting.
Use known expected facts and permissible operations for each scenario.

Record task success, tool names and call counts, response size, elapsed time, and
unexpected writes. Define a call budget, timeout, and spending bound. Record model
identifier, model settings, server revision, fixture version, and scenario inputs.
Make missing model credentials a clear setup result, not an apparent successful run.

Compare baseline and changed behavior on equivalent fixtures. Repeat runs enough
to expose variability, within the configured budget. Separate provider/network
failures from task failures. Prefer checks of known facts and tool traces over
exact wording of natural-language answers.

Use dedicated test accounts and data. Keep deterministic fastmcp.Client tests as
required correctness checks; optional model runs should not make normal CI depend
on model credentials or nondeterministic output.

## Acceptance criteria

- Document one command, required setup, budgets, and fixture cleanup.
- Produce per-scenario results and an aggregate report with configuration details.
- Detect an unnecessary write and a falsely complete summary in controlled cases.
- Support comparisons for author enrichment and compact-response experiments.
- Failed, skipped, timed-out, and successful scenarios are distinguishable.
