"""Tests for the RegistryConfig class."""

import os
from unittest.mock import patch

from openai_model_registry.registry import RegistryConfig


def test_registry_config_initialization() -> None:
    """Test RegistryConfig initialization with default values."""
    # Test with default values
    with patch(
        "openai_model_registry.registry.get_model_registry_path",
        return_value="/default/registry.yml",
    ), patch(
        "openai_model_registry.registry.get_parameter_constraints_path",
        return_value="/default/constraints.yml",
    ):
        config = RegistryConfig()
        assert config.registry_path == "/default/registry.yml"
        assert config.constraints_path == "/default/constraints.yml"
        assert config.auto_update is False
        assert config.cache_size == 100


def test_registry_config_custom_values() -> None:
    """Test RegistryConfig initialization with custom values."""
    config = RegistryConfig(
        registry_path="/custom/registry.yml",
        constraints_path="/custom/constraints.yml",
        auto_update=True,
        cache_size=500,
    )
    assert config.registry_path == "/custom/registry.yml"
    assert config.constraints_path == "/custom/constraints.yml"
    assert config.auto_update is True
    assert config.cache_size == 500


def test_registry_config_mixed_values() -> None:
    """Test RegistryConfig initialization with mixed custom and default values."""
    with patch(
        "openai_model_registry.registry.get_model_registry_path",
        return_value="/default/registry.yml",
    ), patch(
        "openai_model_registry.registry.get_parameter_constraints_path",
        return_value="/default/constraints.yml",
    ):
        config = RegistryConfig(registry_path="/custom/registry.yml")
        assert config.registry_path == "/custom/registry.yml"
        assert config.constraints_path == "/default/constraints.yml"
        assert config.auto_update is False
        assert config.cache_size == 100


def test_registry_config_with_env_vars() -> None:
    """Test RegistryConfig with environment variables."""
    with patch.dict(
        os.environ,
        {
            "MODEL_REGISTRY_PATH": "/env/registry.yml",
            "PARAMETER_CONSTRAINTS_PATH": "/env/constraints.yml",
        },
    ), patch(
        "openai_model_registry.registry.get_model_registry_path",
        return_value="/env/registry.yml",
    ), patch(
        "openai_model_registry.registry.get_parameter_constraints_path",
        return_value="/env/constraints.yml",
    ):
        config = RegistryConfig()
        assert config.registry_path == "/env/registry.yml"
        assert config.constraints_path == "/env/constraints.yml"


def test_custom_config_overrides_env_vars() -> None:
    """Test that custom config values override environment variables."""
    with patch.dict(
        os.environ,
        {
            "MODEL_REGISTRY_PATH": "/env/registry.yml",
            "PARAMETER_CONSTRAINTS_PATH": "/env/constraints.yml",
        },
    ):
        config = RegistryConfig(
            registry_path="/custom/registry.yml",
            constraints_path="/custom/constraints.yml",
        )
        assert config.registry_path == "/custom/registry.yml"
        assert config.constraints_path == "/custom/constraints.yml"
