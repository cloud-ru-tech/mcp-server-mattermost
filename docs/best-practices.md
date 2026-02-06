# Best Practices

How to get the best results from AI assistants using MCP Server Mattermost.

## Configure Your AI

The most effective way to improve results is to tell your AI assistant
how you want Mattermost messages formatted. One line of configuration
can make the difference between plain text and rich, color-coded attachments.

### Claude Code (CLAUDE.md)

Add to your project's `CLAUDE.md`:

```markdown
When posting to Mattermost, use rich attachments for structured data:
- Status updates → color-coded attachments ("good", "warning", "danger")
- Key-value data → fields array with short: true
- Multi-section content → multiple attachments with different colors
- Simple replies → plain text message
```

### Cursor (.cursorrules)

Add to `.cursor/rules/mattermost.md`:

```markdown
When using Mattermost MCP tools, post structured data as attachments:

1. Use color field: "good" (green), "warning" (yellow), "danger" (red)
2. Use fields array for key-value pairs with short: true
3. Use multiple attachments to separate categories
4. Add footer for timestamps or metadata
```

### Claude Desktop

Claude Desktop doesn't have persistent configuration for tool behavior.
Use explicit prompts instead — see the next section.

## Write Better Prompts

The way you phrase your request directly affects the output quality.

### Be specific about format

=== "Vague"

    > "Post deployment status to #ops"

    Result: likely plain text.

=== "Specific"

    > "Post deployment status to #ops with color-coded attachments — green for success, yellow for in-progress, red for failures. Include service name, version, and status as fields."

    Result: rich formatted message with colors and structured fields.

### Show the structure you want

When you include an example in your prompt, the AI follows the pattern:

> "Post release notes to #releases. Use this structure: separate attachments
> for Features (green), Bug Fixes (yellow), and Breaking Changes (red).
> Each attachment should have a title and bulleted text."

### Use conditional formatting

Tell the AI when to use which format:

> "Check deployment status in #ops. If all services are healthy — post
> a green summary. If anything is failing — post red with details.
> If something is in progress — yellow."

## Create Reusable Skills

For workflows you run regularly, Claude Code skills automate the entire process.

### Example: Deployment Report Skill

Create `.claude/skills/deploy-report.md`:

```markdown
---
name: deploy-report
description: Post deployment status report to Mattermost. Use when asked about deployment status, deploy report, or service health.
---

Post deployment status report for $ARGUMENTS:

1. Read recent messages from #ops using get_channel_messages
2. Identify deployment-related updates
3. Post summary to #engineering using post_message with attachments:
   - One attachment per service
   - Color: "good" for success, "warning" for in-progress, "danger" for failure
   - Fields: Service (short), Version (short), Status (short), Time (short)
   - Footer: "Last updated: [current time]"
```

Usage: ask Claude Code "post a deploy report" — the skill activates automatically
based on keywords in the description.

### Example: Support Summary Skill

Create `.claude/skills/support-summary.md`:

```markdown
---
name: support-summary
description: Find unanswered questions in Mattermost support channel. Use when asked about support status, unanswered questions, or support summary.
---

Find and report unanswered questions:

1. Search #support for messages with "?" using search_messages
2. Check each thread using get_thread — filter those with no replies
3. Post summary using post_message with attachment:
   - Color: "warning"
   - Title: "N Unanswered Questions This Week"
   - Text: numbered list with @author, days ago, question text
   - Footer: "Reply in thread to mark as answered"
```

## Attachment Quick Reference

For copy-paste into prompts, CLAUDE.md, or skills:

| Content | Color | Structure |
|---------|-------|-----------|
| Success / healthy | `"good"` (green) | Single attachment with fields |
| Warning / in progress | `"warning"` (yellow) | Single attachment with fields |
| Error / failure | `"danger"` (red) | Single attachment with fields |
| Categorized list | Mixed | Multiple attachments, one per category |
| Key-value data | Any | Fields array with `"short": true` |

```json
{
  "attachments": [{
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
for the full list of attachment fields.
