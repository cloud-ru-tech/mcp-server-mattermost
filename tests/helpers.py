"""Shared test helpers."""

import asyncio
import contextlib
import socket
import threading
import time
from typing import Any

import uvicorn


class UvicornTestServer(threading.Thread):
    """Runs a uvicorn server in a background thread with its own event loop."""

    def __init__(self, app: Any, host: str = "127.0.0.1", port: int = 0) -> None:
        super().__init__(daemon=True)
        self._app = app
        self.host = host
        self.port = port or self._find_free_port()
        self._started = threading.Event()
        self._server: uvicorn.Server | None = None

    @staticmethod
    def _find_free_port() -> int:
        with socket.socket() as sock:
            sock.bind(("", 0))
            return int(sock.getsockname()[1])

    @property
    def url(self) -> str:
        """Base URL of the running server."""
        return f"http://{self.host}:{self.port}"

    def run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        config = uvicorn.Config(self._app, host=self.host, port=self.port, log_level="critical", ws="wsproto")
        self._server = uvicorn.Server(config)

        async def _serve() -> None:
            await self._server.serve()  # type: ignore[union-attr]

        async def _watch_and_notify() -> None:
            while not (self._server and self._server.started):  # noqa: ASYNC110
                await asyncio.sleep(0.02)
            self._started.set()

        async def _main() -> None:
            await asyncio.gather(_serve(), _watch_and_notify())

        try:
            loop.run_until_complete(_main())
        finally:
            loop.close()

    def stop(self) -> None:
        """Signal the server to exit."""
        if self._server is not None:
            self._server.should_exit = True

    def wait_until_ready(self, timeout: float = 10.0) -> bool:
        """Wait until the server TCP listener is accepting connections.

        Args:
            timeout: Maximum seconds to wait.

        Returns:
            True if ready within the timeout, False otherwise.
        """
        if not self._started.wait(timeout):
            return False
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            connected = False
            with contextlib.suppress(OSError), socket.create_connection((self.host, self.port), timeout=0.1):
                connected = True
            if connected:
                return True
            time.sleep(0.05)
        return False
