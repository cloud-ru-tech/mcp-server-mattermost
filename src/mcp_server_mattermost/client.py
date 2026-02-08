"""Async HTTP client for Mattermost API v4."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any, TypeVar

import httpx
from tenacity import RetryCallState, retry, retry_if_exception, stop_after_attempt, wait_exponential

from .config import Settings
from .constants import UPDATE_BOOKMARK_RESPONSE_KEY
from .exceptions import AuthenticationError, MattermostAPIError, NotFoundError, RateLimitError
from .logging import logger, request_id_var


_F = TypeVar("_F", bound=Callable[..., Any])


def _is_retryable_exception(exc: BaseException) -> bool:
    """Check if exception should trigger a retry.

    Args:
        exc: Exception to check

    Returns:
        True if exception is retryable (rate limit or server error)
    """
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, MattermostAPIError):
        # Only retry on server errors (5xx), not client errors (4xx)
        return exc.status_code is not None and exc.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR
    return False


def _log_retry(retry_state: RetryCallState) -> None:
    """Log retry attempts.

    Args:
        retry_state: Current retry state from tenacity
    """
    if retry_state.outcome is not None and retry_state.outcome.failed:
        exc = retry_state.outcome.exception()
        logger.warning(
            "Retry attempt %d failed: %s. Retrying...",
            retry_state.attempt_number,
            exc,
        )


def _wait_for_rate_limit(retry_state: RetryCallState) -> float:
    """Calculate wait time, respecting Retry-After header if present.

    Args:
        retry_state: Current retry state from tenacity

    Returns:
        Seconds to wait before next retry
    """
    exc = retry_state.outcome.exception() if retry_state.outcome else None

    # If rate limited with Retry-After, use that value
    if isinstance(exc, RateLimitError) and exc.retry_after is not None:
        return float(exc.retry_after)

    # Otherwise use exponential backoff: 1s, 2s, 4s, 8s... (max 10s)
    return wait_exponential(multiplier=1, min=1, max=10)(retry_state)


class MattermostClient:
    """Async client for Mattermost REST API v4.

    Usage:
        async with MattermostClient(settings).lifespan() as client:
            channels = await client.get_channels(team_id)
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize client with settings.

        Args:
            settings: Application configuration
        """
        self.settings = settings
        self._client: httpx.AsyncClient | None = None
        self._current_user_id: str | None = None

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator["MattermostClient"]:
        """Context manager for client lifecycle.

        Security note: httpx does not log request headers by default.
        If enabling httpx debug logging (HTTPX_LOG_LEVEL=debug), ensure
        tokens are not exposed. The Authorization header contains a bearer
        token that must remain secret.

        Yields:
            Self with initialized httpx client
        """
        logger.info("Initializing Mattermost API client")
        async with httpx.AsyncClient(
            base_url=f"{self.settings.url}/api/{self.settings.api_version}",
            headers={
                "Authorization": f"Bearer {self.settings.token}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(self.settings.timeout),
            verify=self.settings.verify_ssl,
        ) as client:
            self._client = client
            self._current_user_id = None  # Reset cache on new lifespan
            yield self
            self._client = None
            self._current_user_id = None  # Clear cache on exit
        logger.info("Mattermost API client closed")

    def _make_retrying(self) -> Callable[[_F], _F]:
        """Create tenacity retry decorator with instance settings.

        Returns:
            Configured retry decorator
        """
        return retry(
            stop=stop_after_attempt(self.settings.max_retries + 1),
            wait=_wait_for_rate_limit,
            retry=retry_if_exception(_is_retryable_exception),
            before_sleep=_log_retry,
            reraise=True,
        )

    def _parse_error_response(self, response: httpx.Response) -> tuple[str, str | None]:
        """Parse error message and ID from response.

        Args:
            response: HTTP response from API

        Returns:
            Tuple of (message, error_id)
        """
        error_id = None
        try:
            data = response.json()
            if isinstance(data, dict):
                message = data.get("message", response.text)
                error_id = data.get("id")
                return message, error_id
        except Exception:  # noqa: BLE001 - gracefully handle any JSON parsing failure
            logger.debug("Failed to parse error response as JSON, using raw text")
        return response.text, None

    @staticmethod
    def _parse_retry_after(header: str) -> int | None:
        """Parse Retry-After header value (integer seconds or HTTP-date).

        Args:
            header: Retry-After header value

        Returns:
            Seconds to wait, or None if unparseable
        """
        try:
            return int(header)
        except ValueError:
            logger.debug("Non-integer Retry-After header ignored: %s", header)

        try:
            dt = parsedate_to_datetime(header)
            return max(0, int((dt - datetime.now(timezone.utc)).total_seconds()))
        except (ValueError, TypeError):
            logger.debug("Unparseable Retry-After header ignored: %s", header)

        return None

    def _handle_response(self, response: httpx.Response) -> dict[str, Any] | list[Any] | None:
        """Handle HTTP response and map errors to exceptions.

        Args:
            response: HTTP response from API

        Returns:
            Parsed JSON body or None for empty responses

        Raises:
            AuthenticationError: If authentication failed (401)
            NotFoundError: If resource not found (404)
            RateLimitError: If rate limited (429)
            MattermostAPIError: For other API errors (4xx, 5xx)
        """
        if response.status_code == HTTPStatus.UNAUTHORIZED:
            raise AuthenticationError

        if response.status_code == HTTPStatus.NOT_FOUND:
            message, error_id = self._parse_error_response(response)
            raise NotFoundError(message, error_id=error_id)

        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            retry_after_header = response.headers.get("Retry-After")
            retry_after = self._parse_retry_after(retry_after_header) if retry_after_header else None
            raise RateLimitError(retry_after)

        if response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
            message, error_id = self._parse_error_response(response)
            msg = f"Server error: {message}"
            raise MattermostAPIError(msg, status_code=response.status_code, error_id=error_id)

        if response.status_code >= HTTPStatus.BAD_REQUEST:
            message, error_id = self._parse_error_response(response)
            msg = f"Client error: {message}"
            raise MattermostAPIError(msg, status_code=response.status_code, error_id=error_id)

        if not response.content:
            return None

        result: dict[str, Any] | list[Any] = response.json()
        return result

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,  # noqa: ANN401
    ) -> dict[str, Any] | list[Any] | None:
        """Make HTTP request to Mattermost API with retry.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., "/users/me")
            **kwargs: Additional arguments for httpx request

        Returns:
            Parsed JSON response or None

        Raises:
            RuntimeError: If client not initialized via lifespan
            AuthenticationError: If authentication failed
            NotFoundError: If resource not found
            RateLimitError: If rate limited (after retries exhausted)
            MattermostAPIError: For other API errors
        """
        if self._client is None:
            msg = "Client not initialized. Use async with client.lifespan():"
            raise RuntimeError(msg)

        retrying = self._make_retrying()

        @retrying
        async def _do_request() -> dict[str, Any] | list[Any] | None:
            request_id = request_id_var.get()
            logger.debug(
                "",
                extra={
                    "event": "http_request",
                    "request_id": request_id,
                    "method": method,
                    "endpoint": endpoint,
                },
            )
            response = await self._client.request(method, endpoint, **kwargs)  # type: ignore[union-attr]
            logger.debug(
                "",
                extra={
                    "event": "http_response",
                    "request_id": request_id,
                    "status_code": response.status_code,
                },
            )
            return self._handle_response(response)

        return await _do_request()

    async def get(
        self,
        endpoint: str,
        **kwargs: Any,  # noqa: ANN401 - kwargs forwarded to httpx
    ) -> dict[str, Any] | list[Any] | None:
        """Make GET request.

        Args:
            endpoint: API endpoint
            **kwargs: Additional arguments (params, etc.)

        Returns:
            Parsed JSON response or None
        """
        return await self._request("GET", endpoint, **kwargs)

    async def post(
        self,
        endpoint: str,
        **kwargs: Any,  # noqa: ANN401 - kwargs forwarded to httpx
    ) -> dict[str, Any] | list[Any] | None:
        """Make POST request.

        Args:
            endpoint: API endpoint
            **kwargs: Additional arguments (json, data, etc.)

        Returns:
            Parsed JSON response or None
        """
        return await self._request("POST", endpoint, **kwargs)

    async def put(
        self,
        endpoint: str,
        **kwargs: Any,  # noqa: ANN401 - kwargs forwarded to httpx
    ) -> dict[str, Any] | list[Any] | None:
        """Make PUT request.

        Args:
            endpoint: API endpoint
            **kwargs: Additional arguments (json, data, etc.)

        Returns:
            Parsed JSON response or None
        """
        return await self._request("PUT", endpoint, **kwargs)

    async def delete(
        self,
        endpoint: str,
        **kwargs: Any,  # noqa: ANN401 - kwargs forwarded to httpx
    ) -> dict[str, Any] | list[Any] | None:
        """Make DELETE request.

        Args:
            endpoint: API endpoint
            **kwargs: Additional arguments

        Returns:
            Parsed JSON response or None
        """
        return await self._request("DELETE", endpoint, **kwargs)

    async def patch(
        self,
        endpoint: str,
        **kwargs: Any,  # noqa: ANN401 - kwargs forwarded to httpx
    ) -> dict[str, Any] | list[Any] | None:
        """Make PATCH request for partial updates.

        Args:
            endpoint: API endpoint
            **kwargs: Additional arguments (json, data, etc.)

        Returns:
            Parsed JSON response or None
        """
        return await self._request("PATCH", endpoint, **kwargs)

    # === Teams API ===

    async def get_teams(self) -> list[dict[str, Any]]:
        """Get teams the current user belongs to.

        Returns:
            List of team objects
        """
        result = await self.get("/users/me/teams")
        return result if isinstance(result, list) else []

    async def get_team(self, team_id: str) -> dict[str, Any]:
        """Get team by ID.

        Args:
            team_id: Team identifier

        Returns:
            Team object
        """
        result = await self.get(f"/teams/{team_id}")
        return result if isinstance(result, dict) else {}

    async def get_team_members(
        self,
        team_id: str,
        page: int = 0,
        per_page: int = 60,
    ) -> list[dict[str, Any]]:
        """Get team members with pagination.

        Args:
            team_id: Team identifier
            page: Page number (0-indexed)
            per_page: Results per page (max 200)

        Returns:
            List of team member objects
        """
        result = await self.get(
            f"/teams/{team_id}/members",
            params={"page": page, "per_page": per_page},
        )
        return result if isinstance(result, list) else []

    # === Channels API ===

    async def get_channels(
        self,
        team_id: str,
        page: int = 0,
        per_page: int = 60,
    ) -> list[dict[str, Any]]:
        """Get public channels in a team.

        Args:
            team_id: Team identifier
            page: Page number (0-indexed)
            per_page: Results per page (max 200)

        Returns:
            List of channel objects
        """
        result = await self.get(
            f"/teams/{team_id}/channels",
            params={"page": page, "per_page": per_page},
        )
        return result if isinstance(result, list) else []

    async def get_channel(self, channel_id: str) -> dict[str, Any]:
        """Get channel by ID.

        Args:
            channel_id: Channel identifier

        Returns:
            Channel object
        """
        result = await self.get(f"/channels/{channel_id}")
        return result if isinstance(result, dict) else {}

    async def get_channel_by_name(
        self,
        team_id: str,
        name: str,
    ) -> dict[str, Any]:
        """Get channel by team ID and channel name.

        Args:
            team_id: Team identifier
            name: Channel name

        Returns:
            Channel object
        """
        result = await self.get(f"/teams/{team_id}/channels/name/{name}")
        return result if isinstance(result, dict) else {}

    async def create_channel(  # noqa: PLR0913
        self,
        team_id: str,
        name: str,
        display_name: str,
        channel_type: str = "O",
        purpose: str = "",
        header: str = "",
    ) -> dict[str, Any]:
        """Create a new channel.

        Args:
            team_id: Team identifier
            name: Channel name (lowercase, no spaces)
            display_name: Display name for the channel
            channel_type: O=public, P=private
            purpose: Channel purpose
            header: Channel header

        Returns:
            Created channel object
        """
        result = await self.post(
            "/channels",
            json={
                "team_id": team_id,
                "name": name,
                "display_name": display_name,
                "type": channel_type,
                "purpose": purpose,
                "header": header,
            },
        )
        return result if isinstance(result, dict) else {}

    async def create_direct_channel(
        self,
        user_ids: list[str],
    ) -> dict[str, Any]:
        """Create a direct message channel between two users.

        If a DM channel already exists between the users, returns the existing channel.

        Args:
            user_ids: List of exactly 2 user IDs

        Returns:
            Created or existing channel object (type="D")
        """
        result = await self.post("/channels/direct", json=user_ids)
        return result if isinstance(result, dict) else {}

    async def get_me(self) -> dict[str, Any]:
        """Get current user's profile.

        Returns:
            User object for current user
        """
        result = await self.get("/users/me")
        return result if isinstance(result, dict) else {}

    async def _get_current_user_id(self) -> str:
        """Get current user ID with caching.

        Caches user_id after first call to avoid repeated API requests.

        Returns:
            Current user's ID
        """
        if self._current_user_id is None:
            me = await self.get_me()
            self._current_user_id = me["id"]
        return self._current_user_id

    async def join_channel(self, channel_id: str) -> dict[str, Any]:
        """Join a public channel.

        Args:
            channel_id: Channel identifier

        Returns:
            Channel membership object
        """
        user_id = await self._get_current_user_id()
        result = await self.post(
            f"/channels/{channel_id}/members",
            json={"user_id": user_id},
        )
        return result if isinstance(result, dict) else {}

    async def leave_channel(self, channel_id: str) -> None:
        """Leave a channel.

        Args:
            channel_id: Channel identifier
        """
        user_id = await self._get_current_user_id()
        await self.delete(f"/channels/{channel_id}/members/{user_id}")

    async def get_channel_members(
        self,
        channel_id: str,
        page: int = 0,
        per_page: int = 60,
    ) -> list[dict[str, Any]]:
        """Get channel members with pagination.

        Args:
            channel_id: Channel identifier
            page: Page number (0-indexed)
            per_page: Results per page (max 200)

        Returns:
            List of channel member objects
        """
        result = await self.get(
            f"/channels/{channel_id}/members",
            params={"page": page, "per_page": per_page},
        )
        return result if isinstance(result, list) else []

    async def add_user_to_channel(
        self,
        channel_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Add a user to a channel.

        Args:
            channel_id: Channel identifier
            user_id: User identifier

        Returns:
            Channel membership object
        """
        result = await self.post(
            f"/channels/{channel_id}/members",
            json={"user_id": user_id},
        )
        return result if isinstance(result, dict) else {}

    # === Messages/Posts API ===

    async def get_posts(
        self,
        channel_id: str,
        page: int = 0,
        per_page: int = 60,
    ) -> dict[str, Any]:
        """Get posts in a channel.

        Args:
            channel_id: Channel identifier
            page: Page number (0-indexed)
            per_page: Results per page (max 200)

        Returns:
            Dict with 'posts' (id->post) and 'order' (list of ids)
        """
        result = await self.get(
            f"/channels/{channel_id}/posts",
            params={"page": page, "per_page": per_page},
        )
        return result if isinstance(result, dict) else {}

    async def create_post(
        self,
        channel_id: str,
        message: str,
        root_id: str | None = None,
        file_ids: list[str] | None = None,
        props: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new post/message.

        Args:
            channel_id: Channel identifier
            message: Message content (supports Markdown)
            root_id: Parent post ID for threading
            file_ids: List of file IDs to attach (from upload_file)
            props: Additional properties (attachments, overrides)

        Returns:
            Created post object
        """
        payload: dict[str, Any] = {
            "channel_id": channel_id,
            "message": message,
        }
        if root_id:
            payload["root_id"] = root_id
        if file_ids:
            payload["file_ids"] = file_ids
        if props:
            payload["props"] = props
        result = await self.post("/posts", json=payload)
        return result if isinstance(result, dict) else {}

    async def get_post(self, post_id: str) -> dict[str, Any]:
        """Get post by ID.

        Args:
            post_id: Post identifier

        Returns:
            Post object
        """
        result = await self.get(f"/posts/{post_id}")
        return result if isinstance(result, dict) else {}

    async def update_post(
        self,
        post_id: str,
        message: str,
        props: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update post message.

        Args:
            post_id: Post identifier
            message: New message content
            props: Additional properties (attachments, overrides)

        Returns:
            Updated post object
        """
        payload: dict[str, Any] = {"id": post_id, "message": message}
        if props:
            payload["props"] = props
        result = await self.put(f"/posts/{post_id}", json=payload)
        return result if isinstance(result, dict) else {}

    async def delete_post(self, post_id: str) -> None:
        """Delete a post.

        Args:
            post_id: Post identifier
        """
        await self.delete(f"/posts/{post_id}")

    async def search_posts(
        self,
        team_id: str,
        terms: str,
        is_or_search: bool = False,  # noqa: FBT001, FBT002 - Mattermost API parameter
    ) -> dict[str, Any]:
        """Search posts in a team.

        Args:
            team_id: Team identifier
            terms: Search terms (supports Mattermost search syntax: in:channel, from:user, etc.)
            is_or_search: If True, use OR logic between terms (default: AND logic).
                          Matches Mattermost API parameter name for consistency.

        Returns:
            Dict with 'posts' (id->post mapping) and 'order' (list of post IDs)

        Example:
            # Search with AND (default): posts containing both "bug" AND "fix"
            results = await client.search_posts(team_id, "bug fix")

            # Search with OR: posts containing "bug" OR "fix"
            results = await client.search_posts(team_id, "bug fix", is_or_search=True)
        """
        result = await self.post(
            f"/teams/{team_id}/posts/search",
            json={"terms": terms, "is_or_search": is_or_search},
        )
        return result if isinstance(result, dict) else {}

    async def get_thread(self, post_id: str) -> dict[str, Any]:
        """Get thread/replies for a post.

        Args:
            post_id: Root post identifier

        Returns:
            Dict with 'posts' and 'order'
        """
        result = await self.get(f"/posts/{post_id}/thread")
        return result if isinstance(result, dict) else {}

    # === Reactions API ===

    async def add_reaction(self, post_id: str, emoji_name: str) -> dict[str, Any]:
        """Add emoji reaction to a post.

        Args:
            post_id: Post identifier
            emoji_name: Emoji name without colons (e.g., 'thumbsup')

        Returns:
            Reaction object
        """
        user_id = await self._get_current_user_id()
        result = await self.post(
            "/reactions",
            json={
                "user_id": user_id,
                "post_id": post_id,
                "emoji_name": emoji_name,
            },
        )
        return result if isinstance(result, dict) else {}

    async def remove_reaction(self, post_id: str, emoji_name: str) -> None:
        """Remove emoji reaction from a post.

        Args:
            post_id: Post identifier
            emoji_name: Emoji name without colons
        """
        await self.delete(f"/users/me/posts/{post_id}/reactions/{emoji_name}")

    async def get_reactions(self, post_id: str) -> list[dict[str, Any]]:
        """Get all reactions on a post.

        Args:
            post_id: Post identifier

        Returns:
            List of reaction objects
        """
        result = await self.get(f"/posts/{post_id}/reactions")
        return result if isinstance(result, list) else []

    # === Pins API ===

    async def pin_post(self, post_id: str) -> dict[str, Any]:
        """Pin a post to its channel.

        Args:
            post_id: Post identifier

        Returns:
            Updated post object
        """
        result = await self.post(f"/posts/{post_id}/pin")
        return result if isinstance(result, dict) else {}

    async def unpin_post(self, post_id: str) -> dict[str, Any]:
        """Unpin a post from its channel.

        Args:
            post_id: Post identifier

        Returns:
            Updated post object
        """
        result = await self.post(f"/posts/{post_id}/unpin")
        return result if isinstance(result, dict) else {}

    # === Users API ===

    async def get_user(self, user_id: str) -> dict[str, Any]:
        """Get user by ID.

        Args:
            user_id: User identifier

        Returns:
            User object
        """
        result = await self.get(f"/users/{user_id}")
        return result if isinstance(result, dict) else {}

    async def get_user_by_username(self, username: str) -> dict[str, Any]:
        """Get user by username.

        Args:
            username: Username

        Returns:
            User object
        """
        result = await self.get(f"/users/username/{username}")
        return result if isinstance(result, dict) else {}

    async def search_users(
        self,
        term: str,
        team_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search users by term.

        Args:
            term: Search term (matches username, email, nickname)
            team_id: Optional team to limit search

        Returns:
            List of matching user objects
        """
        payload: dict[str, Any] = {"term": term}
        if team_id:
            payload["team_id"] = team_id
        result = await self.post("/users/search", json=payload)
        return result if isinstance(result, list) else []

    async def get_user_status(self, user_id: str) -> dict[str, Any]:
        """Get user's online status.

        Args:
            user_id: User identifier

        Returns:
            Status object with user_id and status
        """
        result = await self.get(f"/users/{user_id}/status")
        return result if isinstance(result, dict) else {}

    # === Files API ===

    async def upload_file(
        self,
        channel_id: str,
        file_path: str,
        filename: str | None = None,
    ) -> dict[str, Any]:
        """Upload a file to a channel.

        Args:
            channel_id: Channel identifier
            file_path: Path to the file to upload
            filename: Custom filename (defaults to file_path basename)

        Returns:
            Upload response with file_infos list

        Raises:
            FileValidationError: If file path is invalid or file doesn't exist
        """
        from .exceptions import FileValidationError  # noqa: PLC0415

        path = Path(file_path)

        # Resolve to absolute path to prevent TOCTOU race conditions.
        # Normalizes .. and . components.
        try:
            resolved_path = path.resolve(strict=True)
        except (FileNotFoundError, OSError) as e:
            raise FileValidationError(file_path, f"Cannot resolve path: {e}") from e

        # Validate it's not a symlink (check original path before resolution)
        # Note: resolve() follows symlinks, so we check the original path
        if path.is_symlink():
            raise FileValidationError(file_path, "Symbolic links are not allowed")

        # Validate it's a regular file (not directory, device, etc.)
        if not resolved_path.is_file():
            raise FileValidationError(file_path, "Path is not a file")

        name = filename or resolved_path.name
        content = resolved_path.read_bytes()

        return await self._upload_file_with_retry(channel_id, name, content)

    async def _upload_file_with_retry(
        self,
        channel_id: str,
        filename: str,
        content: bytes,
    ) -> dict[str, Any]:
        """Upload file with retry logic.

        Reads file content into memory to avoid stream position issues on retry.

        Args:
            channel_id: Channel identifier
            filename: Name for the uploaded file
            content: File content as bytes

        Returns:
            Upload response with file_infos list
        """
        if self._client is None:
            msg = "Client not initialized. Use async with client.lifespan():"
            raise RuntimeError(msg)

        retrying = self._make_retrying()

        @retrying
        async def _do_upload() -> dict[str, Any] | list[Any] | None:
            request_id = request_id_var.get()
            logger.debug(
                "",
                extra={
                    "event": "http_request",
                    "request_id": request_id,
                    "method": "POST",
                    "endpoint": "/files",
                },
            )
            response = await self._client.post(  # type: ignore[union-attr]
                "/files",
                params={"channel_id": channel_id, "filename": filename},
                data={"channel_id": channel_id},
                files={"files": (filename, content)},
            )
            logger.debug(
                "",
                extra={
                    "event": "http_response",
                    "request_id": request_id,
                    "status_code": response.status_code,
                },
            )
            return self._handle_response(response)

        result = await _do_upload()
        return result if isinstance(result, dict) else {}

    async def get_file_info(self, file_id: str) -> dict[str, Any]:
        """Get file metadata.

        Args:
            file_id: File identifier

        Returns:
            File info object
        """
        result = await self.get(f"/files/{file_id}/info")
        return result if isinstance(result, dict) else {}

    async def get_file_link(self, file_id: str) -> dict[str, Any]:
        """Get public download link for a file.

        Args:
            file_id: File identifier

        Returns:
            Object with 'link' field
        """
        result = await self.get(f"/files/{file_id}/link")
        return result if isinstance(result, dict) else {}

    # === Bookmarks API ===

    async def get_bookmarks(
        self,
        channel_id: str,
        bookmarks_since: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get all bookmarks for a channel.

        Args:
            channel_id: Channel identifier
            bookmarks_since: Optional timestamp to filter bookmarks

        Returns:
            List of bookmark objects
        """
        params: dict[str, Any] = {}
        if bookmarks_since is not None:
            params["bookmarks_since"] = bookmarks_since
        result = await self.get(f"/channels/{channel_id}/bookmarks", params=params or None)
        return result if isinstance(result, list) else []

    async def create_bookmark(  # noqa: PLR0913
        self,
        channel_id: str,
        display_name: str,
        bookmark_type: str,
        link_url: str | None = None,
        file_id: str | None = None,
        emoji: str | None = None,
        image_url: str | None = None,
    ) -> dict[str, Any]:
        """Create a channel bookmark.

        Args:
            channel_id: Channel identifier
            display_name: Bookmark display name
            bookmark_type: Type: "link" or "file"
            link_url: URL for link bookmarks
            file_id: File ID for file bookmarks
            emoji: Optional emoji icon
            image_url: Optional preview image URL

        Returns:
            Created bookmark object
        """
        payload: dict[str, Any] = {"display_name": display_name, "type": bookmark_type}
        if link_url:
            payload["link_url"] = link_url
        if file_id:
            payload["file_id"] = file_id
        if emoji:
            payload["emoji"] = emoji
        if image_url:
            payload["image_url"] = image_url
        result = await self.post(f"/channels/{channel_id}/bookmarks", json=payload)
        return result if isinstance(result, dict) else {}

    async def update_bookmark(
        self,
        channel_id: str,
        bookmark_id: str,
        **fields: Any,  # noqa: ANN401 - kwargs for partial update
    ) -> dict[str, Any]:
        """Partially update a bookmark.

        Args:
            channel_id: Channel identifier
            bookmark_id: Bookmark identifier
            **fields: Fields to update (display_name, link_url, etc.)

        Returns:
            Updated bookmark object
        """
        result = await self.patch(f"/channels/{channel_id}/bookmarks/{bookmark_id}", json=fields)
        if isinstance(result, dict):
            # Mattermost API returns UpdateChannelBookmarkResponse with bookmark in "updated" field
            updated = result.get(UPDATE_BOOKMARK_RESPONSE_KEY)
            if isinstance(updated, dict):
                return updated
            return result
        return {}

    async def delete_bookmark(
        self,
        channel_id: str,
        bookmark_id: str,
    ) -> dict[str, Any]:
        """Archive a bookmark (soft delete).

        Args:
            channel_id: Channel identifier
            bookmark_id: Bookmark identifier

        Returns:
            Deleted bookmark object with delete_at set
        """
        result = await self.delete(f"/channels/{channel_id}/bookmarks/{bookmark_id}")
        return result if isinstance(result, dict) else {}

    async def update_bookmark_sort_order(
        self,
        channel_id: str,
        bookmark_id: str,
        new_sort_order: int,
    ) -> list[dict[str, Any]]:
        """Update bookmark position.

        Args:
            channel_id: Channel identifier
            bookmark_id: Bookmark identifier
            new_sort_order: New position in list

        Returns:
            List of affected bookmark objects
        """
        result = await self.post(
            f"/channels/{channel_id}/bookmarks/{bookmark_id}/sort_order",
            json=new_sort_order,
        )
        return result if isinstance(result, list) else []
