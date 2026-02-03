"""Tests for base response models."""

import pytest
from pydantic import ValidationError

from mcp_server_mattermost.models.base import MattermostResponse


def test_base_model_allows_extra_fields():
    """Test that MattermostResponse accepts unknown fields."""
    data = {
        "known_field": "value",
        "unknown_field": "should be preserved",
        "another_unknown": 123,
    }

    class TestModel(MattermostResponse):
        known_field: str

    model = TestModel(**data)
    assert model.known_field == "value"
    assert model.__pydantic_extra__["unknown_field"] == "should be preserved"
    assert model.__pydantic_extra__["another_unknown"] == 123


def test_base_model_serializes_extra_fields():
    """Test that model_dump includes extra fields."""

    class TestModel(MattermostResponse):
        id: str

    model = TestModel(id="123", extra_field="value")
    dumped = model.model_dump()

    assert dumped["id"] == "123"
    assert dumped["extra_field"] == "value"


def test_base_model_validates_defined_fields():
    """Test that defined fields are validated."""

    class TestModel(MattermostResponse):
        count: int

    with pytest.raises(ValidationError):
        TestModel(count="not an int")
