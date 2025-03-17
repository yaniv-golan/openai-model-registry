"""Error types for the OpenAI model registry.

This module defines the error types used by the model registry
for various validation and compatibility issues.
"""

from typing import Any, Dict, List, Optional, Set, Union


class ModelRegistryError(Exception):
    """Base class for all registry-related errors.

    This is the parent class for all registry-specific exceptions.
    """

    pass


class ConfigurationError(ModelRegistryError):
    """Base class for configuration-related errors.

    This is raised for errors related to configuration loading, parsing,
    or validation.
    """

    def __init__(self, message: str, path: Optional[str] = None) -> None:
        """Initialize configuration error.

        Args:
            message: Error message
            path: Optional path to the configuration file that caused the error
        """
        super().__init__(message)
        self.message = message
        self.path = path


class ConfigFileNotFoundError(ConfigurationError):
    """Raised when a required configuration file is not found.

    Examples:
        >>> try:
        ...     registry._load_config()
        ... except ConfigFileNotFoundError as e:
        ...     print(f"Config file not found: {e.path}")
    """

    pass


class InvalidConfigFormatError(ConfigurationError):
    """Raised when a configuration file has an invalid format.

    Examples:
        >>> try:
        ...     registry._load_config()
        ... except InvalidConfigFormatError as e:
        ...     print(f"Invalid config format: {e}")
    """

    def __init__(
        self,
        message: str,
        path: Optional[str] = None,
        expected_type: str = "dict",
    ) -> None:
        """Initialize invalid format error.

        Args:
            message: Error message
            path: Optional path to the configuration file
            expected_type: Expected type of the configuration
        """
        super().__init__(message, path)
        self.expected_type = expected_type


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
        """Initialize invalid date error.

        Args:
            message: Error message explaining the date format issue
        """
        super().__init__(message)
        self.message = message


class ModelFormatError(ModelRegistryError):
    """Raised when a model name has an invalid format.

    Examples:
        >>> try:
        ...     ModelVersion.parse_from_model("invalid-model-name")
        ... except ModelFormatError as e:
        ...     print(f"Invalid model format: {e.model}")
    """

    def __init__(self, message: str, model: str) -> None:
        """Initialize model format error.

        Args:
            message: Error message
            model: The invalid model name
        """
        super().__init__(message)
        self.message = message
        self.model = model


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
        """Initialize version too old error.

        Args:
            message: Error message
            model: The model that has a version too old
            min_version: The minimum supported version
            alias: Suggested alias to use instead (if available)
        """
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
        available_models: Optional[
            Union[List[str], Set[str], Dict[str, Any]]
        ] = None,
    ) -> None:
        """Initialize model not supported error.

        Args:
            message: Error message
            model: The unsupported model name
            available_models: List of available models (optional)
        """
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
        """Return string representation of the error.

        Returns:
            Error message
        """
        return self.message


class ParameterValidationError(ModelRegistryError):
    """Base class for parameter validation errors.

    This is raised for errors related to parameter validation.
    """

    def __init__(
        self,
        message: str,
        param_name: str,
        value: Any,
        model: Optional[str] = None,
    ) -> None:
        """Initialize parameter validation error.

        Args:
            message: Error message
            param_name: The name of the parameter being validated
            value: The value that failed validation
            model: Optional model name for context
        """
        super().__init__(message)
        self.message = message
        self.param_name = param_name
        self.value = value
        self.model = model


class ParameterNotSupportedError(ParameterValidationError):
    """Raised when a parameter is not supported for a model.

    Examples:
        >>> try:
        ...     capabilities.validate_parameter("unknown_param", "value")
        ... except ParameterNotSupportedError as e:
        ...     print(f"Parameter {e.param_name} not supported for {e.model}")
    """

    pass


class ConstraintNotFoundError(ModelRegistryError):
    """Raised when a constraint reference cannot be found.

    Examples:
        >>> try:
        ...     registry.get_parameter_constraint("unknown.constraint")
        ... except ConstraintNotFoundError as e:
        ...     print(f"Constraint not found: {e.ref}")
    """

    def __init__(self, message: str, ref: str) -> None:
        """Initialize constraint not found error.

        Args:
            message: Error message
            ref: The constraint reference that wasn't found
        """
        super().__init__(message)
        self.message = message
        self.ref = ref


class TokenParameterError(ParameterValidationError):
    """Raised when there's an issue with token-related parameters.

    This error is used for issues with max_tokens, completion_tokens, etc.

    Examples:
        >>> try:
        ...     capabilities.validate_parameter("max_completion_tokens", 100000)
        ... except TokenParameterError as e:
        ...     print(f"Token error: {e}")
    """

    pass


class NetworkError(ModelRegistryError):
    """Raised when a network operation fails.

    Examples:
        >>> try:
        ...     registry.refresh_from_remote()
        ... except NetworkError as e:
        ...     print(f"Network error: {e}")
    """

    def __init__(self, message: str, url: Optional[str] = None) -> None:
        """Initialize network error.

        Args:
            message: Error message
            url: Optional URL that was being accessed
        """
        super().__init__(message)
        self.message = message
        self.url = url
