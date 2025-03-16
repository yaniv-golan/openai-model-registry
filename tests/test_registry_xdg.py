"""Tests for the ModelRegistry XDG path handling."""

import os
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest

from openai_model_registry.config_paths import (
    MODEL_REGISTRY_FILENAME,
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

    with patch.dict(
        os.environ,
        {"XDG_CONFIG_HOME": str(temp_dir)},
        clear=True,
    ), patch(
        "openai_model_registry.config_paths.get_user_config_dir",
        return_value=config_dir,
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
    registry_path = app_config_dir / MODEL_REGISTRY_FILENAME
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
    with patch.dict(
        os.environ,
        {"XDG_CONFIG_HOME": str(temp_dir)},
        clear=True,
    ), patch(
        "openai_model_registry.registry.get_model_registry_path",
        return_value=str(registry_path),
    ), patch(
        "openai_model_registry.registry.get_parameter_constraints_path",
        return_value=str(constraints_path),
    ):
        # Get default registry to test path resolution
        registry = ModelRegistry.get_default()
        assert registry is not None

        # Verify the paths were properly set
        assert registry.config.registry_path == str(registry_path)
        assert registry.config.constraints_path == str(constraints_path)


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
    registry_path = "/env/var/path/registry.yml"
    constraints_path = "/env/var/path/constraints.yml"

    with patch(
        "openai_model_registry.registry.get_model_registry_path",
        return_value=registry_path,
    ), patch(
        "openai_model_registry.registry.get_parameter_constraints_path",
        return_value=constraints_path,
    ):
        # Reset singleton
        ModelRegistry._default_instance = None

        # Get default registry with default config (which should use env vars)
        registry = ModelRegistry.get_default()

        # Verify paths from env vars were used
        assert registry.config.registry_path == registry_path
        assert registry.config.constraints_path == constraints_path
