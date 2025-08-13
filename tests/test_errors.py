"""Tests for error classes."""

from typing import Dict

from openai_model_registry.errors import (
    InvalidDateError,
    ModelNotSupportedError,
    ModelRegistryError,
    ModelVersionError,
    TokenParameterError,
    VersionTooOldError,
)


class TestErrorClasses:
    """Tests for all error classes."""

    def test_model_registry_error(self) -> None:
        """Test ModelRegistryError base class."""
        error = ModelRegistryError("Base error message")
        assert str(error) == "Base error message"

    def test_model_version_error(self) -> None:
        """Test ModelVersionError."""
        error = ModelVersionError("Version error message")
        assert str(error) == "Version error message"
        assert isinstance(error, ModelRegistryError)

    def test_invalid_date_error(self) -> None:
        """Test InvalidDateError."""
        error = InvalidDateError("Invalid date format")
        assert error.message == "Invalid date format"
        assert str(error) == "Invalid date format"
        assert isinstance(error, ModelVersionError)

    def test_version_too_old_error(self) -> None:
        """Test VersionTooOldError."""
        error = VersionTooOldError(
            "Version too old",
            model="gpt-4o-2023-01-01",
            min_version="2023-05-01",
            alias="gpt-4o",
        )

        assert error.message == "Version too old"
        assert error.model == "gpt-4o-2023-01-01"
        assert error.min_version == "2023-05-01"
        assert error.alias == "gpt-4o"
        assert isinstance(error, ModelVersionError)

        # Test without alias
        error_no_alias = VersionTooOldError(
            "Version too old",
            model="gpt-4o-2023-01-01",
            min_version="2023-05-01",
        )
        assert error_no_alias.alias is None

    def test_model_not_supported_error(self) -> None:
        """Test ModelNotSupportedError."""
        # Basic case
        error = ModelNotSupportedError("Model not supported")
        assert error.message == "Model not supported"
        assert error.model is None
        assert error.available_models is None
        assert str(error) == "Model not supported"

        # With model name
        error = ModelNotSupportedError("Model not supported", model="unsupported-model")
        assert error.model == "unsupported-model"

        # With available models as list
        models_list = ["gpt-4", "gpt-3.5-turbo"]
        error = ModelNotSupportedError(
            "Model not supported",
            model="unsupported-model",
            available_models=models_list,
        )
        assert isinstance(error.available_models, list)
        if error.available_models:  # Type guard
            assert "gpt-4" in error.available_models
            assert "gpt-3.5-turbo" in error.available_models

        # With available models as dict
        models_dict: Dict[str, str] = {
            "gpt-4": "description",
            "gpt-3.5-turbo": "description",
        }
        error = ModelNotSupportedError(
            "Model not supported",
            model="unsupported-model",
            available_models=list(models_dict.keys()),  # Convert dict keys to list
        )
        assert isinstance(error.available_models, list)
        if error.available_models:  # Type guard
            assert "gpt-4" in error.available_models
            assert "gpt-3.5-turbo" in error.available_models

    def test_token_parameter_error(self) -> None:
        """Test TokenParameterError."""
        error = TokenParameterError("Invalid token parameter", param_name="max_tokens", value=100000)

        assert error.message == "Invalid token parameter"
        assert error.param_name == "max_tokens"
        assert error.value == 100000
        assert isinstance(error, ModelRegistryError)
