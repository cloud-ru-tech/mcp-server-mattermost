# Building Agents

Integrate MCP Server Mattermost into multi-agent systems.
This page covers tool metadata, access profiles, and filtering patterns
for agent frameworks.

## Tool Annotations

Every tool exposes standard [MCP annotations](https://modelcontextprotocol.io/specification/2025-06-18/server/tools#annotations)
that describe its behavior:

| Annotation | Meaning |
|------------|---------|
| `readOnlyHint` | Tool only reads data, no side effects |
| `destructiveHint` | Operation is irreversible (data loss) |
| `idempotentHint` | Repeated calls produce the same result |

How this server uses them:

| Operation type | readOnlyHint | destructiveHint | idempotentHint | Example |
|----------------|:---:|:---:|:---:|---------|
| Read | true | — | true | `list_channels`, `get_user` |
| Write (idempotent) | — | false | true | `join_channel`, `pin_message` |
| Write (non-idempotent) | — | false | — | `post_message` |
| Destructive | — | true | — | `delete_message` |

!!! note "FastMCP defaults"
    Unset annotations use FastMCP defaults: `readOnlyHint=false`,
    `destructiveHint=true`, `idempotentHint=false`.
    A dash (—) in the table means the default applies.

## Capability Metadata

In addition to standard annotations, each tool carries a `capability` label
in `meta` — a single word describing what the tool does:

| Capability | Meaning | Example tools |
|------------|---------|---------------|
| `read` | Retrieve data, no side effects | `list_channels`, `search_messages`, `get_user` |
| `write` | Modify state within existing resources | `post_message`, `add_reaction`, `upload_file` |
| `create` | Create new top-level entities | `create_channel`, `create_direct_channel` |
| `delete` | Permanently destroy a resource | `delete_message`, `delete_bookmark` |

Classification rules:

- **create** — only for new standalone entities (channels, DMs)
- **write** — all other modifications, including dependent resources
  (bookmarks, messages, reactions exist only inside a channel)
- **delete** — resource permanently ceases to exist
- Each tool gets exactly one capability

## Wire Format

Here's what a client receives from `tools/list` for a read-only tool:

```json
{
  "name": "list_channels",
  "description": "List public and private channels in a team. ...",
  "inputSchema": {
    "type": "object",
    "properties": {
      "team_id": {"type": "string"},
      "page": {"type": "integer", "minimum": 0},
      "per_page": {"type": "integer", "minimum": 1, "maximum": 200}
    },
    "required": ["team_id"]
  },
  "annotations": {
    "readOnlyHint": true,
    "idempotentHint": true
  },
  "tags": ["mattermost", "channel"],
  "_meta": {
    "capability": "read"
  }
}
```

And for a destructive tool:

```json
{
  "name": "delete_message",
  "description": "Delete a message permanently. ...",
  "inputSchema": {"...": "..."},
  "annotations": {
    "destructiveHint": true
  },
  "tags": ["mattermost", "message"],
  "_meta": {
    "capability": "delete"
  }
}
```

## Agent Profiles

Define profiles as sets of allowed capabilities. Each profile includes
all capabilities below it:

```python
PROFILES = {
    "reader":  {"read"},
    "writer":  {"read", "write"},
    "manager": {"read", "write", "create"},
    "admin":   {"read", "write", "create", "delete"},
}
```

| Profile | Can do | Use case |
|---------|--------|----------|
| reader | Browse channels, search messages, look up users | Monitoring, analytics, digest bots |
| writer | Post messages, react, pin, upload files | Chat bots, notification agents |
| manager | Create channels, open DMs | Onboarding agents, project setup |
| admin | Delete messages and bookmarks | Moderation, cleanup agents |

## Filtering Tools

Use capability metadata to give each agent only the tools it needs.

### pydantic-ai

```python
from pydantic_ai.mcp import MCPServerStdio

server = MCPServerStdio("uvx", args=["mcp-server-mattermost"])

WRITER_CAPS = {"read", "write"}
writer_toolset = server.filtered(
    lambda ctx, td: (td.metadata or {}).get("meta", {}).get("capability") in WRITER_CAPS
)
```

### LangChain

```python
from langchain_mcp_adapters.tools import load_mcp_tools

tools = await load_mcp_tools(session)

allowed = PROFILES["writer"]
agent_tools = [
    t for t in tools
    if (t.metadata or {}).get("_meta", {}).get("capability") in allowed
]
```

### MCP SDK (low-level)

```python
from mcp import ClientSession

async with ClientSession(read_stream, write_stream) as session:
    await session.initialize()
    tools = await session.list_tools()

    allowed = {"read", "write"}
    agent_tools = [
        t for t in tools.tools
        if (t.meta or {}).get("capability") in allowed
    ]
```

## Combining Annotations and Capabilities

Annotations and capabilities serve different purposes but work well together.
Capabilities answer "what does this tool do?" while annotations answer
"how safe is it to call?"

Example: give an agent only safe, read-only tools that are guaranteed idempotent:

```python
def is_safe_reader(tool) -> bool:
    ann = tool.annotations
    meta = tool.meta or {}
    return (
        meta.get("capability") == "read"
        and getattr(ann, "readOnlyHint", None) is True
        and getattr(ann, "idempotentHint", None) is True
    )

safe_tools = [t for t in tools.tools if is_safe_reader(t)]
```

Use annotations for **runtime safety** (confirmation dialogs, retry logic)
and capabilities for **access control** (which tools an agent can see).

## Error Responses

When a tool call fails, the server returns a result with `isError: true`
and a text message describing what went wrong. The server automatically
retries rate limits (429) and server errors (5xx) with exponential backoff
before surfacing the error.

Common errors your agent may encounter:

| Error | Cause | Agent action |
|-------|-------|--------------|
| `Authentication failed` | Invalid or expired token | Stop — fix configuration |
| `Resource not found` | Wrong channel/user/post ID | Check ID and retry with correct one |
| `Client error: ...` | Missing permissions (403), bad request (400) | Read the message — usually explains what's wrong |
| `Rate limit exceeded` | All retries exhausted | Back off and retry later |
| `Server error: ...` | Mattermost server issue (5xx), all retries exhausted | Retry after a delay |

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{"type": "text", "text": "Resource not found status=404"}],
    "isError": true
  }
}
```

Check `isError` in the result — don't assume every response is success data.

## End-to-End Example

A complete agent that connects to the server, filters tools by capability,
calls a tool, and handles the result. Uses the MCP SDK directly.

```python
import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROFILES = {
    "reader":  {"read"},
    "writer":  {"read", "write"},
    "manager": {"read", "write", "create"},
    "admin":   {"read", "write", "create", "delete"},
}


async def main():
    # 1. Connect to the server
    server_params = StdioServerParameters(
        command="uvx",
        args=["mcp-server-mattermost"],
        env={
            "MATTERMOST_URL": "https://your-server.com",
            "MATTERMOST_TOKEN": "your-bot-token",
        },
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 2. List tools and filter by profile
            all_tools = await session.list_tools()
            allowed = PROFILES["writer"]
            tools = [
                t for t in all_tools.tools
                if (t.meta or {}).get("capability") in allowed
            ]
            print(f"Agent has {len(tools)} tools (writer profile)")

            # 3. Call a tool
            result = await session.call_tool(
                "post_message",
                {
                    "channel_id": "your-channel-id",
                    "message": "Hello from my agent!",
                },
            )

            # 4. Handle the result
            if result.isError:
                error_text = result.content[0].text
                print(f"Tool failed: {error_text}")
            else:
                print(f"Message posted: {result.content[0].text}")


asyncio.run(main())
```
