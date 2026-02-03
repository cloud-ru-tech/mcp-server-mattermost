"""Configuration management using Pydantic Settings."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Environment variables:
        MATTERMOST_URL: Mattermost server URL (required)
        MATTERMOST_TOKEN: Bot/user access token (required)
        MATTERMOST_TIMEOUT: Request timeout in seconds (default: 30)
        MATTERMOST_MAX_RETRIES: Max retry attempts (default: 3)
        MATTERMOST_VERIFY_SSL: Verify SSL certificates (default: true)
        MATTERMOST_LOG_LEVEL: Logging level (default: INFO)
        MATTERMOST_API_VERSION: API version (default: v4)
    """

    model_config = SettingsConfigDict(
        env_prefix="MATTERMOST_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    url: str = Field(description="Mattermost server URL")
    token: str = Field(description="Bot or user access token")
    timeout: int = Field(default=30, ge=1, le=300, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format: 'json' or 'text'")
    api_version: str = Field(default="v4", description="Mattermost API version")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Remove trailing slash."""
        return v.rstrip("/")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure level is in DEBUG, INFO, WARNING, ERROR, or CRITICAL."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid_levels:
            msg = f"Invalid log level: {v}. Must be one of {valid_levels}"
            raise ValueError(msg)
        return upper

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Ensure format is 'json' or 'text'."""
        valid_formats = {"json", "text"}
        lower = v.lower()
        if lower not in valid_formats:
            msg = f"Invalid log format: {v}. Must be one of {valid_formats}"
            raise ValueError(msg)
        return lower


@lru_cache
def get_settings() -> Settings:
    """Get application settings (cached).

    Returns:
        Application settings

    Raises:
        ConfigurationError: If required settings are missing
    """
    from .exceptions import ConfigurationError  # noqa: PLC0415

    try:
        return Settings()
    except Exception as e:
        msg = f"Failed to load configuration: {e}"
        raise ConfigurationError(msg) from e
