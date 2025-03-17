"""Registry for OpenAI model capabilities and version validation.

This package provides a centralized registry for managing OpenAI model capabilities,
including context windows, token limits, and supported features. It handles
both model aliases and dated versions, with version validation and fallback support.
"""

# Version of the package
try:
    from importlib.metadata import version as _version

    __version__ = _version("openai-model-registry")
except ImportError:
    # Require importlib.metadata which is standard in Python 3.8+
    raise ImportError(
        "Failed to determine package version. This package requires Python 3.8+ "
        "where importlib.metadata is available, or must be installed as a package."
    )

# Import main components for easier access
from .constraints import (
    EnumConstraint,
    NumericConstraint,
    ParameterReference,
)
from .errors import (
    ConfigFileNotFoundError,
    ConfigurationError,
    ConstraintNotFoundError,
    InvalidConfigFormatError,
    InvalidDateError,
    ModelFormatError,
    ModelNotSupportedError,
    ModelRegistryError,
    ModelVersionError,
    NetworkError,
    ParameterNotSupportedError,
    ParameterValidationError,
    TokenParameterError,
    VersionTooOldError,
)
from .logging import (
    LogEvent,
    get_logger,
)
from .model_version import ModelVersion
from .registry import (
    ModelCapabilities,
    ModelRegistry,
    RegistryConfig,
    RegistryUpdateResult,
    RegistryUpdateStatus,
    get_registry,
)

# Define public API
__all__ = [
    # Core registry
    "ModelRegistry",
    "ModelCapabilities",
    "RegistryConfig",
    "get_registry",
    # Version handling
    "ModelVersion",
    "RegistryUpdateStatus",
    "RegistryUpdateResult",
    # Constraints
    "NumericConstraint",
    "EnumConstraint",
    "ParameterReference",
    # Errors
    "ModelRegistryError",
    "ConfigurationError",
    "ConfigFileNotFoundError",
    "InvalidConfigFormatError",
    "ModelVersionError",
    "InvalidDateError",
    "ModelFormatError",
    "VersionTooOldError",
    "ParameterValidationError",
    "ParameterNotSupportedError",
    "TokenParameterError",
    "ConstraintNotFoundError",
    "NetworkError",
    "ModelNotSupportedError",
    # Logging
    "LogEvent",
    "get_logger",
]
