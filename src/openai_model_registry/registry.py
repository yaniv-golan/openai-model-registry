"""Core registry functionality for managing OpenAI model capabilities.

This module provides the ModelRegistry class, which is the central component
for managing model capabilities, version validation, and parameter constraints.
"""

import logging
import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union, cast

import yaml
from pydantic import BaseModel, Field, ValidationError

from .config_paths import (
    MODEL_REGISTRY_FILENAME,
    PARAM_CONSTRAINTS_FILENAME,
    copy_default_to_user_config,
    ensure_user_config_dir_exists,
    get_model_registry_path,
    get_parameter_constraints_path,
    get_user_config_dir,
)
from .constraints import (
    EnumConstraint,
    NumericConstraint,
    ParameterReference,
)
from .errors import (
    InvalidDateError,
    ModelNotSupportedError,
    ModelRegistryError,
    TokenParameterError,
    VersionTooOldError,
)
from .logging import LogEvent, LogLevel, _log
from .model_version import ModelVersion

# Create module logger
logger = logging.getLogger(__name__)


def _default_log_callback(
    level: int, event: str, data: Dict[str, Any]
) -> None:
    """Default logging callback that uses the standard logging module."""
    logger.log(level, f"{event}: {data}")


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


class ModelCapabilities(BaseModel):
    """Model capabilities and constraints."""

    context_window: int
    max_output_tokens: int
    supports_structured: bool = True
    supports_streaming: bool = True
    supported_parameters: List[ParameterReference]
    description: str = ""
    min_version: Optional[ModelVersion] = None
    openai_model_name: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)

    # Add model_config to allow ModelVersion as an arbitrary type
    model_config = {
        "arbitrary_types_allowed": True,
    }

    def validate_parameter(
        self,
        param_name: str,
        value: Any,
        *,
        used_params: Optional[Set[str]] = None,
    ) -> None:
        """Validate that a parameter is supported and its value is valid.

        Args:
            param_name: Name of the parameter to validate
            value: Value to validate
            used_params: Optional set to track which parameters have been used

        Raises:
            OpenAIClientError: If the parameter is not supported or invalid
        """
        # Add to used_params if provided
        if used_params is not None:
            if param_name in used_params:
                raise ModelRegistryError(
                    f"Parameter '{param_name}' has already been used. "
                    f"It cannot be specified multiple times."
                )
            used_params.add(param_name)

        # Special handling for token limits
        if param_name in {
            "max_tokens",
            "max_completion_tokens",
            "max_output_tokens",
        }:
            # Ensure they're not too large for the model
            if (
                isinstance(value, (int, float))
                and value > self.max_output_tokens
            ):
                raise TokenParameterError(
                    f"Token limit '{param_name}' exceeds model maximum. "
                    f"Maximum for {self.openai_model_name} is {self.max_output_tokens}, "
                    f"but {value} was requested.",
                    param_name,
                    value,
                )

        # Find parameter reference
        param_ref = None
        for ref in self.supported_parameters:
            if param_name in ref.ref:
                param_ref = ref
                break

        if param_ref is None:
            supported_params = [
                ref.ref.split(".")[1] for ref in self.supported_parameters
            ]
            raise ModelRegistryError(
                f"Parameter '{param_name}' is not supported by model '{self.openai_model_name}'.\n"
                f"Supported parameters: {', '.join(sorted(supported_params))}"
            )

        # Get the constraint from the registry
        constraint = ModelRegistry.get_instance().get_parameter_constraint(
            param_ref.ref
        )

        if isinstance(constraint, NumericConstraint):
            # Validate numeric type
            if not isinstance(value, (int, float)):
                raise ModelRegistryError(
                    f"Parameter '{param_name}' must be a number, got {type(value).__name__}.\n"
                    "Allowed types: "
                    + (
                        "float and integer"
                        if constraint.allow_float and constraint.allow_int
                        else (
                            "float only"
                            if constraint.allow_float
                            else "integer only"
                        )
                    )
                )

            # Validate integer/float requirements
            if isinstance(value, float) and not constraint.allow_float:
                raise ModelRegistryError(
                    f"Parameter '{param_name}' must be an integer, got float {value}.\n"
                    f"Description: {constraint.description}"
                )
            if isinstance(value, int) and not constraint.allow_int:
                raise ModelRegistryError(
                    f"Parameter '{param_name}' must be a float, got integer {value}.\n"
                    f"Description: {constraint.description}"
                )

            # Use override max_value if specified
            max_value = param_ref.max_value or constraint.max_value
            if max_value is None:
                max_value = self.max_output_tokens

            # Validate range
            if value < constraint.min_value or value > max_value:
                raise ModelRegistryError(
                    f"Parameter '{param_name}' must be between {constraint.min_value} and {max_value}.\n"
                    f"Description: {constraint.description}\n"
                    f"Current value: {value}"
                )

        elif isinstance(constraint, EnumConstraint):
            # Validate type
            if not isinstance(value, str):
                raise ModelRegistryError(
                    f"Parameter '{param_name}' must be a string, got {type(value).__name__}.\n"
                    f"Description: {constraint.description}"
                )

            # Validate allowed values
            if value not in constraint.allowed_values:
                raise ModelRegistryError(
                    f"Invalid value '{value}' for parameter '{param_name}'.\n"
                    f"Description: {constraint.description}\n"
                    f"Allowed values: {', '.join(map(str, sorted(constraint.allowed_values)))}"
                )


class ModelRegistry:
    """Registry for model capabilities and validation."""

    _instance: Optional["ModelRegistry"] = None
    _config_path: Optional[str] = None
    _constraints_path: Optional[str] = None

    def __new__(cls) -> "ModelRegistry":
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the model registry."""
        if not hasattr(self, "_initialized"):
            self._capabilities: Dict[str, ModelCapabilities] = {}
            self._constraints: Dict[
                str, Union[NumericConstraint, EnumConstraint]
            ] = {}

            # Get paths using XDG standard and fallbacks
            self._config_path = get_model_registry_path()
            self._constraints_path = get_parameter_constraints_path()

            # Auto-copy default configs to user directory if they don't exist
            copy_default_to_user_config(MODEL_REGISTRY_FILENAME)
            copy_default_to_user_config(PARAM_CONSTRAINTS_FILENAME)

            if not self._config_path or not self._constraints_path:
                raise ValueError("Registry paths not set")

            self._load_constraints()
            self._load_capabilities()
            self._initialized = True

    def _load_config(self) -> Optional[Dict[str, Any]]:
        """Load model configuration from file.

        Returns:
            Optional[Dict[str, Any]]: The loaded configuration data, or None if loading failed
        """
        if not self._config_path:
            raise ValueError("Config path not set")

        try:
            with open(self._config_path, "r") as f:
                data = yaml.safe_load(f)
                if not isinstance(data, dict):
                    return None
                return data
        except FileNotFoundError:
            _log(
                _default_log_callback,
                LogLevel.WARNING,
                LogEvent.MODEL_REGISTRY,
                {
                    "message": "Model registry config file not found, using defaults",
                    "path": self._config_path,
                },
            )
            return None
        except Exception as e:
            _log(
                _default_log_callback,
                LogLevel.WARNING,
                LogEvent.MODEL_REGISTRY,
                {
                    "message": "Failed to load model registry config, using fallbacks",
                    "error": str(e),
                    "path": self._config_path,
                },
            )
            return None

    def _load_constraints(self) -> None:
        """Load parameter constraints from file."""
        if not self._constraints_path:
            raise ValueError("Constraints path not set")

        try:
            with open(self._constraints_path, "r") as f:
                data = yaml.safe_load(f)

            # Load numeric constraints
            for name, config in data.get("numeric_constraints", {}).items():
                key = f"numeric_constraints.{name}"
                self._constraints[key] = NumericConstraint(**config)

            # Load enum constraints
            for name, config in data.get("enum_constraints", {}).items():
                key = f"enum_constraints.{name}"
                self._constraints[key] = EnumConstraint(**config)

        except FileNotFoundError:
            _log(
                _default_log_callback,
                LogLevel.WARNING,
                LogEvent.MODEL_REGISTRY,
                {
                    "message": "Parameter constraints file not found, using defaults",
                    "path": self._constraints_path,
                },
            )
        except Exception as e:
            _log(
                _default_log_callback,
                LogLevel.ERROR,
                LogEvent.MODEL_REGISTRY,
                {
                    "message": "Failed to load parameter constraints",
                    "error": str(e),
                },
            )
            raise

    def _load_capabilities(self) -> None:
        """Load model capabilities from YAML."""
        # Clear existing capabilities
        self._capabilities.clear()

        # Load configuration
        data = self._load_config()
        if data is None:
            # If loading failed, use fallback models
            data = self._fallback_models

        try:
            # Process dated models
            dated_models = cast(Dict[str, Any], data.get("dated_models", {}))
            for model, config in dated_models.items():
                try:
                    # Handle min_version
                    if "min_version" in config:
                        # Convert to ModelVersion if needed
                        if isinstance(config["min_version"], dict):
                            config["min_version"] = ModelVersion(
                                **config["min_version"]
                            )

                    # Set model name
                    config["openai_model_name"] = model

                    # Create and store capabilities
                    self._capabilities[model] = ModelCapabilities(**config)
                except ValidationError as e:
                    _log(
                        _default_log_callback,
                        LogLevel.ERROR,
                        LogEvent.MODEL_REGISTRY,
                        {
                            "message": f"Failed to load model {model}",
                            "error": str(e),
                        },
                    )

            # Process aliases
            aliases_dict = data.get("aliases", {})
            if isinstance(aliases_dict, dict):
                for alias, target in aliases_dict.items():
                    if target in self._capabilities:
                        # Get the target model capabilities
                        target_model = self._capabilities[target]

                        # Create alias in capabilities
                        self._capabilities[alias] = target_model

                        # Add alias to the target model's aliases list
                        if alias not in target_model.aliases:
                            target_model.aliases.append(alias)
                    else:
                        _log(
                            _default_log_callback,
                            LogLevel.WARNING,
                            LogEvent.MODEL_REGISTRY,
                            {
                                "message": f"Alias {alias} targets non-existent model {target}",
                            },
                        )

        except Exception as e:
            _log(
                _default_log_callback,
                LogLevel.ERROR,
                LogEvent.MODEL_REGISTRY,
                {
                    "message": "Failed to load model capabilities",
                    "error": str(e),
                },
            )

    @classmethod
    def get_instance(cls) -> "ModelRegistry":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_capabilities(self, model: str) -> ModelCapabilities:
        """Get capabilities for a model.

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
        version_match = re.match(r"^(.*)-(\d{4}-\d{2}-\d{2})$", model)
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
                    if not re.match(r".*-\d{4}-\d{2}-\d{2}$", name)
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
                        if not re.match(r".*-\d{4}-\d{2}-\d{2}$", k)
                    )
                    raise ModelNotSupportedError(
                        f"Model '{model}' not found. Available base models: "
                        f"{', '.join(sorted(available_base_models))}",
                        model=model,
                        available_models=available_base_models,
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
                new_caps = base_model_caps.model_copy(
                    update={"openai_model_name": model}
                )
                return new_caps

        # If we get here, the model is not supported
        available_models: set[str] = set(
            k
            for k in self._capabilities.keys()
            if not re.match(r".*-\d{4}-\d{2}-\d{2}$", k)
        )
        raise ModelNotSupportedError(
            f"Model '{model}' not found. Available base models: "
            f"{', '.join(sorted(available_models))}",
            model=model,
            available_models=available_models,
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
            KeyError: If the constraint is not found
        """
        if ref not in self._constraints:
            raise KeyError(f"Constraint not found: {ref}")
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
                _log(
                    _default_log_callback,
                    LogLevel.DEBUG,
                    LogEvent.MODEL_REGISTRY,
                    {
                        "message": "Could not load cache metadata, skipping conditional headers",
                        "error": str(e),
                    },
                )
        return headers

    def _get_metadata_path(self) -> Optional[str]:
        """Get the path to the cache metadata file.

        Returns:
            Optional[str]: Path to the metadata file, or None if config_path is not set
        """
        if not self._config_path:
            return None
        return f"{self._config_path}.meta"

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
            _log(
                _default_log_callback,
                LogLevel.WARNING,
                LogEvent.MODEL_REGISTRY,
                {
                    "message": "Could not save cache metadata",
                    "error": str(e),
                    "path": meta_path,
                },
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
            _log(
                _default_log_callback,
                LogLevel.ERROR,
                LogEvent.MODEL_REGISTRY,
                {"error": "Could not import requests module"},
            )
            return None

        try:
            response = requests.get(url)
            if response.status_code != 200:
                _log(
                    _default_log_callback,
                    LogLevel.ERROR,
                    LogEvent.MODEL_REGISTRY,
                    {
                        "error": f"HTTP error {response.status_code}",
                        "url": url,
                    },
                )
                return None

            # Parse the YAML content
            config = yaml.safe_load(response.text)
            if not isinstance(config, dict):
                _log(
                    _default_log_callback,
                    LogLevel.ERROR,
                    LogEvent.MODEL_REGISTRY,
                    {
                        "error": "Remote config is not a dictionary",
                        "url": url,
                    },
                )
                return None

            return config
        except (requests.RequestException, yaml.YAMLError) as e:
            _log(
                _default_log_callback,
                LogLevel.ERROR,
                LogEvent.MODEL_REGISTRY,
                {
                    "error": f"Failed to fetch or parse remote config: {str(e)}",
                    "url": url,
                },
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
            with open(target_path, "w") as f:
                yaml.dump(remote_config, f)

            # Reload the registry with new configuration
            self._load_constraints()
            self._load_capabilities()

            # Log success
            _log(
                _default_log_callback,
                LogLevel.INFO,
                LogEvent.MODEL_REGISTRY,
                {
                    "message": f"Registry updated from {config_url}",
                    "version": remote_config.get("version", "unknown"),
                },
            )

            return RefreshResult(
                success=True,
                status=RefreshStatus.UPDATED,
                message="Registry updated successfully",
            )

        except Exception as e:
            error_msg = f"Error refreshing registry: {str(e)}"
            _log(
                _default_log_callback,
                LogLevel.ERROR,
                LogEvent.MODEL_REGISTRY,
                {"message": error_msg},
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
            # Load current configuration to compare versions
            current_config = self._load_config()
            if not current_config or "version" not in current_config:
                # Can't determine current version, assume update needed
                return RefreshResult(
                    success=True,
                    status=RefreshStatus.UPDATE_AVAILABLE,
                    message="Current version unknown, update recommended",
                )

            # Get remote version (just the version info)
            try:
                response = requests.head(config_url)
                if response.status_code == 404:
                    return RefreshResult(
                        success=False,
                        status=RefreshStatus.ERROR,
                        message=f"Registry not found at {config_url}",
                    )

                # If we can't determine remote version with HEAD, get the full config
                response = requests.get(config_url)
                if response.status_code != 200:
                    return RefreshResult(
                        success=False,
                        status=RefreshStatus.ERROR,
                        message=f"HTTP error {response.status_code}",
                    )

                remote_config = yaml.safe_load(response.text)
                if not remote_config or "version" not in remote_config:
                    return RefreshResult(
                        success=False,
                        status=RefreshStatus.ERROR,
                        message="Invalid remote configuration format",
                    )

                # Compare versions
                current_version = current_config["version"]
                remote_version = remote_config["version"]

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
        cls._instance = None
        cls._config_path = None
        cls._constraints_path = None

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
