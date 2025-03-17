"""Error types for the OpenAI model registry.

This module defines the error types used by the model registry
for various validation and compatibility issues.
"""

from typing import Any, List, Optional


class ModelRegistryError(Exception):
    """Base class for all registry-related errors.

    This is the parent class for all registry-specific exceptions.
    """

    pass


class ModelVersionError(ModelRegistryError):
    """Base class for version-related errors.

    This is raised for any errors related to model versions.
    """

    pass


class InvalidDateError(ModelVersionError):
    """Raised when a model version has an invalid date format.

    Examples:
        >>> try:
        ...     ModelVersion.from_string("2024-13-01")
        ... except InvalidDateError as e:
        ...     print(f"Date format error: {e}")
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class VersionTooOldError(ModelVersionError):
    """Raised when a model version is older than the minimum supported version.

    Examples:
        >>> try:
        ...     registry.get_capabilities("gpt-4o-2024-07-01")
        ... except VersionTooOldError as e:
        ...     print(f"Version error: {e}")
        ...     print(f"Try using the alias: {e.alias}")
    """

    def __init__(
        self,
        message: str,
        model: str,
        min_version: str,
        alias: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.model = model
        self.min_version = min_version
        self.alias = alias


class ModelNotSupportedError(ModelRegistryError):
    """Raised when a model is not supported by the registry.

    This error indicates that the requested model is not in the registry of
    supported models. This is different from version-related errors, which
    indicate that the model exists but the specific version is invalid.

    Examples:
        >>> try:
        ...     registry.get_capabilities("unsupported-model")
        ... except ModelNotSupportedError as e:
        ...     print(f"Model {e.model} is not supported")
    """

    def __init__(
        self,
        message: str,
        model: Optional[str] = None,
        available_models: Optional[List[str]] = None,
    ) -> None:
        super().__init__(message)
        self.model = model
        self.message = message
        # Convert other collection types to list for consistency
        if available_models is not None:
            if isinstance(available_models, dict):
                self.available_models: Optional[List[str]] = list(
                    available_models.keys()
                )
            elif isinstance(available_models, set):
                self.available_models = list(available_models)
            else:
                self.available_models = available_models
        else:
            self.available_models = None

    def __str__(self) -> str:
        return self.message


class TokenParameterError(ModelRegistryError):
    """Raised when there's an issue with token-related parameters.

    This error is used for issues with max_tokens, completion_tokens, etc.

    Examples:
        >>> try:
        ...     capabilities.validate_parameter("max_completion_tokens", 100000)
        ... except TokenParameterError as e:
        ...     print(f"Token error: {e}")
    """

    def __init__(self, message: str, param_name: str, value: Any) -> None:
        super().__init__(message)
        self.message = message
        self.param_name = param_name
        self.value = value
