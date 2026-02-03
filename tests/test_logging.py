import json
import logging


def test_logger_exists():
    from mcp_server_mattermost.logging import logger

    assert isinstance(logger, logging.Logger)


def test_logger_name():
    from mcp_server_mattermost.logging import LOGGER_NAME, logger

    assert logger.name == LOGGER_NAME


def test_setup_logging_returns_logger():
    from mcp_server_mattermost.logging import setup_logging

    result = setup_logging("DEBUG")
    assert isinstance(result, logging.Logger)


def test_setup_logging_sets_level():
    from mcp_server_mattermost.logging import setup_logging

    logger = setup_logging("WARNING")
    assert logger.level == logging.WARNING


def test_setup_logging_invalid_level():
    import pytest

    from mcp_server_mattermost.logging import setup_logging

    with pytest.raises(ValueError, match="Invalid logging level"):
        setup_logging("INVALID")


def test_request_id_var_default_none():
    """ContextVar returns None by default."""
    from mcp_server_mattermost.logging import request_id_var

    # New context should have None
    assert request_id_var.get() is None


def test_request_id_var_set_and_get():
    """ContextVar correctly stores and returns value."""
    from contextvars import copy_context

    from mcp_server_mattermost.logging import request_id_var

    def set_and_check():
        request_id_var.set("test-request-123")
        return request_id_var.get()

    # Run in isolated context
    ctx = copy_context()
    result = ctx.run(set_and_check)
    assert result == "test-request-123"

    # Original context unchanged
    assert request_id_var.get() is None


def test_json_formatter_basic_fields():
    """JSON contains timestamp, level, message."""
    from mcp_server_mattermost.logging import JSONFormatter

    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    output = formatter.format(record)
    data = json.loads(output)

    assert "timestamp" in data
    assert data["level"] == "INFO"
    assert data["message"] == "Test message"


def test_json_formatter_extra_fields():
    """Extra fields merged into JSON output."""
    from mcp_server_mattermost.logging import JSONFormatter

    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="",
        args=(),
        exc_info=None,
    )
    record.event = "tool_call_start"
    record.request_id = "abc-123"
    record.tool = "list_channels"

    output = formatter.format(record)
    data = json.loads(output)

    assert data["event"] == "tool_call_start"
    assert data["request_id"] == "abc-123"
    assert data["tool"] == "list_channels"


def test_json_formatter_valid_json():
    """Output is valid JSON."""
    from mcp_server_mattermost.logging import JSONFormatter

    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.WARNING,
        pathname="test.py",
        lineno=1,
        msg='Warning with special chars: \n\t"quotes"',
        args=(),
        exc_info=None,
    )

    output = formatter.format(record)
    # Should not raise
    data = json.loads(output)
    assert "quotes" in data["message"]


def test_setup_logging_json_format():
    """setup_logging with format='json' uses JSONFormatter."""
    from mcp_server_mattermost.logging import JSONFormatter, setup_logging

    logger = setup_logging(level="INFO", log_format="json")

    # Clear existing handlers and re-setup
    logger.handlers.clear()
    logger = setup_logging(level="INFO", log_format="json")

    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0].formatter, JSONFormatter)


def test_setup_logging_text_format():
    """setup_logging with format='text' uses standard Formatter."""
    from mcp_server_mattermost.logging import JSONFormatter, setup_logging

    logger = setup_logging(level="INFO", log_format="text")

    # Clear existing handlers and re-setup
    logger.handlers.clear()
    logger = setup_logging(level="INFO", log_format="text")

    assert len(logger.handlers) == 1
    assert not isinstance(logger.handlers[0].formatter, JSONFormatter)
