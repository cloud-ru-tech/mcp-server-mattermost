"""Custom exceptions for Mattermost MCP server."""


class MattermostMCPError(Exception):
    """Base exception for all Mattermost MCP errors."""


class ConfigurationError(MattermostMCPError):
    """Raised when configuration is invalid or missing."""


class MattermostAPIError(MattermostMCPError):
    """Raised when Mattermost API returns an error.

    Attributes:
        status_code: HTTP status code from API
        error_id: Mattermost error identifier
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_id: str | None = None,
    ) -> None:
        """Initialize API error.

        Args:
            message: Error message
            status_code: HTTP status code
            error_id: Mattermost error ID
        """
        super().__init__(message)
        self.status_code = status_code
        self.error_id = error_id

    def __str__(self) -> str:
        """Format error with status code and error_id."""
        parts = [super().__str__()]
        if self.status_code is not None:
            parts.append(f"status={self.status_code}")
        if self.error_id is not None:
            parts.append(f"error_id={self.error_id}")
        return " ".join(parts)


class RateLimitError(MattermostAPIError):
    """Raised when API rate limit is exceeded (429)."""

    def __init__(self, retry_after: int | None = None) -> None:
        """Initialize rate limit error.

        Args:
            retry_after: Seconds to wait before retrying
        """
        super().__init__("Rate limit exceeded", status_code=429)
        self.retry_after = retry_after


class AuthenticationError(MattermostAPIError):
    """Raised when authentication fails (401)."""

    def __init__(self, message: str = "Authentication failed") -> None:
        """Initialize authentication error.

        Args:
            message: Error message
        """
        super().__init__(message, status_code=401)


class NotFoundError(MattermostAPIError):
    """Raised when requested resource is not found (404)."""

    def __init__(self, message: str = "Resource not found", *, error_id: str | None = None) -> None:
        """Initialize not found error.

        Args:
            message: Error message (from API response or default)
            error_id: Mattermost error identifier from API response
        """
        super().__init__(message, status_code=404, error_id=error_id)


class ValidationError(MattermostMCPError):
    """Raised when input validation fails."""


class FileValidationError(ValidationError):
    """Raised when file path validation fails.

    Attributes:
        file_path: The invalid file path
    """

    def __init__(self, file_path: str, message: str) -> None:
        """Initialize file validation error.

        Args:
            file_path: The file path that failed validation
            message: Description of the validation failure
        """
        super().__init__(f"{message}: {file_path}")
        self.file_path = file_path
