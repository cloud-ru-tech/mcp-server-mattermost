# Best Practices

Configure your AI once — get consistent results every day without repeating instructions.

## Tell Your AI About Your Workspace

The biggest lever for AI quality is **workspace context**. When your AI knows which channels
exist and how your team communicates, it makes better decisions about where to read,
what to post, and how to format the result.

Add this to your AI's configuration (adapt channels and conventions to your team):

```markdown
## Mattermost Workspace

Channels:
- #ops — deployment updates, service alerts
- #support — customer questions, bug reports
- #dev — feature discussions, code reviews
- #releases — release announcements

Conventions:
- Use threads for follow-ups, not top-level messages
- Search for existing channels before creating new ones
- Post summaries to Mattermost; keep detailed analysis in conversation
- Use attachments for structured data (status reports, lists)
```

### Where to put it

=== "Claude Code"

    Add to `CLAUDE.md` in project root.

    Claude loads this file automatically at the start of every session.

    [CLAUDE.md documentation](https://docs.anthropic.com/en/docs/claude-code/memory){ target="_blank" }

=== "Cursor"

    Create `.cursor/rules/mattermost.mdc`:

    ```yaml
    ---
    description: "Conventions for Mattermost MCP tools"
    alwaysApply: false
    ---
    ```

    Paste the workspace snippet below the frontmatter.
    With `alwaysApply: false`, the rule loads when Cursor decides it's relevant.

    Note: `.cursorrules` is deprecated — use `.cursor/rules/*.mdc` instead.

    [Cursor Rules documentation](https://docs.cursor.com/context/rules){ target="_blank" }

=== "Claude Desktop"

    Create a Project and paste the workspace snippet into project instructions.
    Instructions apply to all conversations within the project.

    [Claude Desktop Projects documentation](https://support.anthropic.com/en/articles/9517075-what-are-projects){ target="_blank" }

## Write Effective Prompts

How you phrase your request determines how many steps the AI takes
and what result you get. Three patterns cover most Mattermost workflows.

### Source → Analyze → Act

When you need to gather information, make sense of it, and act on the result.

=== "Vague"

    > "Post deployment status to #engineering"

    AI doesn't know where to get data — will ask or make something up.

=== "Specific"

    > "Check #ops for today's deployment messages and post a summary to #engineering"

    AI knows source (#ops), task (summary), and destination (#engineering).
    Executes in 3 tool calls.

### Search → Filter → Report

When you need to find by criteria, filter, and compile a report.

=== "Vague"

    > "What's happening in #support?"

    AI dumps the last few messages without analysis.

=== "Specific"

    > "Find unanswered questions in #support from this week and post a summary for the team"

    AI searches for questions, checks threads for replies, filters unanswered ones,
    and compiles a report.

### Check → Decide → Act

When you need conditional logic — AI checks the situation and decides what to do.

=== "Vague"

    > "Check my question in #backend"

    AI shows the thread but takes no useful action.

=== "Specific"

    > "Check if anyone replied to my question about the API migration in #backend, and if not — ping the team"

    AI checks, makes a decision, and acts accordingly.

## Automate Recurring Workflows

For tasks you run regularly, create a skill — AI executes the entire workflow
by keyword, without repeating instructions each time.

### Example: Deployment Report

```markdown
---
name: deploy-report
description: Post deployment status report to Mattermost. Use when asked about deployment status, deploy report, or service health.
---

Post deployment status report:

1. Get recent messages from #ops using get_channel_messages
2. Identify deployment-related updates
3. Group by status: success, in progress, failed
4. Post summary to #engineering using post_message with attachments:
   - One attachment per service
   - Color: "good" for success, "warning" for in-progress, "danger" for failure
   - Fields: Service, Version, Status
```

=== "Claude Code"

    Save as `.claude/skills/deploy-report.md`.
    Two ways to use: type `/deploy-report` as a slash command,
    or just describe the task — Claude activates the skill automatically
    when context matches the `description` field.

    [Claude Code Skills documentation](https://docs.anthropic.com/en/docs/claude-code/skills){ target="_blank" }

=== "Cursor"

    Save as `.cursor/skills/deploy-report/SKILL.md` with the same frontmatter.
    Invoke with `/deploy-report` in Agent chat,
    or let Cursor activate it automatically when context matches.

    [Cursor Skills documentation](https://cursor.com/docs/context/skills){ target="_blank" }

=== "Claude Desktop"

    Package the directory with `Skill.md` into a ZIP and install
    via Settings → Capabilities.

    [Claude Desktop Skills documentation](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills){ target="_blank" }

### More Ideas

- **Standup rollup** — collect morning updates from #standup, compile a summary for the manager
- **On-call handoff** — summarize incidents and alerts from the shift, post handoff notes for the next rotation
- **Support triage** — find unanswered questions in #support, compile report with age and author
- **Stale threads** — find threads in #dev that went quiet without resolution, remind authors
- **Meeting follow-up** — post action items and decisions to the project channel, tag owners
- **New hire onboarding** — add a person to relevant channels, post a welcome message with useful links

## Combine with Other MCP Servers

Mattermost becomes even more powerful when paired with MCP servers
for other systems. The AI orchestrates across tools in a single prompt.

!!! tip
    Add your other MCP servers to the workspace description
    from [Tell Your AI About Your Workspace](#tell-your-ai-about-your-workspace)
    so the AI knows the full picture.

**Jira + Mattermost** — project management

> "Check overdue tasks in the current sprint and remind assignees in #project-status"

**GitHub / GitLab + Mattermost** — code & CI/CD

> "Find pull requests with no review for 2+ days and nudge reviewers in #dev"

**Confluence + Mattermost** — knowledge sharing

> "Search the wiki for the runbook matching this incident and post the link in the #ops thread"

**Sentry + Mattermost** — monitoring

> "Check for new errors since the last deployment and post a health report to #ops"

**Calendar + Mattermost** — scheduling

> "Check tomorrow's meeting agenda and post a prep summary with context from #dev to the meeting channel"

**Jira + GitHub + Confluence + Mattermost** — full release workflow

> "We're releasing v3.0 next Monday. Gather completed Jira tickets for this version, match them with merged PRs in GitHub, generate release notes, create a release page in Confluence, and post the announcement to #releases with a link to the docs."

## Reference: Mattermost Attachments

For copy-paste into your CLAUDE.md, Cursor rules, or skills:

| Content | Color | Structure |
|---------|-------|-----------|
| Success / healthy | `"good"` (green) | Single attachment with fields |
| Warning / in progress | `"warning"` (yellow) | Single attachment with fields |
| Error / failure | `"danger"` (red) | Single attachment with fields |
| Custom color | `"#1E90FF"` (any hex) | Single attachment with fields |
| Categorized list | Mixed | Multiple attachments, one per category |
| Key-value data | Any | Fields array with `"short": true` |

```json
{
  "attachments": [{
    "fallback": "Plain-text summary for notifications",
    "color": "good",
    "title": "Section Title",
    "text": "Body text with **markdown** support",
    "fields": [
      {"title": "Key", "value": "Value", "short": true},
      {"title": "Key", "value": "Value", "short": true}
    ],
    "footer": "Metadata or timestamp"
  }]
}
```

See [Mattermost Attachment Reference](https://developers.mattermost.com/integrate/reference/message-attachments/)
for the full list of attachment fields (author, images, title links, and more).
