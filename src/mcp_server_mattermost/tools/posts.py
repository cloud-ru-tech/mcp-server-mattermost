"""Post operations: reactions, pins, threads."""

from fastmcp.dependencies import Depends

from mcp_server_mattermost.client import MattermostClient
from mcp_server_mattermost.enums import ToolTag
from mcp_server_mattermost.models import EmojiName, Post, PostId, PostList, Reaction
from mcp_server_mattermost.server import get_client, mcp


@mcp.tool(
    annotations={"destructiveHint": False, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.POST},
)
async def add_reaction(
    post_id: PostId,
    emoji_name: EmojiName,
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> Reaction:
    """Add an emoji reaction to a message.

    Adds a reaction from the authenticated user.
    Common emojis: thumbsup, thumbsdown, smile, heart, eyes.
    Adding the same reaction twice has no additional effect.
    """
    data = await client.add_reaction(
        post_id=post_id,
        emoji_name=emoji_name,
    )
    return Reaction(**data)


@mcp.tool(
    annotations={"destructiveHint": False, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.POST},
)
async def remove_reaction(
    post_id: PostId,
    emoji_name: EmojiName,
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> None:
    """Remove your emoji reaction from a message.

    Removes a reaction previously added by the authenticated user.
    Removing a non-existent reaction has no effect.
    """
    await client.remove_reaction(
        post_id=post_id,
        emoji_name=emoji_name,
    )


@mcp.tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.POST},
)
async def get_reactions(
    post_id: PostId,
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> list[Reaction]:
    """Get all reactions on a message.

    Returns list of reactions with emoji names and user IDs.
    Use to see who reacted to a message and with what emoji.
    """
    data = await client.get_reactions(post_id=post_id)
    return [Reaction(**item) for item in data]


@mcp.tool(
    annotations={"destructiveHint": False, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.POST},
)
async def pin_message(
    post_id: PostId,
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> Post:
    """Pin a message in a channel.

    Pinned messages appear in the channel's pinned posts section.
    Pinning an already pinned message has no additional effect.
    """
    await client.pin_post(post_id=post_id)
    data = await client.get_post(post_id=post_id)
    return Post(**data)


@mcp.tool(
    annotations={"destructiveHint": False, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.POST},
)
async def unpin_message(
    post_id: PostId,
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> Post:
    """Unpin a message from a channel.

    Removes the message from the channel's pinned posts.
    Unpinning a non-pinned message has no effect.
    """
    await client.unpin_post(post_id=post_id)
    data = await client.get_post(post_id=post_id)
    return Post(**data)


@mcp.tool(
    annotations={"readOnlyHint": True, "idempotentHint": True},
    tags={ToolTag.MATTERMOST, ToolTag.POST, ToolTag.MESSAGE},
)
async def get_thread(
    post_id: PostId,
    client: MattermostClient = Depends(get_client),  # type: ignore[arg-type]  # noqa: B008
) -> PostList:
    """Get all messages in a thread.

    Returns the root post and all replies in chronological order.
    Use to read full conversation context before replying.
    """
    data = await client.get_thread(post_id=post_id)
    return PostList(**data)
