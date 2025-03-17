"""Core registry functionality for managing OpenAI model capabilities.

This module provides the ModelRegistry class, which is the central component
for managing model capabilities, version validation, and parameter constraints.
"""

import copy
import functools
import os
import re
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

import yaml
from packaging import version

from .config_paths import (
    MODEL_REGISTRY_FILENAME,
    PARAM_CONSTRAINTS_FILENAME,
    copy_default_to_user_config,
    ensure_user_config_dir_exists,
    get_model_registry_path,
    get_parameter_constraints_path,
    get_user_config_dir,
)
from .config_result import ConfigResult
from .constraints import (
    EnumConstraint,
    NumericConstraint,
    ParameterReference,
)
from .errors import (
    ConstraintNotFoundError,
    InvalidDateError,
    ModelNotSupportedError,
    ParameterNotSupportedError,
    VersionTooOldError,
)
from .logging import (
    LogEvent,
    get_logger,
    log_debug,
    log_error,
    log_info,
    log_warning,
)
from .model_version import ModelVersion

# Create module logger
logger = get_logger("registry")


class RegistryConfig:
    """Configuration for the model registry."""

    def __init__(
        self,
        registry_path: Optional[str] = None,
        constraints_path: Optional[str] = None,
        auto_update: bool = False,
        cache_size: int = 100,
    ):
        """Initialize registry configuration.

        Args:
            registry_path: Custom path to registry YAML file. If None,
                           default location is used.
            constraints_path: Custom path to constraints YAML file. If None,
                              default location is used.
            auto_update: Whether to automatically update the registry.
            cache_size: Size of model capabilities cache.
        """
        self.registry_path = registry_path or get_model_registry_path()
        self.constraints_path = (
            constraints_path or get_parameter_constraints_path()
        )
        self.auto_update = auto_update
        self.cache_size = cache_size


class RegistryUpdateStatus(Enum):
    """Status of a registry update operation."""

    UPDATED = "updated"
    ALREADY_CURRENT = "already_current"
    NOT_FOUND = "not_found"
    NETWORK_ERROR = "network_error"
    PERMISSION_ERROR = "permission_error"
    IMPORT_ERROR = "import_error"
    UNKNOWN_ERROR = "unknown_error"
    UPDATE_AVAILABLE = "update_available"


class RefreshStatus(Enum):
    """Status of a registry refresh operation."""

    UPDATED = "updated"
    ALREADY_CURRENT = "already_current"
    ERROR = "error"
    VALIDATED = "validated"
    UPDATE_AVAILABLE = "update_available"


@dataclass
class RegistryUpdateResult:
    """Result of a registry update operation."""

    success: bool
    status: RegistryUpdateStatus
    message: str
    url: Optional[str] = None
    error: Optional[Exception] = None


@dataclass
class RefreshResult:
    """Result of a registry refresh operation."""

    success: bool
    status: RefreshStatus
    message: str


class ModelCapabilities:
    """Represents the capabilities of a model."""

    def __init__(
        self,
        model_name: str,
        openai_model_name: str,
        context_window: int,
        max_output_tokens: int,
        supports_vision: bool = False,
        supports_functions: bool = False,
        supports_streaming: bool = False,
        supports_structured: bool = False,
        min_version: Optional[ModelVersion] = None,
        aliases: Optional[List[str]] = None,
        supported_parameters: Optional[List[ParameterReference]] = None,
        constraints: Optional[
            Dict[str, Union[NumericConstraint, EnumConstraint]]
        ] = None,
    ):
        """Initialize model capabilities.

        Args:
            model_name: The model identifier in the registry
            openai_model_name: The model name to use with OpenAI API
            context_window: Maximum context window size in tokens
            max_output_tokens: Maximum output tokens
            supports_vision: Whether the model supports vision inputs
            supports_functions: Whether the model supports function calling
            supports_streaming: Whether the model supports streaming
            supports_structured: Whether the model supports structured output
            min_version: Minimum version for dated model variants
            aliases: List of aliases for this model
            supported_parameters: List of parameter references supported by this model
            constraints: Dictionary of constraints for validation
        """
        self.model_name = model_name
        self.openai_model_name = openai_model_name
        self.context_window = context_window
        self.max_output_tokens = max_output_tokens
        self.supports_vision = supports_vision
        self.supports_functions = supports_functions
        self.supports_streaming = supports_streaming
        self.supports_structured = supports_structured
        self.min_version = min_version
        self.aliases = aliases or []
        self.supported_parameters = supported_parameters or []
        self._constraints = constraints or {}

    def get_constraint(
        self, ref: str
    ) -> Optional[Union[NumericConstraint, EnumConstraint]]:
        """Get a constraint by reference.

        Args:
            ref: Constraint reference (key in constraints dict)

        Returns:
            The constraint or None if not found
        """
        return self._constraints.get(ref)

    def validate_parameter(
        self, name: str, value: Any, used_params: Optional[Set[str]] = None
    ) -> None:
        """Validate a parameter against constraints.

        Args:
            name: Parameter name
            value: Parameter value to validate
            used_params: Optional set to track used parameters

        Raises:
            ParameterNotSupportedError: If the parameter is not supported
            ConstraintNotFoundError: If a constraint reference is invalid
            ModelRegistryError: If validation fails for other reasons
        """
        # Track used parameters if requested
        if used_params is not None:
            used_params.add(name)

        # Find matching parameter reference
        param_ref = next(
            (
                p
                for p in self.supported_parameters
                if p.ref.split(".")[-1] == name
            ),
            None,
        )

        if not param_ref:
            # If we're validating a parameter explicitly, it should be supported
            raise ParameterNotSupportedError(
                f"Parameter '{name}' is not supported for model '{self.model_name}'",
                param_name=name,
                value=value,
                model=self.model_name,
            )

        constraint = self.get_constraint(param_ref.ref)
        if not constraint:
            # If a parameter references a constraint, the constraint should exist
            raise ConstraintNotFoundError(
                f"Constraint reference '{param_ref.ref}' not found for parameter '{name}'",
                ref=param_ref.ref,
            )

        # Validate based on constraint type
        if isinstance(constraint, NumericConstraint):
            constraint.validate(name=name, value=value)
        elif isinstance(constraint, EnumConstraint):
            constraint.validate(name=name, value=value)
        else:
            # This shouldn't happen with proper type checking, but just in case
            raise TypeError(
                f"Unknown constraint type for '{name}': {type(constraint).__name__}"
            )

    def validate_parameters(
        self, params: Dict[str, Any], used_params: Optional[Set[str]] = None
    ) -> None:
        """Validate multiple parameters against constraints.

        Args:
            params: Dictionary of parameter names and values to validate
            used_params: Optional set to track used parameters

        Raises:
            ModelRegistryError: If validation fails for any parameter
        """
        for name, value in params.items():
            self.validate_parameter(name, value, used_params)


class ModelRegistry:
    """Registry for model capabilities and validation."""

    _default_instance: Optional["ModelRegistry"] = None
    # Pre-compile regex patterns for improved performance
    _DATE_PATTERN = re.compile(r"^(.*)-(\d{4}-\d{2}-\d{2})$")
    _IS_DATED_MODEL_PATTERN = re.compile(r".*-\d{4}-\d{2}-\d{2}$")
    _instance_lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "ModelRegistry":
        """Get the default registry instance with standard configuration.

        This method is maintained for backward compatibility.
        New code should use get_default() instead.

        Returns:
            The default ModelRegistry instance
        """
        return cls.get_default()

    @classmethod
    def get_default(cls) -> "ModelRegistry":
        """Get the default registry instance with standard configuration.

        Returns:
            The default ModelRegistry instance
        """
        with cls._instance_lock:
            if cls._default_instance is None:
                cls._default_instance = cls()
            return cls._default_instance

    def __init__(self, config: Optional[RegistryConfig] = None):
        """Initialize a new registry instance.

        Args:
            config: Configuration for this registry instance. If None, default
                   configuration is used.
        """
        self.config = config or RegistryConfig()
        self._capabilities: Dict[str, ModelCapabilities] = {}
        self._constraints: Dict[
            str, Union[NumericConstraint, EnumConstraint]
        ] = {}

        # Set up caching for get_capabilities
        self.get_capabilities = functools.lru_cache(
            maxsize=self.config.cache_size
        )(self._get_capabilities_impl)

        # Auto-copy default configs to user directory if they don't exist
        if not config or not config.registry_path:
            try:
                copy_default_to_user_config(MODEL_REGISTRY_FILENAME)
            except OSError as e:
                log_warning(
                    LogEvent.MODEL_REGISTRY,
                    f"Failed to copy default model registry config: {e}",
                    error=str(e),
                )

        if not config or not config.constraints_path:
            try:
                copy_default_to_user_config(PARAM_CONSTRAINTS_FILENAME)
            except OSError as e:
                log_warning(
                    LogEvent.MODEL_REGISTRY,
                    f"Failed to copy default constraint config: {e}",
                    error=str(e),
                )

        self._load_constraints()
        self._load_capabilities()

    def _load_config(self) -> ConfigResult:
        """Load model configuration from file.

        Returns:
            ConfigResult: Result of the configuration loading operation
        """
        try:
            with open(self.config.registry_path, "r") as f:
                data = yaml.safe_load(f)
                if not isinstance(data, dict):
                    error_msg = (
                        f"Invalid configuration format in {self.config.registry_path}: "
                        f"expected dictionary, got {type(data).__name__}"
                    )
                    log_error(
                        LogEvent.MODEL_REGISTRY,
                        error_msg,
                        path=self.config.registry_path,
                    )
                    return ConfigResult(
                        success=False,
                        error=error_msg,
                        path=self.config.registry_path,
                    )
                return ConfigResult(
                    success=True, data=data, path=self.config.registry_path
                )
        except FileNotFoundError as e:
            error_msg = f"Model registry config file not found: {self.config.registry_path}"
            log_warning(
                LogEvent.MODEL_REGISTRY,
                error_msg,
                path=self.config.registry_path,
            )
            return ConfigResult(
                success=False,
                error=error_msg,
                exception=e,
                path=self.config.registry_path,
            )
        except Exception as e:
            error_msg = f"Failed to load model registry config: {e}"
            log_error(
                LogEvent.MODEL_REGISTRY,
                error_msg,
                path=self.config.registry_path,
                error=str(e),
            )
            return ConfigResult(
                success=False,
                error=error_msg,
                exception=e,
                path=self.config.registry_path,
            )

    def _load_constraints(self) -> None:
        """Load parameter constraints from file."""
        try:
            with open(self.config.constraints_path, "r") as f:
                data = yaml.safe_load(f)
                if not isinstance(data, dict):
                    log_error(
                        LogEvent.MODEL_REGISTRY,
                        "Constraints file must contain a dictionary",
                    )
                    return

                # Create constraints from config
                for name, constraint in data.items():
                    if not isinstance(constraint, dict):
                        log_error(
                            LogEvent.MODEL_REGISTRY,
                            f"Constraint '{name}' must be a dictionary",
                            constraint=constraint,
                        )
                        continue

                    constraint_type = constraint.get("type", "")
                    if not constraint_type:
                        log_error(
                            LogEvent.MODEL_REGISTRY,
                            f"Constraint '{name}' missing required 'type' field",
                            constraint=constraint,
                        )
                        continue

                    if constraint_type == "numeric":
                        min_value = constraint.get("min")
                        max_value = constraint.get("max")
                        allow_float = constraint.get("allow_float", True)
                        allow_int = constraint.get("allow_int", True)
                        description = constraint.get("description", "")

                        # Type validation
                        if min_value is not None and not isinstance(
                            min_value, (int, float)
                        ):
                            log_error(
                                LogEvent.MODEL_REGISTRY,
                                f"Constraint '{name}' has non-numeric 'min' value",
                                min_value=min_value,
                            )
                            continue

                        if max_value is not None and not isinstance(
                            max_value, (int, float)
                        ):
                            log_error(
                                LogEvent.MODEL_REGISTRY,
                                f"Constraint '{name}' has non-numeric 'max' value",
                                max_value=max_value,
                            )
                            continue

                        if not isinstance(allow_float, bool) or not isinstance(
                            allow_int, bool
                        ):
                            log_error(
                                LogEvent.MODEL_REGISTRY,
                                f"Constraint '{name}' has non-boolean 'allow_float' or 'allow_int'",
                                allow_float=allow_float,
                                allow_int=allow_int,
                            )
                            continue

                        # Create constraint
                        self._constraints[name] = NumericConstraint(
                            min_value=min_value
                            if min_value is not None
                            else 0.0,
                            max_value=max_value,
                            allow_float=allow_float,
                            allow_int=allow_int,
                            description=description,
                        )
                    elif constraint_type == "enum":
                        allowed_values = constraint.get("values")
                        description = constraint.get("description", "")

                        # Required field validation
                        if allowed_values is None:
                            log_error(
                                LogEvent.MODEL_REGISTRY,
                                f"Constraint '{name}' missing required 'values' field",
                                constraint=constraint,
                            )
                            continue

                        # Type validation
                        if not isinstance(allowed_values, list):
                            log_error(
                                LogEvent.MODEL_REGISTRY,
                                f"Constraint '{name}' has non-list 'values' field",
                                allowed_values=allowed_values,
                            )
                            continue

                        # Validate all values are strings
                        if not all(
                            isinstance(val, str) for val in allowed_values
                        ):
                            log_error(
                                LogEvent.MODEL_REGISTRY,
                                f"Constraint '{name}' has non-string values in 'values' list",
                                allowed_values=allowed_values,
                            )
                            continue

                        # Create constraint
                        self._constraints[name] = EnumConstraint(
                            allowed_values=allowed_values,
                            description=description,
                        )
                    else:
                        log_error(
                            LogEvent.MODEL_REGISTRY,
                            f"Unknown constraint type '{constraint_type}' for '{name}'",
                            constraint=constraint,
                        )

        except FileNotFoundError:
            log_warning(
                LogEvent.MODEL_REGISTRY,
                "Parameter constraints file not found",
                path=self.config.constraints_path,
            )
        except Exception as e:
            log_error(
                LogEvent.MODEL_REGISTRY,
                "Failed to load parameter constraints",
                path=self.config.constraints_path,
                error=str(e),
            )

    def _load_capabilities(self) -> None:
        """Load model capabilities from config."""
        config_result = self._load_config()
        if not config_result.success:
            log_warning(
                LogEvent.MODEL_REGISTRY,
                "No model registry data loaded, using empty registry",
                error=config_result.error,
            )
            return

        # Process model data
        if config_result.data is None:
            log_error(
                LogEvent.MODEL_REGISTRY,
                "Failed to load configuration data",
            )
            return

        models_data = config_result.data.get("models", {})
        if not models_data:
            log_warning(
                LogEvent.MODEL_REGISTRY,
                "No models defined in registry configuration",
                path=config_result.path,
            )

        for model_name, model_config in models_data.items():
            try:
                # Extract aliases
                aliases = model_config.get("aliases", [])

                # Extract min version if present
                min_version_str = model_config.get("min_version")
                min_version = None
                if min_version_str:
                    try:
                        min_version = ModelVersion.from_string(min_version_str)
                    except ValueError:
                        log_warning(
                            LogEvent.MODEL_REGISTRY,
                            "Invalid min_version format for model",
                            model=model_name,
                            min_version=min_version_str,
                        )

                # Create parameters list from references
                param_refs = []
                for _, param_config in model_config.get(
                    "parameters", {}
                ).items():
                    constraint_ref = param_config.get("constraint")
                    if constraint_ref:
                        # Create a parameter reference with description
                        description = param_config.get("description", "")
                        param_refs.append(
                            ParameterReference(
                                ref=constraint_ref,
                                description=description,
                            )
                        )

                # Create capabilities object
                capabilities = ModelCapabilities(
                    model_name=model_name,
                    aliases=aliases,
                    openai_model_name=model_config.get(
                        "openai_name", model_name
                    ),
                    context_window=model_config.get("context_window", 0),
                    max_output_tokens=model_config.get("max_output_tokens", 0),
                    supports_vision=model_config.get("supports_vision", False),
                    supports_functions=model_config.get(
                        "supports_functions", False
                    ),
                    supports_streaming=model_config.get(
                        "supports_streaming", False
                    ),
                    supports_structured=model_config.get(
                        "supports_structured", False
                    ),
                    min_version=min_version,
                    supported_parameters=param_refs,
                    constraints=copy.deepcopy(
                        self._constraints
                    ),  # Deep copy to prevent shared reference
                )

                # Add to registry
                self._capabilities[model_name] = capabilities

                # Also register under aliases - check for duplicates first
                for alias in aliases:
                    if (
                        alias in self._capabilities
                        and self._capabilities[alias].model_name != model_name
                    ):
                        log_warning(
                            LogEvent.MODEL_REGISTRY,
                            "Duplicate model alias detected",
                            alias=alias,
                            original_model=self._capabilities[
                                alias
                            ].model_name,
                            new_model=model_name,
                        )
                        # Skip this alias to prevent overwriting the existing model
                        continue

                    self._capabilities[alias] = capabilities

            except Exception as e:
                log_error(
                    LogEvent.MODEL_REGISTRY,
                    "Failed to load model capabilities",
                    model=model_name,
                    error=str(e),
                )
                # Continue with other models

    def _get_capabilities_impl(self, model: str) -> ModelCapabilities:
        """Implementation of get_capabilities without caching.

        Args:
            model: Model name, which can be:
                  - Dated model (e.g. "gpt-4o-2024-08-06")
                  - Alias (e.g. "gpt-4o")
                  - Versioned model (e.g. "gpt-4o-2024-09-01")

        Returns:
            ModelCapabilities for the requested model

        Raises:
            ModelNotSupportedError: If the model is not supported
            InvalidDateError: If the date components are invalid
            VersionTooOldError: If the version is older than minimum supported
        """
        # First check for exact match (dated model or alias)
        if model in self._capabilities:
            return self._capabilities[model]

        # Check if this is a versioned model
        version_match = self._DATE_PATTERN.match(model)
        if version_match:
            base_name = version_match.group(1)
            version_str = version_match.group(2)

            # Find all capabilities for this base model
            model_versions = [
                (k, v)
                for k, v in self._capabilities.items()
                if k.startswith(f"{base_name}-")
            ]

            if not model_versions:
                # No versions found for this base model
                # Find aliases that might provide a valid alternative
                aliases = [
                    name
                    for name in self._capabilities.keys()
                    if not self._IS_DATED_MODEL_PATTERN.match(name)
                ]

                # Find if any alias might match the base model
                matching_aliases = [
                    alias for alias in aliases if alias == base_name
                ]

                if matching_aliases:
                    raise ModelNotSupportedError(
                        f"Model '{model}' not found. The base model '{base_name}' exists "
                        f"as an alias. Try using '{base_name}' instead.",
                        model=model,
                        available_models=matching_aliases,
                    )
                else:
                    # No matching aliases either
                    available_base_models: set[str] = set(
                        k
                        for k in self._capabilities.keys()
                        if not self._IS_DATED_MODEL_PATTERN.match(k)
                    )
                    raise ModelNotSupportedError(
                        f"Model '{model}' not found. Available base models: "
                        f"{', '.join(sorted(available_base_models))}",
                        model=model,
                        available_models=list(available_base_models),
                    )

            try:
                # Parse version
                requested_version = ModelVersion.from_string(version_str)
            except ValueError as e:
                raise InvalidDateError(str(e))

            # Find the model with the minimum version
            for dated_model, caps in model_versions:
                if caps.min_version and requested_version < caps.min_version:
                    # Find the matching alias if available
                    matching_alias = [
                        alias
                        for alias in caps.aliases
                        if alias == base_name or alias.startswith(base_name)
                    ]
                    alias_suggestion = (
                        matching_alias[0] if matching_alias else None
                    )

                    raise VersionTooOldError(
                        f"Model version '{model}' is older than the minimum supported "
                        f"version {caps.min_version} for {base_name}. "
                        + (
                            f"Try using '{alias_suggestion}' instead."
                            if alias_suggestion
                            else f"Try using a newer version like '{dated_model}'."
                        ),
                        model=model,
                        min_version=str(caps.min_version),
                        alias=alias_suggestion,
                    )

            # Find the best matching model
            base_model_caps = None
            for _dated_model, caps in model_versions:
                if base_model_caps is None or (
                    caps.min_version
                    and caps.min_version <= requested_version
                    and (
                        not base_model_caps.min_version
                        or caps.min_version > base_model_caps.min_version
                    )
                ):
                    base_model_caps = caps

            if base_model_caps:
                # Create a copy with the requested model name
                new_caps = ModelCapabilities(
                    model_name=base_model_caps.model_name,
                    openai_model_name=model,
                    context_window=base_model_caps.context_window,
                    max_output_tokens=base_model_caps.max_output_tokens,
                    supports_vision=base_model_caps.supports_vision,
                    supports_functions=base_model_caps.supports_functions,
                    supports_streaming=base_model_caps.supports_streaming,
                    supports_structured=base_model_caps.supports_structured,
                    min_version=base_model_caps.min_version,
                    aliases=base_model_caps.aliases,
                    supported_parameters=base_model_caps.supported_parameters,
                    constraints=base_model_caps._constraints,
                )
                return new_caps

        # If we get here, the model is not supported
        available_models: set[str] = set(
            k
            for k in self._capabilities.keys()
            if not self._IS_DATED_MODEL_PATTERN.match(k)
        )
        raise ModelNotSupportedError(
            f"Model '{model}' not found. Available base models: "
            f"{', '.join(sorted(available_models))}",
            model=model,
            available_models=list(available_models),
        )

    def get_parameter_constraint(
        self, ref: str
    ) -> Union[NumericConstraint, EnumConstraint]:
        """Get a parameter constraint by reference.

        Args:
            ref: Reference string (e.g., "numeric_constraints.temperature")

        Returns:
            The constraint object (NumericConstraint or EnumConstraint)

        Raises:
            ConstraintNotFoundError: If the constraint is not found
        """
        if ref not in self._constraints:
            raise ConstraintNotFoundError(
                f"Constraint reference '{ref}' not found in registry",
                ref=ref,
            )
        return self._constraints[ref]

    def _get_conditional_headers(self, force: bool = False) -> Dict[str, str]:
        """Get conditional headers for HTTP requests.

        Args:
            force: If True, bypass conditional headers

        Returns:
            Dictionary of HTTP headers
        """
        if force:
            return {}

        headers = {}
        meta_path = self._get_metadata_path()
        if meta_path and os.path.exists(meta_path):
            try:
                with open(meta_path, "r") as f:
                    metadata = yaml.safe_load(f)
                    if metadata and isinstance(metadata, dict):
                        if "etag" in metadata:
                            headers["If-None-Match"] = metadata["etag"]
                        if "last_modified" in metadata:
                            headers["If-Modified-Since"] = metadata[
                                "last_modified"
                            ]
            except Exception as e:
                log_debug(
                    LogEvent.MODEL_REGISTRY,
                    "Could not load cache metadata, skipping conditional headers",
                    error=str(e),
                )
        return headers

    def _get_metadata_path(self) -> Optional[str]:
        """Get the path to the cache metadata file.

        Returns:
            Optional[str]: Path to the metadata file, or None if config_path is not set
        """
        if not self.config.registry_path:
            return None
        return f"{self.config.registry_path}.meta"

    def _save_cache_metadata(self, metadata: Dict[str, str]) -> None:
        """Save cache metadata to file.

        Args:
            metadata: Dictionary of metadata to save
        """
        meta_path = self._get_metadata_path()
        if not meta_path:
            return

        try:
            with open(meta_path, "w") as f:
                yaml.safe_dump(metadata, f)
        except Exception as e:
            log_warning(
                LogEvent.MODEL_REGISTRY,
                "Could not save cache metadata",
                error=str(e),
                path=str(
                    meta_path
                ),  # Convert to string in case meta_path is None
            )

    def _fetch_remote_config(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch the remote configuration from the specified URL.

        Args:
            url: URL to fetch the configuration from

        Returns:
            Parsed configuration dictionary or None if fetch failed
        """
        try:
            import requests
        except ImportError:
            log_error(
                LogEvent.MODEL_REGISTRY,
                "Could not import requests module",
            )
            return None

        try:
            # Add a timeout of 10 seconds to prevent indefinite hanging
            response = requests.get(url, timeout=10)
            try:
                if response.status_code != 200:
                    log_error(
                        LogEvent.MODEL_REGISTRY,
                        f"HTTP error {response.status_code}",
                        url=url,
                    )
                    return None

                # Parse the YAML content
                config = yaml.safe_load(response.text)
                if not isinstance(config, dict):
                    log_error(
                        LogEvent.MODEL_REGISTRY,
                        "Remote config is not a dictionary",
                        url=url,
                    )
                    return None

                return config
            finally:
                # Ensure response is closed to prevent resource leaks
                response.close()
        except (requests.RequestException, yaml.YAMLError) as e:
            log_error(
                LogEvent.MODEL_REGISTRY,
                f"Failed to fetch or parse remote config: {str(e)}",
                url=url,
            )
            return None

    def _validate_remote_config(self, config: Dict[str, Any]) -> None:
        """Validate the remote configuration before applying it.

        Args:
            config: Configuration dictionary to validate

        Raises:
            ValueError: If the configuration is invalid
        """
        # Check version
        if "version" not in config:
            raise ValueError("Remote configuration missing version field")

        # Check required sections
        if "dated_models" not in config:
            raise ValueError(
                "Remote configuration missing dated_models section"
            )

        if "aliases" not in config:
            raise ValueError("Remote configuration missing aliases section")

        # Validate dated models
        for model_id, model_data in config["dated_models"].items():
            required_fields = [
                "context_window",
                "max_output_tokens",
                "supported_parameters",
            ]
            for field in required_fields:
                if field not in model_data:
                    raise ValueError(
                        f"Model {model_id} missing required field: {field}"
                    )

            # Validate version information
            if "min_version" not in model_data:
                raise ValueError(f"Model {model_id} missing min_version")

            min_version = model_data["min_version"]
            for field in ["year", "month", "day"]:
                if field not in min_version:
                    raise ValueError(
                        f"Model {model_id} min_version missing {field}"
                    )

    def refresh_from_remote(
        self,
        url: Optional[str] = None,
        force: bool = False,
        validate_only: bool = False,
    ) -> RefreshResult:
        """Refresh the registry configuration from remote source.

        Args:
            url: Optional custom URL to fetch registry from
            force: Force refresh even if version is current
            validate_only: Only validate remote config without updating

        Returns:
            Result of the refresh operation
        """
        # Check for updates
        result = self.check_for_updates(url=url)

        if not force and result.status == RefreshStatus.ALREADY_CURRENT:
            return RefreshResult(
                success=True,
                status=RefreshStatus.ALREADY_CURRENT,
                message="Registry is already up to date",
            )

        try:
            # Get remote config
            config_url = url or (
                "https://raw.githubusercontent.com/openai-model-registry/"
                "openai-model-registry/main/src/openai_model_registry/config/models.yml"
            )
            remote_config = self._fetch_remote_config(config_url)
            if not remote_config:
                raise ValueError("Failed to fetch remote configuration")

            # Validate the remote config
            self._validate_remote_config(remote_config)

            if validate_only:
                # Only validation was requested
                return RefreshResult(
                    success=True,
                    status=RefreshStatus.VALIDATED,
                    message="Remote registry configuration validated successfully",
                )

            # Write to user config directory instead of package directory
            ensure_user_config_dir_exists()
            target_path = get_user_config_dir() / MODEL_REGISTRY_FILENAME

            # Write the updated config
            try:
                with open(target_path, "w") as f:
                    yaml.dump(remote_config, f)
            except PermissionError as e:
                log_error(
                    LogEvent.MODEL_REGISTRY,
                    "Permission denied when writing registry configuration",
                    path=str(target_path),
                    error=str(e),
                )
                return RefreshResult(
                    success=False,
                    status=RefreshStatus.ERROR,
                    message=f"Permission denied when writing to {target_path}",
                )
            except OSError as e:
                log_error(
                    LogEvent.MODEL_REGISTRY,
                    "File system error when writing registry configuration",
                    path=str(target_path),
                    error=str(e),
                )
                return RefreshResult(
                    success=False,
                    status=RefreshStatus.ERROR,
                    message=f"Error writing to {target_path}: {str(e)}",
                )

            # Reload the registry with new configuration
            self._load_constraints()
            self._load_capabilities()

            # Verify that the reload was successful
            if not self._capabilities:
                log_error(
                    LogEvent.MODEL_REGISTRY,
                    "Failed to reload registry after update",
                    path=str(target_path),
                )
                return RefreshResult(
                    success=False,
                    status=RefreshStatus.ERROR,
                    message="Registry update failed: could not load capabilities after update",
                )

            # Log success
            log_info(
                LogEvent.MODEL_REGISTRY,
                "Registry updated from remote",
                version=remote_config.get("version", "unknown"),
            )

            return RefreshResult(
                success=True,
                status=RefreshStatus.UPDATED,
                message="Registry updated successfully",
            )

        except Exception as e:
            error_msg = f"Error refreshing registry: {str(e)}"
            log_error(
                LogEvent.MODEL_REGISTRY,
                error_msg,
            )
            return RefreshResult(
                success=False,
                status=RefreshStatus.ERROR,
                message=error_msg,
            )

    def check_for_updates(self, url: Optional[str] = None) -> RefreshResult:
        """Check if updates are available for the model registry.

        Args:
            url: Optional custom URL to check for updates

        Returns:
            Result of the update check
        """
        try:
            import requests
        except ImportError:
            return RefreshResult(
                success=False,
                status=RefreshStatus.ERROR,
                message="Could not import requests module",
            )

        # Set up the URL
        config_url = url or (
            "https://raw.githubusercontent.com/openai-model-registry/"
            "openai-model-registry/main/src/openai_model_registry/config/models.yml"
        )

        try:
            # Use a lock when checking and comparing versions to prevent race conditions
            with self.__class__._instance_lock:
                # Load current configuration to compare versions
                current_config = self._load_config()

                # Handle ConfigResult vs dict return type
                if isinstance(current_config, dict):
                    config_data = current_config
                    has_version = "version" in config_data
                else:
                    # It's a ConfigResult
                    if (
                        not current_config.success
                        or current_config.data is None
                    ):
                        return RefreshResult(
                            success=True,
                            status=RefreshStatus.UPDATE_AVAILABLE,
                            message="Current version unknown, update recommended",
                        )
                    config_data = current_config.data  # type: ignore
                    has_version = "version" in config_data

                if not has_version:
                    # Can't determine current version, assume update needed
                    return RefreshResult(
                        success=True,
                        status=RefreshStatus.UPDATE_AVAILABLE,
                        message="Current version unknown, update recommended",
                    )

                # Get remote version (just the version info)
                try:
                    # Add a timeout of 10 seconds to HEAD request
                    head_response = requests.head(config_url, timeout=10)
                    try:
                        if head_response.status_code == 404:
                            return RefreshResult(
                                success=False,
                                status=RefreshStatus.ERROR,
                                message=f"Registry not found at {config_url}",
                            )
                        elif head_response.status_code != 200:
                            return RefreshResult(
                                success=False,
                                status=RefreshStatus.ERROR,
                                message=f"HTTP error {head_response.status_code} during HEAD request",
                            )

                        # Check if version info is available in headers (future optimization)
                        # For now, we still need the GET request to get the version
                    finally:
                        # Ensure HEAD response is closed
                        head_response.close()

                    # Make GET request to get the actual content
                    get_response = requests.get(config_url, timeout=10)
                    try:
                        if get_response.status_code != 200:
                            return RefreshResult(
                                success=False,
                                status=RefreshStatus.ERROR,
                                message=f"HTTP error {get_response.status_code} during GET request",
                            )

                        # Load the remote config as a dict
                        config_dict = yaml.safe_load(get_response.text)
                        if (
                            not config_dict
                            or not isinstance(config_dict, dict)
                            or "version" not in config_dict
                        ):
                            return RefreshResult(
                                success=False,
                                status=RefreshStatus.ERROR,
                                message="Invalid remote configuration format",
                            )

                        # Compare versions
                        current_version = config_data["version"]
                        remote_version = config_dict["version"]

                        # Parse versions using semantic versioning
                        try:
                            current_ver = version.parse(str(current_version))
                            remote_ver = version.parse(str(remote_version))

                            if current_ver >= remote_ver:
                                return RefreshResult(
                                    success=True,
                                    status=RefreshStatus.ALREADY_CURRENT,
                                    message=f"Registry is already up to date (version {current_version})",
                                )
                            else:
                                # Remote version is newer
                                return RefreshResult(
                                    success=True,
                                    status=RefreshStatus.UPDATE_AVAILABLE,
                                    message=f"Update available: {current_version} -> {remote_version}",
                                )
                        except (TypeError, ValueError) as e:
                            # Fallback to string comparison if version parsing fails
                            log_warning(
                                LogEvent.MODEL_REGISTRY,
                                f"Failed to parse versions as semantic versions: {e}",
                                current_version=str(current_version),
                                remote_version=str(remote_version),
                            )

                            if current_version == remote_version:
                                return RefreshResult(
                                    success=True,
                                    status=RefreshStatus.ALREADY_CURRENT,
                                    message=f"Registry is already up to date (version {current_version})",
                                )
                            else:
                                # Version differs, update available
                                return RefreshResult(
                                    success=True,
                                    status=RefreshStatus.UPDATE_AVAILABLE,
                                    message=f"Update available: {current_version} -> {remote_version}",
                                )
                    finally:
                        # Ensure GET response is closed
                        get_response.close()
                except (requests.RequestException, yaml.YAMLError) as e:
                    return RefreshResult(
                        success=False,
                        status=RefreshStatus.ERROR,
                        message=f"Failed to check for updates: {str(e)}",
                    )

        except Exception as e:
            return RefreshResult(
                success=False,
                status=RefreshStatus.ERROR,
                message=f"Unexpected error checking for updates: {str(e)}",
            )

    # Fallback models provide default capabilities when config is missing
    _fallback_models = {
        "version": "1.0.0",
        "dated_models": {
            "gpt-4o-2024-08-06": {
                "context_window": 128000,
                "max_output_tokens": 16384,
                "supports_structured": True,
                "supports_streaming": True,
                "supported_parameters": [
                    {"ref": "numeric_constraints.temperature"},
                    {"ref": "numeric_constraints.top_p"},
                    {"ref": "numeric_constraints.frequency_penalty"},
                    {"ref": "numeric_constraints.presence_penalty"},
                    {"ref": "numeric_constraints.max_completion_tokens"},
                ],
                "description": "Production GPT-4 model with structured output support",
                "min_version": {
                    "year": 2024,
                    "month": 8,
                    "day": 6,
                },
            },
            "gpt-4o-mini-2024-07-18": {
                "context_window": 128000,
                "max_output_tokens": 16384,
                "supports_structured": True,
                "supports_streaming": True,
                "supported_parameters": [
                    {"ref": "numeric_constraints.temperature"},
                    {"ref": "numeric_constraints.top_p"},
                    {"ref": "numeric_constraints.frequency_penalty"},
                    {"ref": "numeric_constraints.presence_penalty"},
                    {"ref": "numeric_constraints.max_completion_tokens"},
                ],
                "description": "First release of mini variant",
                "min_version": {
                    "year": 2024,
                    "month": 7,
                    "day": 18,
                },
            },
            "o1-2024-12-17": {
                "context_window": 200000,
                "max_output_tokens": 100000,
                "supports_structured": True,
                "supports_streaming": True,
                "supported_parameters": [
                    {"ref": "numeric_constraints.max_completion_tokens"},
                    {"ref": "enum_constraints.reasoning_effort"},
                ],
                "description": "Production O1 model optimized for structured output",
                "min_version": {
                    "year": 2024,
                    "month": 12,
                    "day": 17,
                },
            },
        },
        "aliases": {
            "gpt-4o": "gpt-4o-2024-08-06",
            "gpt-4o-mini": "gpt-4o-mini-2024-07-18",
            "o1": "o1-2024-12-17",
        },
    }

    @classmethod
    def cleanup(cls) -> None:
        """Clean up the registry instance."""
        with cls._instance_lock:
            cls._default_instance = None

    @property
    def models(self) -> Dict[str, ModelCapabilities]:
        """Get a read-only view of registered models."""
        return dict(self._capabilities)


def get_registry() -> ModelRegistry:
    """Get the model registry singleton instance.

    This is a convenience function for getting the registry instance.

    Returns:
        ModelRegistry: The singleton registry instance
    """
    return ModelRegistry.get_instance()
