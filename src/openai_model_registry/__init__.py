"""Registry for OpenAI model capabilities and version validation.

This package provides a centralized registry for managing OpenAI model capabilities,
including context windows, token limits, and supported features. It handles
both model aliases and dated versions, with version validation and fallback support.
"""

# Version of the package
__version__ = "1.0.0"

# Import main components for easier access
from .constraints import (
    EnumConstraint,
    NumericConstraint,
    ParameterReference,
)
from .errors import (
    InvalidDateError,
    ModelNotSupportedError,
    ModelVersionError,
    OpenAIClientError,
    TokenParameterError,
    VersionTooOldError,
)
from .model_version import ModelVersion
from .registry import (
    ModelCapabilities,
    ModelRegistry,
    RegistryUpdateResult,
    RegistryUpdateStatus,
    get_registry,
)

# Define public API
__all__ = [
    # Core registry
    "ModelRegistry",
    "ModelCapabilities",
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
    "OpenAIClientError",
    "ModelNotSupportedError",
    "ModelVersionError",
    "InvalidDateError",
    "VersionTooOldError",
    "TokenParameterError",
]
