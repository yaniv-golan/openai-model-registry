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
        "temperature": {
            "type": "numeric",
            "min": 0.0,
            "max": 2.0,
            "description": "Controls randomness in the output",
            "allow_float": True,
        },
        "max_completion_tokens": {
            "type": "numeric",
            "min": 1,
            "description": "Maximum number of tokens to generate",
            "allow_float": False,
        },
        "reasoning_effort": {
            "type": "enum",
            "values": ["low", "medium", "high"],
            "description": "Controls the model's reasoning depth",
        },
    }

    with open(constraints_path, "w") as f:
        yaml.dump(constraints_content, f)

    # Create model capabilities file
    models_path = test_config_dir / "models.yml"
    models_content = {
        "version": "1.0.0",
        "models": {
            "test-model-2024-01-01": {
                "openai_name": "test-model",
                "context_window": 4096,
                "max_output_tokens": 2048,
                "supports_structured": True,
                "supports_streaming": True,
                "min_version": "2024-01-01",
                "parameters": {
                    "temperature": {
                        "constraint": "temperature",
                        "description": "Controls randomness in the output",
                    },
                    "max_completion_tokens": {
                        "constraint": "max_completion_tokens",
                        "description": "Maximum number of tokens to generate",
                    },
                },
                "aliases": ["test-model"],
            },
            "gpt-4o-2024-08-06": {
                "openai_name": "gpt-4o",
                "context_window": 128000,
                "max_output_tokens": 16384,
                "supports_structured": True,
                "supports_streaming": True,
                "supports_vision": True,
                "supports_functions": True,
                "min_version": "2024-08-06",
                "parameters": {
                    "temperature": {
                        "constraint": "temperature",
                        "description": "Controls randomness in the output",
                    },
                    "max_completion_tokens": {
                        "constraint": "max_completion_tokens",
                        "description": "Maximum number of tokens to generate",
                    },
                    "reasoning_effort": {
                        "constraint": "reasoning_effort",
                        "description": "Controls the reasoning depth",
                    },
                },
                "aliases": ["gpt-4o"],
            },
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
    assert "gpt-4o-2024-08-06" in registry.models


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
