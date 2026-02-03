"""Logging configuration for MCP server.

All logs go to stderr per MCP specification.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, ClassVar, Final


LOGGER_NAME: Final = "mcp-server-mattermost"

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class JSONFormatter(logging.Formatter):
    """Format log records as JSON lines."""

    # Fields that are part of LogRecord but not useful in JSON output
    EXCLUDE_FIELDS: ClassVar[set[str]] = {
        "name",
        "msg",
        "args",
        "created",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "exc_info",
        "exc_text",
        "thread",
        "threadName",
        "taskName",
        "message",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format record as JSON line.

        Args:
            record: Log record to format

        Returns:
            JSON string
        """
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "message": record.getMessage(),
        }

        # Add extra fields from record
        log_data.update(
            {
                key: value
                for key, value in record.__dict__.items()
                if key not in self.EXCLUDE_FIELDS and not key.startswith("_")
            },
        )

        return json.dumps(log_data, default=str)


def setup_logging(level: str = "INFO", log_format: str = "json") -> logging.Logger:
    """Configure logging to stderr for MCP compliance.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ('json' for production, 'text' for development)

    Returns:
        Configured logger instance

    Raises:
        ValueError: If level is not a valid logging level
    """
    log = logging.getLogger(LOGGER_NAME)
    log.propagate = False

    level_upper = level.upper()
    level_value = getattr(logging, level_upper, None)
    if level_value is None or not isinstance(level_value, int):
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        msg = f"Invalid logging level: {level}. Must be one of {valid_levels}"
        raise ValueError(msg)
    log.setLevel(level_value)

    if not log.handlers:
        handler = logging.StreamHandler(sys.stderr)
        if log_format == "json":
            handler.setFormatter(JSONFormatter())
        else:
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                ),
            )
        log.addHandler(handler)

    return log


logger = setup_logging()
