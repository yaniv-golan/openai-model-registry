"""Tests for the model registry functionality."""

import os
from pathlib import Path
from typing import Generator

import pytest
import yaml

from openai_model_registry.errors import (
    ModelNotSupportedError,
    OpenAIClientError,
)
from openai_model_registry.registry import (
    ModelRegistry,
)


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
    ModelRegistry._instance = None

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
                "allow_int": True,
            },
            "max_completion_tokens": {
                "type": "numeric",
                "min_value": 1,
                "max_value": None,
                "description": "Maximum number of tokens to generate",
                "allow_float": False,
                "allow_int": True,
            },
        },
        "enum_constraints": {
            "reasoning_effort": {
                "type": "enum",
                "allowed_values": ["low", "medium", "high"],
                "description": "Controls the model's reasoning depth",
            }
        },
    }

    with open(constraints_path, "w") as f:
        yaml.dump(constraints_content, f)

    # Create model capabilities file
    models_path = test_config_dir / "models.yml"
    models_content = {
        "version": "1.0.0",
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
                "description": "Test model",
                "min_version": {"year": 2024, "month": 1, "day": 1},
            },
            "gpt-4o-2024-08-06": {
                "context_window": 128000,
                "max_output_tokens": 16384,
                "supports_structured": True,
                "supports_streaming": True,
                "supported_parameters": [
                    {"ref": "numeric_constraints.temperature"},
                    {"ref": "numeric_constraints.max_completion_tokens"},
                ],
                "description": "Test GPT-4o model",
                "min_version": {"year": 2024, "month": 8, "day": 6},
            },
        },
        "aliases": {
            "test-model": "test-model-2024-01-01",
            "gpt-4o": "gpt-4o-2024-08-06",
        },
    }

    with open(models_path, "w") as f:
        yaml.dump(models_content, f)

    # Set environment variables
    os.environ["MODEL_REGISTRY_PATH"] = str(models_path)
    os.environ["PARAMETER_CONSTRAINTS_PATH"] = str(constraints_path)

    # Create and return registry
    registry = ModelRegistry()

    yield registry

    # Restore original environment variables
    if original_registry_path:
        os.environ["MODEL_REGISTRY_PATH"] = original_registry_path
    else:
        os.environ.pop("MODEL_REGISTRY_PATH", None)

    if original_constraints_path:
        os.environ["PARAMETER_CONSTRAINTS_PATH"] = original_constraints_path
    else:
        os.environ.pop("PARAMETER_CONSTRAINTS_PATH", None)

    # Reset the singleton
    ModelRegistry._instance = None


def test_registry_initialization(registry: ModelRegistry) -> None:
    """Test that the registry initializes correctly."""
    # Check that capabilities were loaded
    assert len(registry.models) > 0
    assert "test-model" in registry.models
    assert "gpt-4o" in registry.models


def test_get_capabilities(registry: ModelRegistry) -> None:
    """Test getting model capabilities."""
    # Test getting by alias
    capabilities = registry.get_capabilities("test-model")
    assert capabilities.context_window == 4096
    assert capabilities.max_output_tokens == 2048
    assert capabilities.supports_structured is True

    # Test getting by dated model
    capabilities = registry.get_capabilities("test-model-2024-01-01")
    assert capabilities.context_window == 4096
    assert capabilities.max_output_tokens == 2048


def test_unsupported_model(registry: ModelRegistry) -> None:
    """Test behavior with unsupported models."""
    with pytest.raises(ModelNotSupportedError):
        registry.get_capabilities("not-a-model")


def test_parameter_validation(registry: ModelRegistry) -> None:
    """Test parameter validation."""
    capabilities = registry.get_capabilities("test-model")

    # Valid parameters
    capabilities.validate_parameter("temperature", 0.7)
    capabilities.validate_parameter("max_completion_tokens", 100)

    # Invalid parameters
    with pytest.raises(OpenAIClientError):
        capabilities.validate_parameter("temperature", 3.0)

    with pytest.raises(OpenAIClientError):
        capabilities.validate_parameter("max_completion_tokens", 0)

    with pytest.raises(OpenAIClientError):
        capabilities.validate_parameter("unsupported_param", 1.0)
