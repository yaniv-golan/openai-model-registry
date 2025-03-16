"""Tests for the constraint classes."""

import pytest

from openai_model_registry.constraints import (
    EnumConstraint,
    NumericConstraint,
    ParameterReference,
)
from openai_model_registry.errors import ModelRegistryError


def test_parameter_reference() -> None:
    """Test ParameterReference class."""
    # Test basic initialization
    ref = ParameterReference("temperature", "Controls randomness")
    assert ref.ref == "temperature"
    assert ref.description == "Controls randomness"
    assert ref.max_value is None

    # Test with max_value
    ref = ParameterReference("tokens", "Max tokens", max_value=100.0)
    assert ref.ref == "tokens"
    assert ref.description == "Max tokens"
    assert ref.max_value == 100.0


def test_numeric_constraint_initialization() -> None:
    """Test NumericConstraint initialization."""
    # Test with default values
    constraint = NumericConstraint(min_value=0.0, max_value=1.0)
    assert constraint.min_value == 0.0
    assert constraint.max_value == 1.0
    assert constraint.allow_float is True
    assert constraint.allow_int is True
    assert constraint.description == ""

    # Test with custom values
    constraint = NumericConstraint(
        min_value=1.0,
        max_value=10.0,
        allow_float=False,
        allow_int=True,
        description="Must be an integer between 1 and 10",
    )
    assert constraint.min_value == 1.0
    assert constraint.max_value == 10.0
    assert constraint.allow_float is False
    assert constraint.allow_int is True
    assert constraint.description == "Must be an integer between 1 and 10"


def test_numeric_constraint_validation() -> None:
    """Test NumericConstraint validation."""
    # Create constraint that allows both float and int
    constraint = NumericConstraint(
        min_value=0.0,
        max_value=1.0,
        allow_float=True,
        allow_int=True,
        description="Must be between 0 and 1",
    )

    # Valid values
    constraint.validate("test_param", 0.0)
    constraint.validate("test_param", 0.5)
    constraint.validate("test_param", 1.0)
    constraint.validate("test_param", 0)
    constraint.validate("test_param", 1)

    # Invalid values - type error
    with pytest.raises(ModelRegistryError) as exc_info:
        constraint.validate("test_param", "0.5")
    assert "must be a number" in str(exc_info.value)

    # Invalid values - out of range
    with pytest.raises(ModelRegistryError) as exc_info:
        constraint.validate("test_param", -0.1)
    assert "must be between" in str(exc_info.value)

    with pytest.raises(ModelRegistryError) as exc_info:
        constraint.validate("test_param", 1.1)
    assert "must be between" in str(exc_info.value)

    # Test int-only constraint
    int_constraint = NumericConstraint(
        min_value=1,
        max_value=10,
        allow_float=False,
        allow_int=True,
        description="Must be an integer between 1 and 10",
    )

    # Valid values
    int_constraint.validate("test_param", 1)
    int_constraint.validate("test_param", 5)
    int_constraint.validate("test_param", 10)

    # Invalid values - float not allowed
    with pytest.raises(ModelRegistryError) as exc_info:
        int_constraint.validate("test_param", 5.5)
    assert "must be an integer" in str(exc_info.value)

    # Test float-only constraint
    float_constraint = NumericConstraint(
        min_value=0.0,
        max_value=1.0,
        allow_float=True,
        allow_int=False,
        description="Must be a float between 0 and 1",
    )

    # Valid values
    float_constraint.validate("test_param", 0.0)
    float_constraint.validate("test_param", 0.5)
    float_constraint.validate("test_param", 1.0)

    # Invalid values - int not allowed
    with pytest.raises(ModelRegistryError) as exc_info:
        float_constraint.validate("test_param", 1)
    assert "must be a float" in str(exc_info.value)


def test_enum_constraint_initialization() -> None:
    """Test EnumConstraint initialization."""
    # Test basic initialization
    constraint = EnumConstraint(
        allowed_values=["low", "medium", "high"],
        description="Reasoning effort level",
    )
    assert constraint.allowed_values == ["low", "medium", "high"]
    assert constraint.description == "Reasoning effort level"


def test_enum_constraint_validation() -> None:
    """Test EnumConstraint validation."""
    # Create constraint
    constraint = EnumConstraint(
        allowed_values=["low", "medium", "high"],
        description="Reasoning effort level",
    )

    # Valid values
    constraint.validate("test_param", "low")
    constraint.validate("test_param", "medium")
    constraint.validate("test_param", "high")

    # Invalid values - not in allowed values
    with pytest.raises(ModelRegistryError) as exc_info:
        constraint.validate("test_param", "very_high")
    assert "Invalid value" in str(exc_info.value)
    assert "Allowed values: high, low, medium" in str(exc_info.value)

    # Invalid values - type error
    with pytest.raises(ModelRegistryError) as exc_info:
        constraint.validate("test_param", 123)
    assert "must be a string" in str(exc_info.value)
