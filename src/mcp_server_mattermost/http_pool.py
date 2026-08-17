"""Registry owning the HTTP connection pool shared by every Mattermost API call.

``app_lifespan`` is still the owner, as FastMCP's lifespan documentation
prescribes. What lives here is the bookkeeping that a lifespan alone cannot do:

* FastMCP closes a server's lifespan stack as soon as the *first* of several
  concurrent sessions exits, without waiting for the reference count to reach
  zero (``fastmcp/server/mixins/lifespan.py``). Retiring a pool instead of
  closing it outright keeps in-flight requests working and hands the next call
  a fresh pool.
* Tools pulled into someone else's FastMCP server via ``add_tool`` or
  ``import_server``, and direct library use of ``get_client``, run with no
  lifespan of ours at all.
* A composed user lifespan shallow-merges over ours, so a pool published under
  a lifespan context key can be replaced by a foreign client — which would then
  be handed the Mattermost bearer token.

A pool checked out without ``app_lifespan`` is never explicitly closed; it lives
until its event loop is garbage collected. That is inherent to sharing a pool
and is the cost of using these tools as a library.
"""

import asyncio
import threading
import weakref
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import httpx

from .client import create_http_client
from .config import Settings
from .logging import logger


PoolKey = tuple[str, str, int, bool, int, int, float]


@dataclass
class _PoolEntry:
    """A shared pool plus the bookkeeping that decides when it may close."""

    client: httpx.AsyncClient
    key: PoolKey
    refs: int = 0
    retired: bool = False


# One pool per event loop: httpx binds a pool's internal locks to the loop that
# created it, so a pool must never be used from another one. Weak keys let an
# ended loop drop its entry.
_entries: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, _PoolEntry]" = weakref.WeakKeyDictionary()

# Every critical section below is await-free, so a plain threading lock is both
# sufficient and — unlike asyncio.Lock — safe to share between loops.
_guard = threading.Lock()


def _pool_key(settings: Settings) -> PoolKey:
    """Return every setting baked into a pool's transport.

    A pool cannot be reconfigured after creation, so a change to any of these
    has to produce a new pool rather than silently keep serving the old one.

    Args:
        settings: Application configuration.

    Returns:
        Hashable identity of the pool these settings ask for.
    """
    return (
        settings.url,
        settings.api_version,
        settings.timeout,
        settings.verify_ssl,
        settings.max_connections,
        settings.max_keepalive_connections,
        settings.keepalive_expiry,
    )


async def _checkout(settings: Settings) -> _PoolEntry:
    """Borrow the current loop's pool, creating one when there is none to reuse.

    Args:
        settings: Application configuration.

    Returns:
        Entry with its reference count already incremented; the caller must
        hand it back to ``_checkin``.
    """
    loop = asyncio.get_running_loop()
    key = _pool_key(settings)
    orphan: _PoolEntry | None = None

    with _guard:
        entry = _entries.get(loop)
        if entry is not None and (entry.retired or entry.client.is_closed or entry.key != key):
            # Unusable: retire it so its remaining users close it, then start over.
            entry.retired = True
            del _entries[loop]
            if entry.refs <= 0:
                # Nobody left to check it in, so closing it is on us.
                orphan = entry
            entry = None
        if entry is None:
            entry = _PoolEntry(client=create_http_client(settings), key=key)
            _entries[loop] = entry
        entry.refs += 1

    if orphan is not None:
        try:
            await orphan.client.aclose()
        except Exception:  # noqa: BLE001 - a superseded pool must not fail the request that replaced it
            logger.exception("Failed to close a superseded HTTP connection pool")
        else:
            logger.info("HTTP connection pool closed")

    return entry


async def _checkin(entry: _PoolEntry) -> None:
    """Hand a borrowed pool back, closing it once it is retired and unused.

    Args:
        entry: Entry previously returned by ``_checkout``.
    """
    with _guard:
        entry.refs -= 1
        should_close = entry.retired and entry.refs <= 0
    if should_close:
        await entry.client.aclose()
        logger.info("HTTP connection pool closed")


def _retire(entry: _PoolEntry) -> None:
    """Take a pool out of service so no new caller can reach it.

    Args:
        entry: Entry to retire; whoever holds the last reference closes it.
    """
    loop = asyncio.get_running_loop()
    with _guard:
        entry.retired = True
        # Leave a newer entry for this loop alone — it superseded this one.
        if _entries.get(loop) is entry:
            del _entries[loop]


@asynccontextmanager
async def shared_http_client(settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
    """Borrow the shared pool for the duration of a single request.

    Args:
        settings: Application configuration.

    Yields:
        The shared ``httpx.AsyncClient``. Borrowers must not close it.
    """
    entry = await _checkout(settings)
    try:
        yield entry.client
    finally:
        await _checkin(entry)


@asynccontextmanager
async def owned_shared_client(settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
    """Hold the shared pool for a server's lifetime and retire it on shutdown.

    Retiring is not closing: requests still in flight keep the pool alive and
    the last one out closes it, while any new call gets a fresh pool. That is
    what keeps a second, still-open session working when the first one tears
    the lifespan down.

    Args:
        settings: Application configuration.

    Yields:
        The shared ``httpx.AsyncClient``.
    """
    entry = await _checkout(settings)
    try:
        yield entry.client
    finally:
        _retire(entry)
        await _checkin(entry)


async def reset_shared_pool() -> None:
    """Retire the current loop's pool and close it if nobody is using it.

    Borrowers keep working until they return the pool; the next caller gets a
    freshly built one. Useful after changing settings at runtime, and in tests
    that would otherwise carry one test's pool into the next.
    """
    loop = asyncio.get_running_loop()
    with _guard:
        entry = _entries.pop(loop, None)
        should_close = False
        if entry is not None:
            entry.retired = True
            should_close = entry.refs <= 0
    if entry is not None and should_close:
        await entry.client.aclose()
