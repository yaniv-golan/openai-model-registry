"""Tests for the model registry functionality."""

import os
from pathlib import Path
from typing import Generator

import pytest
import yaml

from openai_model_registry import (
    ModelRegistry,
    ModelRegistryError,
)
from openai_model_registry.errors import (
    ModelNotSupportedError,
)
from openai_model_registry.registry import RegistryConfig


@pytest.fixture
def test_config_dir(tmp_path: Path) -> Path:
    """Create a test configuration directory.

    Returns:
        Path to the temporary directory
    """
    return tmp_path


@pytest.fixture
def registry(test_config_dir: Path) -> Generator[ModelRegistry, None, None]:
    """Create a test registry with temporary config files.

    Args:
        test_config_dir: Temporary directory for config files

    Returns:
        ModelRegistry instance for testing
    """
    # Store original env vars
    original_registry_path = os.environ.get("MODEL_REGISTRY_PATH")
    original_constraints_path = os.environ.get("PARAMETER_CONSTRAINTS_PATH")

    # Cleanup any existing registry first
    ModelRegistry._default_instance = None

    # Create parameter constraints file
    constraints_path = test_config_dir / "parameter_constraints.yml"
    constraints_content = {
        "numeric_constraints": {
            "temperature": {
                "type": "numeric",
                "min_value": 0.0,
                "max_value": 2.0,
                "description": "Controls randomness in the output",
                "allow_float": True,
            },
            "max_completion_tokens": {
                "type": "numeric",
                "min_value": 1,
                "description": "Maximum number of tokens to generate",
                "allow_float": False,
            },
        },
        "enum_constraints": {
            "reasoning_effort": {
                "type": "enum",
                "allowed_values": ["low", "medium", "high"],
                "description": "Controls the model's reasoning depth",
            },
        },
    }

    with open(constraints_path, "w") as f:
        yaml.dump(constraints_content, f)

    # Create model capabilities file
    models_path = test_config_dir / "models.yml"
    models_content = {
        "version": "1.1.0",
        "dated_models": {
            "test-model-2024-01-01": {
                "context_window": 4096,
                "max_output_tokens": 2048,
                "supports_structured": True,
                "supports_streaming": True,
                "supported_parameters": [
                    {"ref": "numeric_constraints.temperature"},
                    {"ref": "numeric_constraints.max_completion_tokens"},
                ],
                "description": "Test model for unit tests",
                "min_version": {
                    "year": 2024,
                    "month": 1,
                    "day": 1,
                },
                "deprecation": {
                    "status": "active",
                    "deprecates_on": None,
                    "sunsets_on": None,
                    "replacement": None,
                    "migration_guide": None,
                    "reason": "active",
                },
            },
            "gpt-4o-2024-05-13": {
                "context_window": 128000,
                "max_output_tokens": 16384,
                "supports_structured": True,
                "supports_streaming": True,
                "supports_vision": True,
                "supports_functions": True,
                "supported_parameters": [
                    {"ref": "numeric_constraints.temperature"},
                    {"ref": "numeric_constraints.max_completion_tokens"},
                    {"ref": "enum_constraints.reasoning_effort"},
                ],
                "description": "GPT-4o test model",
                "min_version": {
                    "year": 2024,
                    "month": 5,
                    "day": 13,
                },
                "deprecation": {
                    "status": "active",
                    "deprecates_on": None,
                    "sunsets_on": None,
                    "replacement": None,
                    "migration_guide": None,
                    "reason": "active",
                },
            },
        },
        "aliases": {
            "test-model": "test-model-2024-01-01",
            "gpt-4o": "gpt-4o-2024-05-13",
        },
    }

    with open(models_path, "w") as f:
        yaml.dump(models_content, f)

    # Set environment variables to point to test files
    os.environ["MODEL_REGISTRY_PATH"] = str(models_path)
    os.environ["PARAMETER_CONSTRAINTS_PATH"] = str(constraints_path)

    # Create and return registry with the test configuration
    config = RegistryConfig(
        registry_path=str(models_path), constraints_path=str(constraints_path)
    )
    registry = ModelRegistry(config)

    try:
        yield registry
    finally:
        # Clean up environment variables
        if original_registry_path:
            os.environ["MODEL_REGISTRY_PATH"] = original_registry_path
        else:
            os.environ.pop("MODEL_REGISTRY_PATH", None)

        if original_constraints_path:
            os.environ[
                "PARAMETER_CONSTRAINTS_PATH"
            ] = original_constraints_path
        else:
            os.environ.pop("PARAMETER_CONSTRAINTS_PATH", None)

        # Reset the registry
        ModelRegistry._default_instance = None


def test_registry_initialization(registry: ModelRegistry) -> None:
    """Test that the registry initializes properly."""
    assert registry is not None
    assert registry.config is not None
    assert "test-model-2024-01-01" in registry.models
    assert "gpt-4o-2024-05-13" in registry.models


def test_get_capabilities(registry: ModelRegistry) -> None:
    """Test retrieving model capabilities."""
    # Test getting capabilities for a dated model
    capabilities = registry.get_capabilities("test-model-2024-01-01")
    assert capabilities.context_window == 4096
    assert capabilities.max_output_tokens == 2048
    assert capabilities.supports_streaming is True
    assert capabilities.supports_structured is True

    # Test getting capabilities via the base model alias
    base_capabilities = registry.get_capabilities("test-model")
    assert base_capabilities.context_window == 4096


def test_unsupported_model(registry: ModelRegistry) -> None:
    """Test error handling for unsupported models."""
    with pytest.raises(ModelNotSupportedError):
        registry.get_capabilities("non-existent-model")


def test_parameter_validation(registry: ModelRegistry) -> None:
    """Test parameter validation."""
    capabilities = registry.get_capabilities("test-model")

    # Test valid parameter
    capabilities.validate_parameter("temperature", 0.7)

    # Test invalid parameter (too high)
    with pytest.raises(ModelRegistryError):
        capabilities.validate_parameter("temperature", 3.0)

    # Test invalid parameter type
    with pytest.raises(ModelRegistryError):
        capabilities.validate_parameter("temperature", "hot")


def test_registry_config() -> None:
    """Test creating registry with different configurations."""
    # Clean up for this test
    ModelRegistry._default_instance = None

    # Test creating with explicit config
    config = RegistryConfig(
        registry_path="/custom/path/registry.yml",
        constraints_path="/custom/path/constraints.yml",
        auto_update=True,
        cache_size=200,
    )
    registry = ModelRegistry(config)

    assert registry.config is not None
    assert registry.config.registry_path == "/custom/path/registry.yml"
    assert registry.config.constraints_path == "/custom/path/constraints.yml"
    assert registry.config.auto_update is True
    assert registry.config.cache_size == 200


def test_multiple_registry_instances() -> None:
    """Test creating multiple registry instances."""
    # Clean up for this test
    ModelRegistry._default_instance = None

    # Create two different configurations
    config1 = RegistryConfig(registry_path="/path/to/registry1.yml")
    config2 = RegistryConfig(registry_path="/path/to/registry2.yml")

    # Create two registry instances
    registry1 = ModelRegistry(config1)
    registry2 = ModelRegistry(config2)

    # Check they have different configurations
    assert registry1.config.registry_path == "/path/to/registry1.yml"
    assert registry2.config.registry_path == "/path/to/registry2.yml"
    assert registry1 is not registry2


def test_default_registry_instance() -> None:
    """Test getting the default registry instance."""
    # Clean up for this test
    ModelRegistry._default_instance = None

    # Get default instance
    registry1 = ModelRegistry.get_default()
    registry2 = ModelRegistry.get_default()

    # Should be the same instance
    assert registry1 is registry2

    # Test backwards compatibility
    registry3 = ModelRegistry.get_instance()
    assert registry3 is registry1
