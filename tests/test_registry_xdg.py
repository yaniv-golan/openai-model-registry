"""Tests for the ModelRegistry XDG path handling."""

import os
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest

from openai_model_registry.config_paths import (
    PARAM_CONSTRAINTS_FILENAME,
)
from openai_model_registry.registry import (
    ModelRegistry,
    RegistryConfig,
)


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture(autouse=True)
def reset_registry_singleton() -> Generator[None, None, None]:
    """Reset the ModelRegistry singleton before and after each test."""
    # Reset the default instance
    original_instance = ModelRegistry._default_instance
    ModelRegistry._default_instance = None

    # Run the test
    yield

    # Restore the original instance
    ModelRegistry._default_instance = original_instance


def test_xdg_config_home(temp_dir: Path) -> None:
    """Test that the registry uses the XDG_CONFIG_HOME environment variable."""
    # Mock get_user_config_dir to directly return the expected path
    config_dir = temp_dir / "openai-model-registry"

    with (
        patch.dict(
            os.environ,
            {"XDG_CONFIG_HOME": str(temp_dir)},
            clear=True,
        ),
        patch(
            "openai_model_registry.config_paths.get_user_config_dir",
            return_value=config_dir,
        ),
    ):
        # Ensure directory doesn't exist yet
        assert not config_dir.exists()

        # Create empty registry instance to trigger directory creation
        registry = ModelRegistry.get_default()
        assert registry is not None
        assert config_dir.exists()


def test_xdg_config_home_with_existing_config(temp_dir: Path) -> None:
    """Test that the registry uses existing config files in XDG_CONFIG_HOME."""
    # Create XDG config directory structure
    app_config_dir = temp_dir / "openai-model-registry"
    app_config_dir.mkdir(parents=True)

    # Create minimal config files
    registry_path = app_config_dir / "models.yaml"
    registry_content = {
        "version": "1.0.0",
        "models": {
            "test-model": {
                "openai_name": "test-model",
                "context_window": 4096,
                "max_output_tokens": 2048,
                "supports_streaming": True,
                "supports_structured": True,
                "parameters": {
                    "temperature": {
                        "constraint": "temperature",
                        "description": "Controls randomness",
                    }
                },
            }
        },
    }

    with open(registry_path, "w") as f:
        f.write(str(registry_content))

    constraints_path = app_config_dir / PARAM_CONSTRAINTS_FILENAME
    constraints_content = {
        "temperature": {
            "type": "numeric",
            "min": 0.0,
            "max": 2.0,
            "description": "Controls randomness",
        }
    }

    with open(constraints_path, "w") as f:
        f.write(str(constraints_content))

    # Test with XDG environment variables
    with (
        patch.dict(
            os.environ,
            {
                "XDG_CONFIG_HOME": str(temp_dir),
                "OMR_MODEL_REGISTRY_PATH": str(registry_path),
                "OMR_PARAMETER_CONSTRAINTS_PATH": str(constraints_path),
                "OMR_DISABLE_DATA_UPDATES": "1",
            },
            clear=True,
        ),
    ):
        # Get default registry to test path resolution
        registry = ModelRegistry.get_default()
        assert registry is not None

        # Verify the registry loaded successfully (DataManager handles model path resolution)
        assert registry.config.constraints_path == str(constraints_path)

        # Verify that models were loaded successfully
        assert len(registry.models) > 0


def test_custom_registry_config() -> None:
    """Test creating a registry with a custom configuration."""
    # Create a custom configuration
    config = RegistryConfig(
        registry_path="/custom/path/registry.yml",
        constraints_path="/custom/path/constraints.yml",
        auto_update=True,
        cache_size=500,
    )

    # Create registry with custom config
    registry = ModelRegistry(config)

    # Verify config was properly set
    assert registry.config.registry_path == "/custom/path/registry.yml"
    assert registry.config.constraints_path == "/custom/path/constraints.yml"
    assert registry.config.auto_update is True
    assert registry.config.cache_size == 500

    # Ensure this is not the default instance
    assert registry is not ModelRegistry.get_default()


def test_env_var_override() -> None:
    """Test that environment variables override default paths."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create temporary files
        registry_path = os.path.join(temp_dir, "registry.yml")
        constraints_path = os.path.join(temp_dir, "constraints.yml")

        # Create minimal valid files
        with open(registry_path, "w") as f:
            f.write(
                "version: 2.0.0\nmodels:\n  test-model:\n    context_window: 1000\n    capabilities: {}\n    deprecation: {status: active}\n"
            )

        with open(constraints_path, "w") as f:
            f.write("numeric_constraints:\n  temperature:\n    type: numeric\n    min_value: 0.0\n    max_value: 2.0\n")

        with patch.dict(
            os.environ,
            {
                "OMR_MODEL_REGISTRY_PATH": registry_path,
                "OMR_PARAMETER_CONSTRAINTS_PATH": constraints_path,
                "OMR_DISABLE_DATA_UPDATES": "1",
            },
        ):
            # Reset singleton
            ModelRegistry._default_instance = None

            # Get default registry with default config (which should use env vars)
            registry = ModelRegistry.get_default()

            # Verify constraints path from env var was used (DataManager handles model path)
            assert registry.config.constraints_path == constraints_path

            # Verify that registry loaded successfully
            assert registry is not None
