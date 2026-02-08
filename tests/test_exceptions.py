def test_base_exception_exists():
    from mcp_server_mattermost.exceptions import MattermostMCPError

    exc = MattermostMCPError("test")
    assert str(exc) == "test"


def test_configuration_error():
    from mcp_server_mattermost.exceptions import ConfigurationError, MattermostMCPError

    exc = ConfigurationError("bad config")
    assert isinstance(exc, MattermostMCPError)


def test_api_error_attributes():
    from mcp_server_mattermost.exceptions import MattermostAPIError

    exc = MattermostAPIError("error", status_code=500, error_id="server.error")
    assert exc.status_code == 500
    assert exc.error_id == "server.error"
    assert "500" in str(exc)
    assert "server.error" in str(exc)


def test_rate_limit_error():
    from mcp_server_mattermost.exceptions import RateLimitError

    exc = RateLimitError(retry_after=60)
    assert exc.status_code == 429
    assert exc.retry_after == 60


def test_authentication_error():
    from mcp_server_mattermost.exceptions import AuthenticationError

    exc = AuthenticationError()
    assert exc.status_code == 401


def test_not_found_error_default_message():
    from mcp_server_mattermost.exceptions import NotFoundError

    exc = NotFoundError()
    assert str(exc) == "Resource not found status=404"
    assert exc.status_code == 404


def test_not_found_error_with_message():
    from mcp_server_mattermost.exceptions import NotFoundError

    exc = NotFoundError("We couldn't find the existing channel.")
    assert "We couldn't find the existing channel." in str(exc)
    assert exc.status_code == 404


def test_not_found_error_with_error_id():
    from mcp_server_mattermost.exceptions import NotFoundError

    exc = NotFoundError("Channel not found", error_id="app.channel.get.existing.app_error")
    assert "Channel not found" in str(exc)
    assert "error_id=app.channel.get.existing.app_error" in str(exc)
    assert exc.error_id == "app.channel.get.existing.app_error"


def test_validation_error():
    from mcp_server_mattermost.exceptions import MattermostMCPError, ValidationError

    exc = ValidationError("invalid input")
    assert isinstance(exc, MattermostMCPError)


def test_file_validation_error():
    """FileValidationError should be a ValidationError subclass."""
    from mcp_server_mattermost.exceptions import FileValidationError, ValidationError

    exc = FileValidationError("/path/to/file", "File not found")
    assert isinstance(exc, ValidationError)
    assert exc.file_path == "/path/to/file"
    assert "File not found" in str(exc)
    assert "/path/to/file" in str(exc)
