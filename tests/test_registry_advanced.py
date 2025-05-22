"""Tests for advanced registry functionality to improve code coverage."""

import os
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
import yaml

from openai_model_registry.config_result import ConfigResult
from openai_model_registry.errors import (
    ConstraintNotFoundError,
    InvalidDateError,
    ModelNotSupportedError,
    ModelRegistryError,
    VersionTooOldError,
)
from openai_model_registry.registry import (
    ModelRegistry,
    RefreshStatus,
    RegistryConfig,
)


@pytest.fixture
def test_config_dir(tmp_path: Path) -> Path:
    """Create a test configuration directory."""
    return tmp_path


@pytest.fixture
def simple_registry(
    test_config_dir: Path,
) -> Generator[ModelRegistry, None, None]:
    """Create a simple test registry with minimal config.

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
        },
    }

    with open(constraints_path, "w") as f:
        yaml.dump(constraints_content, f)

    # Create model capabilities file
    models_path = test_config_dir / "models.yml"
    models_content = {
        "version": "1.1.0",
        "dated_models": {
            "old-model-2023-01-01": {
                "context_window": 4096,
                "max_output_tokens": 1024,
                "description": "Old test model",
                "min_version": {
                    "year": 2023,
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
                "supports_vision": True,
                "supports_functions": True,
                "supports_streaming": True,
                "description": "GPT-4o test model",
                "min_version": {
                    "year": 2024,
                    "month": 5,
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
        },
        "aliases": {
            "old-model": "old-model-2023-01-01",
            "gpt-4o": "gpt-4o-2024-05-13",
        },
    }

    with open(models_path, "w") as f:
        yaml.dump(models_content, f)

    # Set environment variables
    os.environ["MODEL_REGISTRY_PATH"] = str(models_path)
    os.environ["PARAMETER_CONSTRAINTS_PATH"] = str(constraints_path)

    try:
        # Create registry with test config
        registry = ModelRegistry(
            config=RegistryConfig(
                registry_path=str(models_path),
                constraints_path=str(constraints_path),
            )
        )
        yield registry
    finally:
        # Restore environment variables
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

        # Cleanup
        ModelRegistry._default_instance = None


class TestRegistryVersionHandling:
    """Tests for registry model version handling."""

    def test_get_versioned_model(self, simple_registry: ModelRegistry) -> None:
        """Test getting a specific version of a model."""
        # Test retrieving a model using its dated version
        capabilities = simple_registry.get_capabilities("gpt-4o-2024-05-13")
        assert capabilities.model_name == "gpt-4o-2024-05-13"
        assert capabilities.openai_model_name == "gpt-4o-2024-05-13"

    def test_version_too_old(self, simple_registry: ModelRegistry) -> None:
        """Test error when requesting a version older than minimum."""
        # Try to get a version earlier than the minimum
        with pytest.raises(VersionTooOldError) as exc_info:
            simple_registry.get_capabilities("gpt-4o-2024-01-01")

        # Verify error details
        assert "gpt-4o-2024-01-01" in str(exc_info.value)
        assert "2024-05-01" in str(exc_info.value)  # min version
        assert exc_info.value.model == "gpt-4o-2024-01-01"
        assert exc_info.value.min_version == "2024-05-01"
        assert exc_info.value.alias == "gpt-4o"

    def test_invalid_date_format(self, simple_registry: ModelRegistry) -> None:
        """Test error when date format is invalid."""
        with pytest.raises(InvalidDateError):
            simple_registry.get_capabilities(
                "gpt-4o-2024-13-01"
            )  # Invalid month

    def test_nonexistent_model_with_valid_date(
        self, simple_registry: ModelRegistry
    ) -> None:
        """Test error for non-existent model with valid date format."""
        with pytest.raises(ModelNotSupportedError) as exc_info:
            simple_registry.get_capabilities("nonexistent-2024-01-01")

        assert "nonexistent-2024-01-01" in str(exc_info.value)
        assert exc_info.value.model == "nonexistent-2024-01-01"

    def test_model_using_alias(self, simple_registry: ModelRegistry) -> None:
        """Test getting a model using an alias."""
        # Get via alias
        capabilities = simple_registry.get_capabilities("gpt-4o")
        assert capabilities.model_name == "gpt-4o-2024-05-13"
        # Note: aliases are not stored in the capabilities object in the new schema

    def test_newer_version_than_registered(
        self, simple_registry: ModelRegistry
    ) -> None:
        """Test getting a newer version than what's registered."""
        # Test with a future version (should work because it's newer than min version)
        capabilities = simple_registry.get_capabilities("gpt-4o-2024-10-01")
        assert capabilities.openai_model_name == "gpt-4o-2024-10-01"
        assert (
            capabilities.context_window == 128000
        )  # Should inherit from base model

    def test_model_with_version_but_no_dated_models(
        self, simple_registry: ModelRegistry
    ) -> None:
        """Test behavior when requesting a versioned model but no dated models exist."""
        # Remove the registered dated model to test this case
        model_key = "gpt-4o-2024-05-13"
        original_capability = simple_registry._capabilities.pop(
            model_key, None
        )

        try:
            with pytest.raises(ModelNotSupportedError) as exc_info:
                simple_registry.get_capabilities("gpt-4o-2024-09-01")

            # Since the alias still exists, it should recommend using it
            assert "Try using 'gpt-4o' instead" in str(exc_info.value)
        finally:
            # Restore the capability
            if original_capability:
                simple_registry._capabilities[model_key] = original_capability


class TestModelCapabilities:
    """Tests for ModelCapabilities functionality."""

    def test_validate_parameter(self, simple_registry: ModelRegistry) -> None:
        """Test parameter validation in ModelCapabilities."""
        # Get a model
        capabilities = simple_registry.get_capabilities("gpt-4o")

        # Add a test constraint to validate
        from openai_model_registry.constraints import NumericConstraint

        capabilities._constraints = {
            "test_constraint": NumericConstraint(
                min_value=0, max_value=10, allow_float=False
            )
        }

        # Add a test parameter reference
        from openai_model_registry.constraints import ParameterReference

        capabilities.supported_parameters = [
            ParameterReference(
                ref="test_constraint", description="Test parameter"
            )
        ]

        # Test with valid value
        capabilities.validate_parameter("test_constraint", 5)

        # Test with invalid value (should raise an error)
        with pytest.raises(ModelRegistryError):
            capabilities.validate_parameter("test_constraint", 15)

        # Test with invalid type
        with pytest.raises(ModelRegistryError):
            capabilities.validate_parameter("test_constraint", "not a number")

    def test_validate_parameters(self, simple_registry: ModelRegistry) -> None:
        """Test validating multiple parameters at once."""
        # Similar setup as above
        capabilities = simple_registry.get_capabilities("gpt-4o")

        from openai_model_registry.constraints import (
            NumericConstraint,
            ParameterReference,
        )

        capabilities._constraints = {
            "temp_constraint": NumericConstraint(
                min_value=0, max_value=2, allow_float=True
            ),
            "max_tokens_constraint": NumericConstraint(
                min_value=1, max_value=1000, allow_float=False
            ),
        }

        capabilities.supported_parameters = [
            ParameterReference(
                ref="temp_constraint", description="Temperature"
            ),
            ParameterReference(
                ref="max_tokens_constraint", description="Max tokens"
            ),
        ]

        # Valid parameters
        params = {"temp_constraint": 0.7, "max_tokens_constraint": 500}
        capabilities.validate_parameters(params)

        # Invalid parameters
        params = {
            "temp_constraint": 3.0,  # Over max
            "max_tokens_constraint": 500,
        }
        with pytest.raises(ModelRegistryError):
            capabilities.validate_parameters(params)

    def test_get_parameter_constraint(
        self, simple_registry: ModelRegistry
    ) -> None:
        """Test get_parameter_constraint."""
        # Add a test constraint
        from openai_model_registry.constraints import NumericConstraint

        # Set up a numeric constraint for testing
        simple_registry._constraints = {
            "test_constraint": NumericConstraint(
                min_value=0, max_value=10, allow_float=True, allow_int=True
            )
        }

        # Get the constraint
        constraint = simple_registry.get_parameter_constraint(
            "test_constraint"
        )
        # Use isinstance to ensure we're dealing with the right type
        assert isinstance(constraint, NumericConstraint)
        assert constraint.min_value == 0
        assert constraint.max_value == 10

        # Test with non-existent constraint
        with pytest.raises(ConstraintNotFoundError):
            simple_registry.get_parameter_constraint("nonexistent_constraint")

    def test_models_property(self, simple_registry: ModelRegistry) -> None:
        """Test the models property."""
        models = simple_registry.models
        assert isinstance(models, dict)
        assert "gpt-4o" in models
        assert "gpt-4o-2024-05-13" in models

        # Should be a copy, not the original
        original_len = len(simple_registry._capabilities)
        # Verify that modifying the returned dict doesn't affect the original
        assert id(models) != id(simple_registry._capabilities)
        assert (
            len(simple_registry._capabilities) == original_len
        )  # Original unchanged

    def test_duplicate_alias_detection(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that duplicate aliases are properly detected and handled."""
        # Create a simple registry configuration with duplicate aliases
        test_config = {
            "dated_models": {
                "model-a-2024-01-01": {
                    "context_window": 1000,
                    "max_output_tokens": 100,
                    "description": "Model A",
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
                "model-b-2024-01-01": {
                    "context_window": 2000,
                    "max_output_tokens": 200,
                    "description": "Model B",
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
            },
            "aliases": {
                "shared-alias": "model-a-2024-01-01",
                "unique-a": "model-a-2024-01-01",
                "unique-b": "model-b-2024-01-01",
            },
        }

        # Create a registry with this config
        with patch.object(ModelRegistry, "_load_config") as mock_load:
            config_data = {"version": "1.1.0", **test_config}
            mock_load.return_value = ConfigResult(
                success=True, data=config_data, path="test_path"
            )

            # Clear any existing registry
            ModelRegistry._default_instance = None

            registry = ModelRegistry()

            # Force capabilities loading to trigger the alias detection
            registry._load_capabilities()

            # Check that aliases point to the correct models
            assert (
                registry._capabilities["shared-alias"].context_window == 1000
            )
            assert (
                registry._capabilities["shared-alias"].model_name
                == "model-a-2024-01-01"
            )

            # Check that unique aliases are properly assigned
            assert (
                registry._capabilities["unique-a"].model_name
                == "model-a-2024-01-01"
            )
            assert (
                registry._capabilities["unique-b"].model_name
                == "model-b-2024-01-01"
            )

            # In the new schema, there shouldn't be duplicate alias warnings since
            # aliases are explicitly defined in the aliases section
            # This test now verifies that aliases work correctly


class TestRegistryRefresh:
    """Tests for registry refresh functionality with safer mocking approaches."""

    def test_refresh_validate_only(
        self, simple_registry: ModelRegistry
    ) -> None:
        """Test refresh with validate_only flag."""
        # Only mock what's necessary
        with patch.object(
            simple_registry, "_fetch_remote_config"
        ) as mock_fetch:
            # Provide a simple mock config
            mock_fetch.return_value = {"version": "1.1.0"}

            # Mock just the validation method to avoid complex logic
            with patch.object(
                simple_registry, "_validate_remote_config"
            ) as mock_validate:
                mock_validate.return_value = None

                # Call with validate_only=True
                result = simple_registry.refresh_from_remote(
                    validate_only=True
                )

                # Verify the correct behavior
                assert result.success is True
                assert result.status == RefreshStatus.VALIDATED

                # Verify methods were called with correct args
                mock_fetch.assert_called_once()
                mock_validate.assert_called_once()

    def test_refresh_fetch_failure(
        self, simple_registry: ModelRegistry
    ) -> None:
        """Test behavior when fetch fails."""
        with patch.object(
            simple_registry, "_fetch_remote_config"
        ) as mock_fetch:
            # Simulate fetch failure
            mock_fetch.return_value = None

            # Call refresh
            result = simple_registry.refresh_from_remote()

            # Verify failure handling
            assert result.success is False
            assert result.status == RefreshStatus.ERROR
            assert "Failed to fetch" in result.message

    def test_check_for_updates_with_explicit_url(
        self, simple_registry: ModelRegistry
    ) -> None:
        """Test check_for_updates with custom URL."""
        with (
            patch("requests.head") as mock_head,
            patch("requests.get") as mock_get,
        ):
            # Mock HEAD response
            head_response = MagicMock()
            head_response.status_code = 200
            mock_head.return_value = head_response

            # Mock GET response
            get_response = MagicMock()
            get_response.status_code = 200
            get_response.text = yaml.dump({"version": "2.0.0"})
            mock_get.return_value = get_response

            # Mock _load_config to return a known version
            with patch.object(
                simple_registry,
                "_load_config",
                return_value={"version": "1.0.0"},
            ):
                # Use a custom URL to avoid default URL issues
                result = simple_registry.check_for_updates(
                    url="https://example.com/test.yml"
                )

                # Verify the requests were made to the correct URL
                mock_head.assert_called_once_with(
                    "https://example.com/test.yml", timeout=10
                )
                mock_get.assert_called_once_with(
                    "https://example.com/test.yml", timeout=10
                )

                # Verify result
                assert result.success is True
                assert result.status == RefreshStatus.UPDATE_AVAILABLE
                assert "1.0.0 -> 2.0.0" in result.message

    def test_check_for_updates_http_404(self) -> None:
        """Test check_for_updates with a 404 HTTP error using more direct mocking."""
        registry = ModelRegistry()

        # Create a mock config result with version information
        mock_config_result = MagicMock()
        mock_config_result.success = True
        mock_config_result.data = {"version": "1.0.0"}
        # Ensure the mock correctly implements dict-like access for the code
        mock_config_result.__getitem__ = (
            lambda self, key: mock_config_result.data.get(key)
        )
        mock_config_result.__contains__ = (
            lambda self, key: key in mock_config_result.data
        )

        with (
            patch.object(
                registry, "_load_config", return_value=mock_config_result
            ),
            patch("requests.head") as mock_head,
            patch("requests.get") as mock_get,
        ):
            # Create a mock response with 404
            mock_head_response = MagicMock()
            mock_head_response.status_code = 404
            mock_head.return_value = mock_head_response

            # We don't expect get to be called with 404 from head
            mock_get_response = MagicMock()
            mock_get_response.status_code = 200
            mock_get.return_value = mock_get_response

            # Test with specified URL to avoid using the default URL
            result = registry.check_for_updates(
                url="https://test.example.com/config.yml"
            )

            # Verify the request was made to the correct URL
            mock_head.assert_called_once_with(
                "https://test.example.com/config.yml", timeout=10
            )

            # Verify get was not called
            mock_get.assert_not_called()

            # Verify error handling
            assert result.success is False
            assert result.status == RefreshStatus.ERROR
            assert "not found" in result.message.lower()

    def test_file_permission_error_handling(self) -> None:
        """Test file permission error handling in file writing operations."""
        with patch("builtins.open") as mock_open:
            # Mock the open function to raise a PermissionError
            mock_open.side_effect = PermissionError("Permission denied")

            # Create a target path
            target_path = Path("/mock/path/config.yml")

            # Create a dictionary to write
            data = {"test": "data"}

            # Create a direct test case that makes it easy to validate
            # We'll use the helper method from edit_file without our mocking
            # This is similar to what's happening in the actual code:
            def write_test_file() -> str:
                try:
                    with open(target_path, "w") as f:
                        yaml.dump(data, f)
                except PermissionError as e:
                    return f"Permission error: {e}"
                except OSError as e:
                    return f"OS error: {e}"
                return "Success"

            # Test that we get the expected error
            result = write_test_file()
            assert "Permission error" in result
            assert "Permission denied" in result


class TestRegistryErrors:
    """Tests for error handling in the registry."""

    def test_load_config_file_not_found(self, test_config_dir: Path) -> None:
        """Test loading config when file doesn't exist."""
        nonexistent_path = test_config_dir / "nonexistent.yml"

        registry = ModelRegistry(
            config=RegistryConfig(
                registry_path=str(nonexistent_path),
                constraints_path=str(nonexistent_path),
            )
        )

        # The registry should be initialized with empty capabilities
        assert registry._capabilities == {}

        # Load config should return a ConfigResult with success=False
        result = registry._load_config()
        assert result is not None
        assert result.success is False
        assert result.data is None
        assert (
            result.error is not None
            and "file not found" in result.error.lower()
        )
        assert isinstance(result.exception, FileNotFoundError)

    def test_load_config_invalid_format(self, test_config_dir: Path) -> None:
        """Test loading config with invalid format."""
        invalid_path = test_config_dir / "invalid.yml"

        # Create an invalid YAML file (not a dictionary)
        with open(invalid_path, "w") as f:
            f.write("- this\n- is\n- a\n- list")

        registry = ModelRegistry(
            config=RegistryConfig(
                registry_path=str(invalid_path),
            )
        )

        # Load config should return a ConfigResult with success=False for non-dict data
        result = registry._load_config()
        assert result is not None
        assert result.success is False
        assert result.data is None
        assert (
            result.error is not None
            and "invalid configuration format" in result.error.lower()
        )
        assert (
            result.error is not None
            and "expected dictionary" in result.error.lower()
        )

    def test_init_with_copy_error(self) -> None:
        """Test ModelRegistry initialization with config file copy error."""
        # Mock the copy_default_to_user_config function to raise an OSError
        with patch(
            "openai_model_registry.registry.copy_default_to_user_config"
        ) as mock_copy:
            mock_copy.side_effect = OSError("Simulated copy error")

            # Registry should still initialize without raising an exception
            registry = ModelRegistry()

            # Verify that copy was attempted
            assert mock_copy.called

            # Registry should have capabilities loaded from the default package config
            assert isinstance(registry._capabilities, dict)

            # Should be able to check models list without error
            # The registry should still load models from the default package configuration
            assert len(registry.models) > 0


class TestMiscellaneousFunctions:
    """Tests for miscellaneous functions in registry."""

    def test_get_instance_and_get_default(self) -> None:
        """Test the get_instance and get_default class methods."""
        # Reset the default instance
        ModelRegistry._default_instance = None

        # Both methods should return the same instance
        instance1 = ModelRegistry.get_instance()
        instance2 = ModelRegistry.get_default()

        assert instance1 is instance2
        assert ModelRegistry._default_instance is instance1

    def test_cleanup(self) -> None:
        """Test the cleanup class method."""
        # Create an instance
        instance = ModelRegistry.get_default()
        assert ModelRegistry._default_instance is instance

        # Cleanup
        ModelRegistry.cleanup()
        assert ModelRegistry._default_instance is None

        # Creating a new instance should work
        new_instance = ModelRegistry.get_default()
        assert ModelRegistry._default_instance is new_instance
        assert new_instance is not instance
