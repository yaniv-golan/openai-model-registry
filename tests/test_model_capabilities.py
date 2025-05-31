"""Tests for the ModelCapabilities class."""

from typing import Set

import pytest

from openai_model_registry.constraints import (
    EnumConstraint,
    NumericConstraint,
    ParameterReference,
)
from openai_model_registry.deprecation import DeprecationInfo
from openai_model_registry.errors import (
    ModelRegistryError,
    ParameterNotSupportedError,
)
from openai_model_registry.model_version import ModelVersion
from openai_model_registry.registry import ModelCapabilities


def _create_test_deprecation() -> DeprecationInfo:
    """Create a test deprecation info for active models."""
    return DeprecationInfo(
        status="active",
        deprecates_on=None,
        sunsets_on=None,
        replacement=None,
        migration_guide=None,
        reason="active",
    )


def test_model_capabilities_initialization() -> None:
    """Test ModelCapabilities initialization."""
    # Create a model capabilities instance
    capabilities = ModelCapabilities(
        model_name="test-model",
        openai_model_name="test-model",
        context_window=4096,
        max_output_tokens=2048,
        deprecation=_create_test_deprecation(),
        supports_vision=False,
        supports_functions=True,
        supports_streaming=True,
        supports_structured=True,
        min_version=ModelVersion(2024, 1, 1),
        aliases=["test-model-alias"],
        supported_parameters=[
            ParameterReference(
                ref="temperature",
                description="Controls randomness in the output",
            ),
        ],
        constraints={
            "temperature": NumericConstraint(
                min_value=0.0,
                max_value=2.0,
                description="Controls randomness in the output",
            ),
        },
    )

    # Check basic properties
    assert capabilities.model_name == "test-model"
    assert capabilities.openai_model_name == "test-model"
    assert capabilities.context_window == 4096
    assert capabilities.max_output_tokens == 2048
    assert capabilities.supports_vision is False
    assert capabilities.supports_functions is True
    assert capabilities.supports_streaming is True
    assert capabilities.supports_structured is True
    assert capabilities.min_version == ModelVersion(2024, 1, 1)
    assert capabilities.aliases == ["test-model-alias"]
    assert len(capabilities.supported_parameters) == 1
    assert capabilities.supported_parameters[0].ref == "temperature"


def test_model_capabilities_get_constraint() -> None:
    """Test ModelCapabilities.get_constraint method."""
    # Create constraints
    temperature_constraint = NumericConstraint(
        min_value=0.0,
        max_value=2.0,
        description="Controls randomness in the output",
    )
    effort_constraint = EnumConstraint(
        allowed_values=["low", "medium", "high"],
        description="Controls reasoning effort",
    )

    # Create capabilities
    capabilities = ModelCapabilities(
        model_name="test-model",
        openai_model_name="test-model",
        context_window=4096,
        max_output_tokens=2048,
        deprecation=_create_test_deprecation(),
        constraints={
            "temperature": temperature_constraint,
            "reasoning_effort": effort_constraint,
        },
    )

    # Test retrieving constraints
    assert capabilities.get_constraint("temperature") is temperature_constraint
    assert capabilities.get_constraint("reasoning_effort") is effort_constraint
    assert capabilities.get_constraint("nonexistent") is None


def test_model_capabilities_validate_parameter() -> None:
    """Test ModelCapabilities.validate_parameter method."""
    # Create capabilities with constraints
    capabilities = ModelCapabilities(
        model_name="test-model",
        openai_model_name="test-model",
        context_window=4096,
        max_output_tokens=2048,
        deprecation=_create_test_deprecation(),
        supported_parameters=[
            ParameterReference(
                ref="temperature",
                description="Controls randomness",
            ),
            ParameterReference(
                ref="reasoning_effort",
                description="Controls reasoning effort",
            ),
        ],
        constraints={
            "temperature": NumericConstraint(
                min_value=0.0,
                max_value=2.0,
                description="Controls randomness",
            ),
            "reasoning_effort": EnumConstraint(
                allowed_values=["low", "medium", "high"],
                description="Controls reasoning effort",
            ),
        },
    )

    # Test valid parameters
    capabilities.validate_parameter("temperature", 0.7)
    capabilities.validate_parameter("reasoning_effort", "medium")

    # Test parameter not in supported_parameters
    with pytest.raises(ParameterNotSupportedError):
        capabilities.validate_parameter("nonexistent", "value")

    # Test invalid parameters
    with pytest.raises(ModelRegistryError):
        capabilities.validate_parameter("temperature", 3.0)

    with pytest.raises(ModelRegistryError):
        capabilities.validate_parameter("reasoning_effort", "extreme")


def test_model_capabilities_validate_parameters() -> None:
    """Test ModelCapabilities.validate_parameters method."""
    # Create capabilities with constraints
    capabilities = ModelCapabilities(
        model_name="test-model",
        openai_model_name="test-model",
        context_window=4096,
        max_output_tokens=2048,
        deprecation=_create_test_deprecation(),
        supported_parameters=[
            ParameterReference(
                ref="temperature",
                description="Controls randomness",
            ),
            ParameterReference(
                ref="max_tokens",
                description="Max tokens to generate",
            ),
        ],
        constraints={
            "temperature": NumericConstraint(
                min_value=0.0,
                max_value=2.0,
                description="Controls randomness",
            ),
            "max_tokens": NumericConstraint(
                min_value=1,
                max_value=2048,
                allow_float=False,
                description="Max tokens to generate",
            ),
        },
    )

    # Test valid parameter set
    capabilities.validate_parameters(
        {
            "temperature": 0.7,
            "max_tokens": 1024,
        }
    )

    # Test with used_params tracking
    used_params: Set[str] = set()
    capabilities.validate_parameters(
        {
            "temperature": 0.7,
            "max_tokens": 1024,
        },
        used_params,
    )
    assert "temperature" in used_params
    assert "max_tokens" in used_params

    # Test invalid parameter
    with pytest.raises(ModelRegistryError):
        capabilities.validate_parameters(
            {
                "temperature": 0.7,
                "max_tokens": 3000,  # Too high
            }
        )


def test_web_search_capability() -> None:
    """Test web search capability tracking."""
    # Test model with web search support
    web_search_model = ModelCapabilities(
        model_name="gpt-4o-search-preview",
        openai_model_name="gpt-4o-search-preview",
        context_window=128000,
        max_output_tokens=16384,
        deprecation=_create_test_deprecation(),
        supports_web_search=True,
    )

    # Test model without web search support
    regular_model = ModelCapabilities(
        model_name="gpt-3.5-turbo",
        openai_model_name="gpt-3.5-turbo",
        context_window=4096,
        max_output_tokens=2048,
        deprecation=_create_test_deprecation(),
        supports_web_search=False,
    )

    # Test web search capability detection
    assert web_search_model.supports_web_search is True
    assert regular_model.supports_web_search is False

    # Test that web search is properly tracked alongside other capabilities
    assert web_search_model.supports_web_search
    assert not regular_model.supports_web_search


def test_web_search_capability_default() -> None:
    """Test that web search capability defaults to False."""
    # Test that web search defaults to False when not specified
    default_model = ModelCapabilities(
        model_name="test-model",
        openai_model_name="test-model",
        context_window=4096,
        max_output_tokens=2048,
        deprecation=_create_test_deprecation(),
        # supports_web_search not specified, should default to False
    )

    assert default_model.supports_web_search is False
