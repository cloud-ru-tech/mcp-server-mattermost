"""Tests for MattermostClient."""

import logging

import httpx
import pytest
import respx

from mcp_server_mattermost.client import MattermostClient
from mcp_server_mattermost.config import Settings


class TestTokenRedaction:
    @pytest.fixture
    def settings_with_token(self, monkeypatch):
        monkeypatch.setenv("MATTERMOST_URL", "https://mattermost.example.com")
        monkeypatch.setenv("MATTERMOST_TOKEN", "secret-token-12345")
        return Settings()

    def test_token_not_in_debug_logs(self, settings_with_token, caplog):
        caplog.set_level(logging.DEBUG)

        _ = MattermostClient(settings_with_token)

        log_text = caplog.text
        assert "secret-token-12345" not in log_text
        assert "Bearer secret-token-12345" not in log_text

    @pytest.mark.asyncio
    @respx.mock
    async def test_token_not_in_request_logs(self, settings_with_token, caplog):
        respx.get("https://mattermost.example.com/api/v4/users/me").mock(
            return_value=httpx.Response(200, json={"id": "user123", "username": "test"}),
        )

        caplog.set_level(logging.DEBUG)

        client = MattermostClient(settings_with_token)
        async with client.lifespan():
            await client.get_me()

        log_text = caplog.text
        assert "secret-token-12345" not in log_text
        assert "Bearer secret-token-12345" not in log_text


class TestMattermostClientInit:
    def test_client_stores_settings(self, mock_settings):
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        assert client.settings is settings
        assert client._client is None

    @pytest.mark.asyncio
    async def test_request_without_lifespan_raises_runtime_error(self, mock_settings):
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        with pytest.raises(RuntimeError, match="Client not initialized"):
            await client._request("GET", "/users/me")


class TestMattermostClientLifespan:
    @pytest.mark.asyncio
    async def test_lifespan_creates_client(self, mock_settings):
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        assert client._client is None

        async with client.lifespan() as ctx:
            assert ctx is client
            assert client._client is not None
            assert isinstance(client._client, httpx.AsyncClient)

        assert client._client is None

    @pytest.mark.asyncio
    async def test_lifespan_configures_base_url(self, mock_settings):
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        async with client.lifespan():
            assert str(client._client.base_url).rstrip("/") == "https://test.mattermost.com/api/v4"

    @pytest.mark.asyncio
    async def test_lifespan_sets_auth_header(self, mock_settings):
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        async with client.lifespan():
            assert "Authorization" in client._client.headers
            assert client._client.headers["Authorization"] == "Bearer test-token-12345"


class TestMattermostClientResponseHandler:
    """Test response handling and error mapping."""

    def test_handle_response_success_with_json(self, mock_settings):
        """Successful response with JSON body should return parsed data."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        response = httpx.Response(200, json={"id": "abc123", "name": "test"})
        result = client._handle_response(response)

        assert result == {"id": "abc123", "name": "test"}

    def test_handle_response_success_empty_body(self, mock_settings):
        """Successful response with empty body should return None."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        response = httpx.Response(204, content=b"")
        result = client._handle_response(response)

        assert result is None

    def test_handle_response_401_raises_authentication_error(self, mock_settings):
        """401 response should raise AuthenticationError."""
        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.exceptions import AuthenticationError

        settings = get_settings()
        client = MattermostClient(settings)

        response = httpx.Response(401, json={"message": "Invalid token"})

        with pytest.raises(AuthenticationError):
            client._handle_response(response)

    def test_handle_response_404_raises_not_found_error(self, mock_settings):
        """404 response should raise NotFoundError."""
        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.exceptions import NotFoundError

        settings = get_settings()
        client = MattermostClient(settings)

        response = httpx.Response(404, json={"message": "Channel not found"})

        with pytest.raises(NotFoundError):
            client._handle_response(response)

    def test_handle_response_429_raises_rate_limit_error(self, mock_settings):
        """429 response should raise RateLimitError with retry_after."""
        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.exceptions import RateLimitError

        settings = get_settings()
        client = MattermostClient(settings)

        response = httpx.Response(
            429,
            headers={"Retry-After": "30"},
            json={"message": "Rate limit exceeded"},
        )

        with pytest.raises(RateLimitError) as exc_info:
            client._handle_response(response)

        assert exc_info.value.retry_after == 30

    def test_handle_response_429_http_date_retry_after(self, mock_settings):
        """429 with HTTP-date Retry-After should parse date into seconds."""
        from datetime import datetime, timezone

        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.exceptions import RateLimitError

        settings = get_settings()
        client = MattermostClient(settings)

        # Use a date far in the future so we get a positive retry_after
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        http_date = future.strftime("%a, %d %b %Y %H:%M:%S GMT")

        response = httpx.Response(
            429,
            headers={"Retry-After": http_date},
            json={"message": "Rate limit exceeded"},
        )

        with pytest.raises(RateLimitError) as exc_info:
            client._handle_response(response)

        assert exc_info.value.retry_after is not None
        assert exc_info.value.retry_after > 0

    def test_handle_response_429_http_date_in_past(self, mock_settings):
        """429 with HTTP-date in the past should clamp retry_after to 0."""
        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.exceptions import RateLimitError

        settings = get_settings()
        client = MattermostClient(settings)

        response = httpx.Response(
            429,
            headers={"Retry-After": "Mon, 01 Jan 2001 00:00:00 GMT"},
            json={"message": "Rate limit exceeded"},
        )

        with pytest.raises(RateLimitError) as exc_info:
            client._handle_response(response)

        assert exc_info.value.retry_after == 0

    def test_handle_response_429_invalid_retry_after(self, mock_settings):
        """429 with unparseable Retry-After should fall back to retry_after=None."""
        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.exceptions import RateLimitError

        settings = get_settings()
        client = MattermostClient(settings)

        response = httpx.Response(
            429,
            headers={"Retry-After": "not-a-date-or-number"},
            json={"message": "Rate limit exceeded"},
        )

        with pytest.raises(RateLimitError) as exc_info:
            client._handle_response(response)

        assert exc_info.value.retry_after is None

    def test_handle_response_429_no_retry_after_header(self, mock_settings):
        """429 without Retry-After header should raise RateLimitError with retry_after=None."""
        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.exceptions import RateLimitError

        settings = get_settings()
        client = MattermostClient(settings)

        response = httpx.Response(
            429,
            json={"message": "Rate limit exceeded"},
        )

        with pytest.raises(RateLimitError) as exc_info:
            client._handle_response(response)

        assert exc_info.value.retry_after is None

    def test_handle_response_500_raises_api_error(self, mock_settings):
        """5xx response should raise MattermostAPIError."""
        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.exceptions import MattermostAPIError

        settings = get_settings()
        client = MattermostClient(settings)

        response = httpx.Response(500, json={"message": "Internal error"})

        with pytest.raises(MattermostAPIError) as exc_info:
            client._handle_response(response)

        assert exc_info.value.status_code == 500


class TestErrorParsing:
    """Test structured error response parsing."""

    def test_parses_json_error_message(self, mock_settings):
        """Verify JSON error response is parsed for message."""
        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.exceptions import MattermostAPIError

        settings = get_settings()
        client = MattermostClient(settings)

        response = httpx.Response(
            400,
            json={
                "id": "api.user.get.error",
                "message": "User not found in database",
                "status_code": 400,
            },
        )

        with pytest.raises(MattermostAPIError) as exc_info:
            client._handle_response(response)

        assert "User not found in database" in str(exc_info.value)
        assert exc_info.value.error_id == "api.user.get.error"

    def test_handles_plain_text_error(self, mock_settings):
        """Verify plain text error is handled gracefully."""
        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.exceptions import MattermostAPIError

        settings = get_settings()
        client = MattermostClient(settings)

        response = httpx.Response(500, text="Internal Server Error")

        with pytest.raises(MattermostAPIError) as exc_info:
            client._handle_response(response)

        assert "Internal Server Error" in str(exc_info.value)

    def test_parses_server_error_json(self, mock_settings):
        """Verify 5xx JSON error response is parsed."""
        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.exceptions import MattermostAPIError

        settings = get_settings()
        client = MattermostClient(settings)

        response = httpx.Response(
            503,
            json={
                "id": "api.service.unavailable",
                "message": "Service temporarily unavailable",
            },
        )

        with pytest.raises(MattermostAPIError) as exc_info:
            client._handle_response(response)

        assert "Service temporarily unavailable" in str(exc_info.value)
        assert exc_info.value.error_id == "api.service.unavailable"


class TestMattermostClientRequest:
    """Test _request method with retry logic."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_request_get_success(self, mock_settings):
        """GET request should return parsed JSON."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/users/me").mock(
            return_value=httpx.Response(200, json={"id": "user123", "username": "test"}),
        )

        async with client.lifespan():
            result = await client._request("GET", "/users/me")

        assert result == {"id": "user123", "username": "test"}

    @pytest.mark.asyncio
    @respx.mock
    async def test_request_post_with_json_body(self, mock_settings):
        """POST request should send JSON body."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        route = respx.post("https://test.mattermost.com/api/v4/posts").mock(
            return_value=httpx.Response(201, json={"id": "post123"}),
        )

        async with client.lifespan():
            result = await client._request("POST", "/posts", json={"channel_id": "ch123", "message": "Hello"})

        assert result == {"id": "post123"}
        assert route.call_count == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_request_logs_debug(self, mock_settings, mocker):
        """Request should log at DEBUG level."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/users/me").mock(
            return_value=httpx.Response(200, json={"id": "user123"}),
        )

        mock_debug = mocker.patch("mcp_server_mattermost.client.logger.debug")

        async with client.lifespan():
            await client._request("GET", "/users/me")

        calls = [str(call) for call in mock_debug.call_args_list]
        assert any("GET" in call and "/users/me" in call for call in calls)


class TestMattermostClientRetry:
    """Test retry behavior with tenacity."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_retries_on_rate_limit(self, mock_settings):
        """Should retry on 429 with exponential backoff."""
        settings = Settings(
            url="https://test.mattermost.com",
            token="test-token-12345",
            max_retries=2,
        )
        client = MattermostClient(settings)

        route = respx.get("https://test.mattermost.com/api/v4/users/me").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "1"}),
                httpx.Response(200, json={"id": "user123"}),
            ],
        )

        async with client.lifespan():
            result = await client._request("GET", "/users/me")

        assert result == {"id": "user123"}
        assert route.call_count == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_retries_on_server_error(self, mock_settings):
        """Should retry on 5xx errors."""
        settings = Settings(
            url="https://test.mattermost.com",
            token="test-token-12345",
            max_retries=2,
        )
        client = MattermostClient(settings)

        route = respx.get("https://test.mattermost.com/api/v4/users/me").mock(
            side_effect=[
                httpx.Response(503),
                httpx.Response(200, json={"id": "user123"}),
            ],
        )

        async with client.lifespan():
            result = await client._request("GET", "/users/me")

        assert result == {"id": "user123"}
        assert route.call_count == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_no_retry_on_auth_error(self, mock_settings):
        """Should not retry on 401."""
        from mcp_server_mattermost.exceptions import AuthenticationError

        settings = Settings(
            url="https://test.mattermost.com",
            token="test-token-12345",
            max_retries=3,
        )
        client = MattermostClient(settings)

        route = respx.get("https://test.mattermost.com/api/v4/users/me").mock(return_value=httpx.Response(401))

        async with client.lifespan():
            with pytest.raises(AuthenticationError):
                await client._request("GET", "/users/me")

        assert route.call_count == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_no_retry_on_not_found(self, mock_settings):
        """Should not retry on 404."""
        from mcp_server_mattermost.exceptions import NotFoundError

        settings = Settings(
            url="https://test.mattermost.com",
            token="test-token-12345",
            max_retries=3,
        )
        client = MattermostClient(settings)

        route = respx.get("https://test.mattermost.com/api/v4/channels/abc").mock(return_value=httpx.Response(404))

        async with client.lifespan():
            with pytest.raises(NotFoundError):
                await client._request("GET", "/channels/abc")

        assert route.call_count == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_gives_up_after_max_retries(self, mock_settings):
        """Should give up after max_retries attempts."""
        from mcp_server_mattermost.exceptions import MattermostAPIError

        settings = Settings(
            url="https://test.mattermost.com",
            token="test-token-12345",
            max_retries=2,
        )
        client = MattermostClient(settings)

        route = respx.get("https://test.mattermost.com/api/v4/users/me").mock(return_value=httpx.Response(503))

        async with client.lifespan():
            with pytest.raises(MattermostAPIError):
                await client._request("GET", "/users/me")

        assert route.call_count == 3

    @pytest.mark.asyncio
    @respx.mock
    async def test_retry_respects_retry_after_header(self, mock_settings):
        """Verify retry waits for Retry-After seconds."""
        import time

        call_times: list[float] = []

        def track_request(request):
            call_times.append(time.monotonic())
            if len(call_times) == 1:
                return httpx.Response(429, headers={"Retry-After": "2"})
            return httpx.Response(200, json={"id": "user123", "username": "test"})

        settings = Settings(
            url="https://test.mattermost.com",
            token="test-token-12345",
            max_retries=2,
        )
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/users/me").mock(side_effect=track_request)

        async with client.lifespan():
            result = await client.get_me()

        assert result["id"] == "user123"
        assert len(call_times) == 2
        wait_time = call_times[1] - call_times[0]
        assert wait_time >= 2.0, f"Expected wait >= 2s, got {wait_time}s"


class TestMattermostClientConvenienceMethods:
    """Test get, post, put, delete convenience methods."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_method(self, mock_settings):
        """get() should make GET request."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/users/me").mock(
            return_value=httpx.Response(200, json={"id": "user123"}),
        )

        async with client.lifespan():
            result = await client.get("/users/me")

        assert result == {"id": "user123"}

    @pytest.mark.asyncio
    @respx.mock
    async def test_post_method(self, mock_settings):
        """post() should make POST request with JSON body."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.post("https://test.mattermost.com/api/v4/posts").mock(
            return_value=httpx.Response(201, json={"id": "post123"}),
        )

        async with client.lifespan():
            result = await client.post("/posts", json={"message": "Hello"})

        assert result == {"id": "post123"}

    @pytest.mark.asyncio
    @respx.mock
    async def test_put_method(self, mock_settings):
        """put() should make PUT request."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.put("https://test.mattermost.com/api/v4/posts/123").mock(
            return_value=httpx.Response(200, json={"id": "post123"}),
        )

        async with client.lifespan():
            result = await client.put("/posts/123", json={"message": "Updated"})

        assert result == {"id": "post123"}

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_method(self, mock_settings):
        """delete() should make DELETE request."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.delete("https://test.mattermost.com/api/v4/posts/123").mock(return_value=httpx.Response(204))

        async with client.lifespan():
            result = await client.delete("/posts/123")

        assert result is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_with_params(self, mock_settings):
        """get() should pass query parameters."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        route = respx.get("https://test.mattermost.com/api/v4/channels").mock(return_value=httpx.Response(200, json=[]))

        async with client.lifespan():
            await client.get("/channels", params={"page": 0, "per_page": 60})

        assert route.calls[0].request.url.params["page"] == "0"
        assert route.calls[0].request.url.params["per_page"] == "60"


class TestMattermostClientTeamsAPI:
    """Test Teams API methods."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_teams(self, mock_settings):
        """get_teams() should return user's teams."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/users/me/teams").mock(
            return_value=httpx.Response(200, json=[{"id": "team123", "name": "my-team"}]),
        )

        async with client.lifespan():
            result = await client.get_teams()

        assert result == [{"id": "team123", "name": "my-team"}]

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_team(self, mock_settings):
        """get_team() should return team by ID."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/teams/team123").mock(
            return_value=httpx.Response(200, json={"id": "team123", "name": "my-team"}),
        )

        async with client.lifespan():
            result = await client.get_team("team123")

        assert result == {"id": "team123", "name": "my-team"}

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_team_members(self, mock_settings):
        """get_team_members() should return paginated members."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        route = respx.get("https://test.mattermost.com/api/v4/teams/team123/members").mock(
            return_value=httpx.Response(200, json=[{"user_id": "user123", "team_id": "team123"}]),
        )

        async with client.lifespan():
            result = await client.get_team_members("team123", page=1, per_page=30)

        assert result == [{"user_id": "user123", "team_id": "team123"}]
        assert route.calls[0].request.url.params["page"] == "1"
        assert route.calls[0].request.url.params["per_page"] == "30"


class TestMattermostClientChannelsAPI:
    """Test Channels API methods."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_channels(self, mock_settings):
        """get_channels() should return team's channels."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        route = respx.get("https://test.mattermost.com/api/v4/teams/team123/channels").mock(
            return_value=httpx.Response(200, json=[{"id": "ch123", "name": "general"}]),
        )

        async with client.lifespan():
            result = await client.get_channels("team123", page=0, per_page=60)

        assert result == [{"id": "ch123", "name": "general"}]
        assert route.calls[0].request.url.params["page"] == "0"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_channel(self, mock_settings):
        """get_channel() should return channel by ID."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/channels/ch123").mock(
            return_value=httpx.Response(200, json={"id": "ch123", "name": "general"}),
        )

        async with client.lifespan():
            result = await client.get_channel("ch123")

        assert result == {"id": "ch123", "name": "general"}

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_channel_by_name(self, mock_settings):
        """get_channel_by_name() should return channel by team and name."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/teams/team123/channels/name/general").mock(
            return_value=httpx.Response(200, json={"id": "ch123", "name": "general"}),
        )

        async with client.lifespan():
            result = await client.get_channel_by_name("team123", "general")

        assert result == {"id": "ch123", "name": "general"}

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_channel(self, mock_settings):
        """create_channel() should create new channel."""
        import json

        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        route = respx.post("https://test.mattermost.com/api/v4/channels").mock(
            return_value=httpx.Response(201, json={"id": "ch123", "name": "new-channel"}),
        )

        async with client.lifespan():
            result = await client.create_channel(
                team_id="team123",
                name="new-channel",
                display_name="New Channel",
                channel_type="O",
                purpose="Test channel",
                header="Welcome!",
            )

        assert result == {"id": "ch123", "name": "new-channel"}
        request_json = route.calls[0].request.content
        body = json.loads(request_json)
        assert body["team_id"] == "team123"
        assert body["name"] == "new-channel"
        assert body["type"] == "O"

    @pytest.mark.asyncio
    @respx.mock
    async def test_join_channel(self, mock_settings):
        """join_channel() should add current user to channel."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/users/me").mock(
            return_value=httpx.Response(200, json={"id": "user123"}),
        )
        respx.post("https://test.mattermost.com/api/v4/channels/ch123/members").mock(
            return_value=httpx.Response(201, json={"channel_id": "ch123", "user_id": "user123"}),
        )

        async with client.lifespan():
            result = await client.join_channel("ch123")

        assert result == {"channel_id": "ch123", "user_id": "user123"}

    @pytest.mark.asyncio
    @respx.mock
    async def test_leave_channel(self, mock_settings):
        """leave_channel() should remove current user from channel."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/users/me").mock(
            return_value=httpx.Response(200, json={"id": "user123"}),
        )
        respx.delete("https://test.mattermost.com/api/v4/channels/ch123/members/user123").mock(
            return_value=httpx.Response(204),
        )

        async with client.lifespan():
            result = await client.leave_channel("ch123")

        assert result is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_channel_members(self, mock_settings):
        """get_channel_members() should return paginated members."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/channels/ch123/members").mock(
            return_value=httpx.Response(200, json=[{"user_id": "user123"}]),
        )

        async with client.lifespan():
            result = await client.get_channel_members("ch123")

        assert result == [{"user_id": "user123"}]

    @pytest.mark.asyncio
    @respx.mock
    async def test_add_user_to_channel(self, mock_settings):
        """add_user_to_channel() should add specified user to channel."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.post("https://test.mattermost.com/api/v4/channels/ch123/members").mock(
            return_value=httpx.Response(201, json={"channel_id": "ch123", "user_id": "user456"}),
        )

        async with client.lifespan():
            result = await client.add_user_to_channel("ch123", "user456")

        assert result == {"channel_id": "ch123", "user_id": "user456"}


class TestMattermostClientMessagesAPI:
    """Test Messages/Posts API methods."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_posts(self, mock_settings):
        """get_posts() should return channel posts."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/channels/ch123/posts").mock(
            return_value=httpx.Response(
                200,
                json={"posts": {"post1": {"id": "post1", "message": "Hello"}}, "order": ["post1"]},
            ),
        )

        async with client.lifespan():
            result = await client.get_posts("ch123", page=0, per_page=60)

        assert "posts" in result
        assert "post1" in result["posts"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_post(self, mock_settings):
        """create_post() should create a new post."""
        import json

        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        route = respx.post("https://test.mattermost.com/api/v4/posts").mock(
            return_value=httpx.Response(201, json={"id": "post123", "message": "Hello"}),
        )

        async with client.lifespan():
            result = await client.create_post("ch123", "Hello")

        assert result == {"id": "post123", "message": "Hello"}
        body = json.loads(route.calls[0].request.content)
        assert body["channel_id"] == "ch123"
        assert body["message"] == "Hello"

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_post_with_root_id(self, mock_settings):
        """create_post() with root_id should create a threaded reply."""
        import json

        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        route = respx.post("https://test.mattermost.com/api/v4/posts").mock(
            return_value=httpx.Response(201, json={"id": "post124", "root_id": "post123"}),
        )

        async with client.lifespan():
            result = await client.create_post("ch123", "Reply", root_id="post123")

        assert result["root_id"] == "post123"
        body = json.loads(route.calls[0].request.content)
        assert body["root_id"] == "post123"

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_post(self, mock_settings):
        """get_post() should return post by ID."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/posts/post123").mock(
            return_value=httpx.Response(200, json={"id": "post123", "message": "Hello"}),
        )

        async with client.lifespan():
            result = await client.get_post("post123")

        assert result == {"id": "post123", "message": "Hello"}

    @pytest.mark.asyncio
    @respx.mock
    async def test_update_post(self, mock_settings):
        """update_post() should update post message."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.put("https://test.mattermost.com/api/v4/posts/post123").mock(
            return_value=httpx.Response(200, json={"id": "post123", "message": "Updated"}),
        )

        async with client.lifespan():
            result = await client.update_post("post123", "Updated")

        assert result["message"] == "Updated"

    @pytest.mark.asyncio
    @respx.mock
    async def test_update_post_includes_id_in_body(self, mock_settings):
        """update_post() should include post id in request body."""
        import json

        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        route = respx.put("https://test.mattermost.com/api/v4/posts/post123").mock(
            return_value=httpx.Response(200, json={"id": "post123", "message": "Updated"}),
        )

        async with client.lifespan():
            await client.update_post("post123", "Updated")

        body = json.loads(route.calls[0].request.content)
        assert body["id"] == "post123"
        assert body["message"] == "Updated"

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_post(self, mock_settings):
        """delete_post() should delete a post."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.delete("https://test.mattermost.com/api/v4/posts/post123").mock(return_value=httpx.Response(204))

        async with client.lifespan():
            result = await client.delete_post("post123")

        assert result is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_posts(self, mock_settings):
        """search_posts() should search posts in team."""
        import json

        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        route = respx.post("https://test.mattermost.com/api/v4/teams/team123/posts/search").mock(
            return_value=httpx.Response(200, json={"posts": {}, "order": []}),
        )

        async with client.lifespan():
            result = await client.search_posts("team123", "hello world", is_or_search=False)

        assert "posts" in result
        body = json.loads(route.calls[0].request.content)
        assert body["terms"] == "hello world"
        assert body["is_or_search"] is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_thread(self, mock_settings):
        """get_thread() should return thread posts."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/posts/post123/thread").mock(
            return_value=httpx.Response(200, json={"posts": {}, "order": []}),
        )

        async with client.lifespan():
            result = await client.get_thread("post123")

        assert "posts" in result


class TestMattermostClientReactionsAPI:
    """Test Reactions and Pins API methods."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_add_reaction(self, mock_settings):
        """add_reaction() should add emoji reaction to post."""
        import json

        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/users/me").mock(
            return_value=httpx.Response(200, json={"id": "user123"}),
        )
        route = respx.post("https://test.mattermost.com/api/v4/reactions").mock(
            return_value=httpx.Response(201, json={"user_id": "user123", "emoji_name": "thumbsup"}),
        )

        async with client.lifespan():
            result = await client.add_reaction("post123", "thumbsup")

        assert result["emoji_name"] == "thumbsup"
        body = json.loads(route.calls[0].request.content)
        assert body["post_id"] == "post123"
        assert body["emoji_name"] == "thumbsup"

    @pytest.mark.asyncio
    @respx.mock
    async def test_remove_reaction(self, mock_settings):
        """remove_reaction() should remove reaction from post."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/users/me").mock(
            return_value=httpx.Response(200, json={"id": "user123"}),
        )
        respx.delete("https://test.mattermost.com/api/v4/users/me/posts/post123/reactions/thumbsup").mock(
            return_value=httpx.Response(204),
        )

        async with client.lifespan():
            result = await client.remove_reaction("post123", "thumbsup")

        assert result is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_reactions(self, mock_settings):
        """get_reactions() should return all reactions on post."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/posts/post123/reactions").mock(
            return_value=httpx.Response(200, json=[{"user_id": "user123", "emoji_name": "thumbsup"}]),
        )

        async with client.lifespan():
            result = await client.get_reactions("post123")

        assert result == [{"user_id": "user123", "emoji_name": "thumbsup"}]

    @pytest.mark.asyncio
    @respx.mock
    async def test_pin_post(self, mock_settings):
        """pin_post() should pin a post."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.post("https://test.mattermost.com/api/v4/posts/post123/pin").mock(
            return_value=httpx.Response(200, json={"id": "post123", "is_pinned": True}),
        )

        async with client.lifespan():
            result = await client.pin_post("post123")

        assert result["is_pinned"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_unpin_post(self, mock_settings):
        """unpin_post() should unpin a post."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.post("https://test.mattermost.com/api/v4/posts/post123/unpin").mock(
            return_value=httpx.Response(200, json={"id": "post123", "is_pinned": False}),
        )

        async with client.lifespan():
            result = await client.unpin_post("post123")

        assert result["is_pinned"] is False


class TestMattermostClientUsersAPI:
    """Test Users API methods."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_me(self, mock_settings):
        """get_me() should return current user."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/users/me").mock(
            return_value=httpx.Response(200, json={"id": "user123", "username": "testuser"}),
        )

        async with client.lifespan():
            result = await client.get_me()

        assert result == {"id": "user123", "username": "testuser"}

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_user(self, mock_settings):
        """get_user() should return user by ID."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/users/user123").mock(
            return_value=httpx.Response(200, json={"id": "user123", "username": "testuser"}),
        )

        async with client.lifespan():
            result = await client.get_user("user123")

        assert result == {"id": "user123", "username": "testuser"}

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_user_by_username(self, mock_settings):
        """get_user_by_username() should return user by username."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/users/username/testuser").mock(
            return_value=httpx.Response(200, json={"id": "user123", "username": "testuser"}),
        )

        async with client.lifespan():
            result = await client.get_user_by_username("testuser")

        assert result == {"id": "user123", "username": "testuser"}

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_users(self, mock_settings):
        """search_users() should search users by term."""
        import json

        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        route = respx.post("https://test.mattermost.com/api/v4/users/search").mock(
            return_value=httpx.Response(200, json=[{"id": "user123", "username": "testuser"}]),
        )

        async with client.lifespan():
            result = await client.search_users("test", team_id="team123")

        assert result == [{"id": "user123", "username": "testuser"}]
        body = json.loads(route.calls[0].request.content)
        assert body["term"] == "test"
        assert body["team_id"] == "team123"

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_users_without_team(self, mock_settings):
        """search_users() without team_id should omit it from request."""
        import json

        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        route = respx.post("https://test.mattermost.com/api/v4/users/search").mock(
            return_value=httpx.Response(200, json=[]),
        )

        async with client.lifespan():
            await client.search_users("test")

        body = json.loads(route.calls[0].request.content)
        assert "team_id" not in body

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_user_status(self, mock_settings):
        """get_user_status() should return user's online status."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/users/user123/status").mock(
            return_value=httpx.Response(200, json={"user_id": "user123", "status": "online"}),
        )

        async with client.lifespan():
            result = await client.get_user_status("user123")

        assert result == {"user_id": "user123", "status": "online"}


class TestMattermostClientFilesAPI:
    """Test Files API methods."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_upload_file(self, mock_settings):
        """upload_file() should upload a file to channel."""
        import tempfile
        from pathlib import Path

        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.post("https://test.mattermost.com/api/v4/files").mock(
            return_value=httpx.Response(201, json={"file_infos": [{"id": "file123", "name": "test.txt"}]}),
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test content")
            temp_path = f.name

        try:
            async with client.lifespan():
                result = await client.upload_file("ch123", temp_path)

            assert result["file_infos"][0]["id"] == "file123"
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    @respx.mock
    async def test_upload_file_with_custom_filename(self, mock_settings):
        """upload_file() should use custom filename if provided."""
        import tempfile
        from pathlib import Path

        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.post("https://test.mattermost.com/api/v4/files").mock(
            return_value=httpx.Response(201, json={"file_infos": [{"id": "file123", "name": "custom.txt"}]}),
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test content")
            temp_path = f.name

        try:
            async with client.lifespan():
                result = await client.upload_file("ch123", temp_path, filename="custom.txt")

            assert result["file_infos"][0]["name"] == "custom.txt"
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    @respx.mock
    async def test_upload_file_passes_channel_id_and_filename_as_query_params(self, mock_settings):
        """upload_file() should pass channel_id and filename as query parameters."""
        import tempfile
        from pathlib import Path

        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        route = respx.post("https://test.mattermost.com/api/v4/files").mock(
            return_value=httpx.Response(201, json={"file_infos": [{"id": "file123"}]}),
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test content")
            temp_path = f.name

        try:
            async with client.lifespan():
                await client.upload_file("ch123", temp_path)

            # Verify channel_id and filename are in query params
            params = route.calls[0].request.url.params
            assert params["channel_id"] == "ch123"
            assert params["filename"] == Path(temp_path).name
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_file_info(self, mock_settings):
        """get_file_info() should return file metadata."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/files/file123/info").mock(
            return_value=httpx.Response(200, json={"id": "file123", "name": "test.txt", "size": 100}),
        )

        async with client.lifespan():
            result = await client.get_file_info("file123")

        assert result == {"id": "file123", "name": "test.txt", "size": 100}

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_file_link(self, mock_settings):
        """get_file_link() should return download link."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/files/file123/link").mock(
            return_value=httpx.Response(200, json={"link": "https://server.com/files/file123/download"}),
        )

        async with client.lifespan():
            result = await client.get_file_link("file123")

        assert "link" in result

    @pytest.mark.asyncio
    async def test_upload_file_not_found_raises_error(self, mock_settings):
        """upload_file() should raise FileValidationError for non-existent file."""
        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.exceptions import FileValidationError

        settings = get_settings()
        client = MattermostClient(settings)

        async with client.lifespan():
            with pytest.raises(FileValidationError) as exc_info:
                await client.upload_file("ch123", "/nonexistent/path/file.txt")

            assert exc_info.value.file_path == "/nonexistent/path/file.txt"
            assert "cannot resolve path" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_upload_file_directory_raises_error(self, mock_settings):
        """upload_file() should raise FileValidationError for directory path."""
        import tempfile

        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.exceptions import FileValidationError

        settings = get_settings()
        client = MattermostClient(settings)

        with tempfile.TemporaryDirectory() as tmpdir:
            async with client.lifespan():
                with pytest.raises(FileValidationError) as exc_info:
                    await client.upload_file("ch123", tmpdir)

                assert "not a file" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_upload_file_symlink_raises_error(self, mock_settings):
        """upload_file() should raise FileValidationError for symlink."""
        import tempfile
        from pathlib import Path

        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.exceptions import FileValidationError

        settings = get_settings()
        client = MattermostClient(settings)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a real file and a symlink to it
            real_file = Path(tmpdir) / "real.txt"
            symlink = Path(tmpdir) / "link.txt"

            real_file.write_text("test")
            symlink.symlink_to(real_file)

            async with client.lifespan():
                with pytest.raises(FileValidationError) as exc_info:
                    await client.upload_file("ch123", str(symlink))

                assert "symlink" in str(exc_info.value).lower() or "symbolic" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @respx.mock
    async def test_upload_file_retries_on_rate_limit(self, mock_settings, tmp_path):
        """upload_file() should retry on 429 like other API methods."""
        settings = Settings(
            url="https://test.mattermost.com",
            token="test-token-12345",
            max_retries=2,
        )
        client = MattermostClient(settings)

        route = respx.post("https://test.mattermost.com/api/v4/files").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "0"}),
                httpx.Response(201, json={"file_infos": [{"id": "file123"}]}),
            ],
        )

        temp_file = tmp_path / "test.txt"
        temp_file.write_text("retry test content")

        async with client.lifespan():
            result = await client.upload_file("ch123", str(temp_file))

        assert result["file_infos"][0]["id"] == "file123"
        assert route.call_count == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_upload_file_retries_on_server_error(self, mock_settings, tmp_path):
        """upload_file() should retry on 5xx like other API methods."""
        settings = Settings(
            url="https://test.mattermost.com",
            token="test-token-12345",
            max_retries=2,
        )
        client = MattermostClient(settings)

        route = respx.post("https://test.mattermost.com/api/v4/files").mock(
            side_effect=[
                httpx.Response(503),
                httpx.Response(201, json={"file_infos": [{"id": "file123"}]}),
            ],
        )

        temp_file = tmp_path / "test.txt"
        temp_file.write_text("retry test content")

        async with client.lifespan():
            result = await client.upload_file("ch123", str(temp_file))

        assert result["file_infos"][0]["id"] == "file123"
        assert route.call_count == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_upload_file_sends_file_content_on_retry(self, mock_settings, tmp_path):
        """upload_file() should send complete file content on every retry attempt."""
        settings = Settings(
            url="https://test.mattermost.com",
            token="test-token-12345",
            max_retries=2,
        )
        client = MattermostClient(settings)

        request_bodies: list[bytes] = []

        def capture_request(request):
            request_bodies.append(request.content)
            if len(request_bodies) == 1:
                return httpx.Response(429, headers={"Retry-After": "0"})
            return httpx.Response(201, json={"file_infos": [{"id": "file123"}]})

        respx.post("https://test.mattermost.com/api/v4/files").mock(side_effect=capture_request)

        file_content = "important data for retry test"
        temp_file = tmp_path / "test.txt"
        temp_file.write_text(file_content)

        async with client.lifespan():
            await client.upload_file("ch123", str(temp_file))

        assert len(request_bodies) == 2
        # Both requests should contain the file content (in multipart encoding)
        assert file_content.encode() in request_bodies[0]
        assert file_content.encode() in request_bodies[1]

    @pytest.mark.asyncio
    async def test_relative_path_resolved(self, mock_settings, tmp_path, monkeypatch):
        """Verify relative paths are resolved correctly."""
        from pathlib import Path

        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Change to tmp_path
        monkeypatch.chdir(tmp_path)

        # Verify path resolution works
        path = Path("test.txt").resolve(strict=True)
        assert path == test_file


class TestCreateDirectChannel:
    """Tests for create_direct_channel client method."""

    @pytest.mark.asyncio
    async def test_create_direct_channel_success(self, mock_settings) -> None:
        """Test creating a direct message channel between two users."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        async with client.lifespan():
            with respx.mock:
                respx.post("https://test.mattermost.com/api/v4/channels/direct").mock(
                    return_value=httpx.Response(
                        201,
                        json={
                            "id": "dm1234567890123456789012",
                            "type": "D",
                            "name": "us1234567890123456789012__us2234567890123456789012",
                        },
                    ),
                )

                result = await client.create_direct_channel(
                    user_ids=["us1234567890123456789012", "us2234567890123456789012"],
                )

                assert result["id"] == "dm1234567890123456789012"
                assert result["type"] == "D"


class TestMattermostClientBookmarksAPI:
    """Test Bookmarks API methods."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_bookmarks(self, mock_settings):
        """get_bookmarks() should return channel bookmarks."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/channels/ch123/bookmarks").mock(
            return_value=httpx.Response(
                200,
                json=[{"id": "bm123", "display_name": "Test", "type": "link"}],
            ),
        )

        async with client.lifespan():
            result = await client.get_bookmarks("ch123")

        assert result == [{"id": "bm123", "display_name": "Test", "type": "link"}]

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_bookmarks_with_since(self, mock_settings):
        """get_bookmarks() should pass bookmarks_since param."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        route = respx.get("https://test.mattermost.com/api/v4/channels/ch123/bookmarks").mock(
            return_value=httpx.Response(200, json=[]),
        )

        async with client.lifespan():
            await client.get_bookmarks("ch123", bookmarks_since=1234567890)

        assert route.calls[0].request.url.params["bookmarks_since"] == "1234567890"

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_bookmark(self, mock_settings):
        """create_bookmark() should create a bookmark."""
        import json

        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        route = respx.post("https://test.mattermost.com/api/v4/channels/ch123/bookmarks").mock(
            return_value=httpx.Response(
                201,
                json={"id": "bm123", "display_name": "Test", "type": "link"},
            ),
        )

        async with client.lifespan():
            result = await client.create_bookmark(
                channel_id="ch123",
                display_name="Test",
                bookmark_type="link",
                link_url="https://example.com",
            )

        assert result["id"] == "bm123"
        body = json.loads(route.calls[0].request.content)
        assert body["display_name"] == "Test"
        assert body["type"] == "link"
        assert body["link_url"] == "https://example.com"

    @pytest.mark.asyncio
    @respx.mock
    async def test_update_bookmark(self, mock_settings):
        """update_bookmark() should update bookmark fields."""
        import json

        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        route = respx.patch("https://test.mattermost.com/api/v4/channels/ch123/bookmarks/bm123").mock(
            return_value=httpx.Response(
                200,
                json={"id": "bm123", "display_name": "Updated"},
            ),
        )

        async with client.lifespan():
            result = await client.update_bookmark(
                channel_id="ch123",
                bookmark_id="bm123",
                display_name="Updated",
            )

        assert result["display_name"] == "Updated"
        body = json.loads(route.calls[0].request.content)
        assert body["display_name"] == "Updated"

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_bookmark(self, mock_settings):
        """delete_bookmark() should archive a bookmark."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.delete("https://test.mattermost.com/api/v4/channels/ch123/bookmarks/bm123").mock(
            return_value=httpx.Response(
                200,
                json={"id": "bm123", "delete_at": 1234567890},
            ),
        )

        async with client.lifespan():
            result = await client.delete_bookmark("ch123", "bm123")

        assert result["delete_at"] == 1234567890

    @pytest.mark.asyncio
    @respx.mock
    async def test_update_bookmark_sort_order(self, mock_settings):
        """update_bookmark_sort_order() should reorder bookmarks."""
        from mcp_server_mattermost.config import get_settings

        settings = get_settings()
        client = MattermostClient(settings)

        respx.post("https://test.mattermost.com/api/v4/channels/ch123/bookmarks/bm123/sort_order").mock(
            return_value=httpx.Response(
                200,
                json=[{"id": "bm123", "sort_order": 1}, {"id": "bm456", "sort_order": 0}],
            ),
        )

        async with client.lifespan():
            result = await client.update_bookmark_sort_order("ch123", "bm123", 1)

        assert len(result) == 2
        assert result[0]["sort_order"] == 1


class TestClientRequestIdLogging:
    """Test request_id correlation in HTTP logs."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_http_logs_include_request_id(self, mock_settings):
        """HTTP DEBUG logs include request_id from ContextVar."""
        from unittest.mock import patch

        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.logging import request_id_var

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/users/me").mock(
            return_value=httpx.Response(200, json={"id": "user123"}),
        )

        # Set request_id in context
        request_id_var.set("test-request-123")

        with patch("mcp_server_mattermost.client.logger") as mock_logger:
            async with client.lifespan():
                await client.get_me()

        # Check that logger.debug was called with request_id
        debug_calls = list(mock_logger.debug.call_args_list)
        assert any(call[1].get("extra", {}).get("request_id") == "test-request-123" for call in debug_calls)

    @pytest.mark.asyncio
    @respx.mock
    async def test_http_logs_without_request_id(self, mock_settings):
        """HTTP logs work when request_id is not set."""
        from mcp_server_mattermost.config import get_settings
        from mcp_server_mattermost.logging import request_id_var

        settings = get_settings()
        client = MattermostClient(settings)

        respx.get("https://test.mattermost.com/api/v4/users/me").mock(
            return_value=httpx.Response(200, json={"id": "user123"}),
        )

        # Ensure no request_id
        request_id_var.set(None)

        async with client.lifespan():
            result = await client.get_me()

        # Should not raise, request succeeds
        assert result["id"] == "user123"
