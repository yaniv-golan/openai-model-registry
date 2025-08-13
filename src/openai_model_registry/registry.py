"""Core registry functionality for managing OpenAI model capabilities.

This module provides the ModelRegistry class, which is the central component
for managing model capabilities, version validation, and parameter constraints.

This module is the canonical implementation (v1.0 and later).
Typical usage:

    from openai_model_registry import get_registry  # singleton helper

    # or, for a custom configuration
    from openai_model_registry import ModelRegistry

Backward-compatibility shims from < v1.0 have been removed.

"""

import copy
import functools
import os
import re
import threading
import typing
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Literal, NamedTuple, Optional, Set, Union, cast

import yaml

from .config_paths import (
    PARAM_CONSTRAINTS_FILENAME,
    copy_default_to_user_config,
    get_parameter_constraints_path,
    get_user_data_dir,
)
from .config_result import ConfigResult
from .constraints import EnumConstraint, NumericConstraint, ObjectConstraint, ParameterReference
from .data_manager import DataManager
from .deprecation import DeprecationInfo, assert_model_active, sunset_headers
from .errors import (
    ConstraintNotFoundError,
    InvalidDateError,
    ModelNotSupportedError,
    ParameterNotSupportedError,
    VersionTooOldError,
)
from .logging import LogEvent, get_logger, log_debug, log_error, log_info, log_warning
from .model_version import ModelVersion
from .pricing import PricingInfo

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
        self.registry_path = registry_path  # Will be handled by DataManager
        self.constraints_path = constraints_path or get_parameter_constraints_path()
        self.auto_update = auto_update

        # Validate cache_size bounds to prevent excessive memory usage
        if cache_size < 1:
            raise ValueError("cache_size must be at least 1")
        if cache_size > 10000:
            raise ValueError("cache_size must not exceed 10000 to prevent excessive memory usage")
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


class UpdateInfo(NamedTuple):
    """Information about available updates."""

    update_available: bool
    current_version: Optional[str]
    current_version_date: Optional[str]
    latest_version: Optional[str]
    latest_version_date: Optional[str]
    download_url: Optional[str]
    update_size_estimate: Optional[str]
    latest_version_description: Optional[str]
    accumulated_changes: List[Dict[str, Any]]
    error_message: Optional[str] = None


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


@dataclass(frozen=True)
class WebSearchBilling:
    """Web search billing policy and rates for a model.

    - call_fee_per_1000: flat fee per 1000 calls
    - content_token_policy: whether content tokens are included or billed at model rate
    - currency: ISO currency code (default USD)
    - notes: optional free-form notes
    """

    call_fee_per_1000: float
    content_token_policy: Literal["included_in_call_fee", "billed_at_model_rate"]
    currency: str = "USD"
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if self.call_fee_per_1000 < 0:
            raise ValueError("call_fee_per_1000 must be non-negative")


class ModelCapabilities:
    """Represents the capabilities of a model."""

    def __init__(
        self,
        model_name: str,
        openai_model_name: str,
        context_window: int,
        max_output_tokens: int,
        deprecation: DeprecationInfo,
        supports_vision: bool = False,
        supports_functions: bool = False,
        supports_streaming: bool = False,
        supports_structured: bool = False,
        supports_web_search: bool = False,
        supports_audio: bool = False,
        supports_json_mode: bool = False,
        pricing: Optional["PricingInfo"] = None,
        input_modalities: Optional[List[str]] = None,
        output_modalities: Optional[List[str]] = None,
        min_version: Optional[ModelVersion] = None,
        aliases: Optional[List[str]] = None,
        supported_parameters: Optional[List[ParameterReference]] = None,
        constraints: Optional[Dict[str, Union[NumericConstraint, EnumConstraint, ObjectConstraint]]] = None,
        inline_parameters: Optional[Dict[str, Dict[str, Any]]] = None,
        web_search_billing: Optional["WebSearchBilling"] = None,
    ):
        """Initialize model capabilities.

        Args:
            model_name: The model identifier in the registry
            openai_model_name: The model name to use with OpenAI API
            context_window: Maximum context window size in tokens
            max_output_tokens: Maximum output tokens
            deprecation: Deprecation metadata (mandatory in current schema)
            supports_vision: Whether the model supports vision inputs
            supports_functions: Whether the model supports function calling
            supports_streaming: Whether the model supports streaming
            supports_structured: Whether the model supports structured output
            supports_web_search: Whether the model supports web search
                (Chat API search-preview models or Responses API tool)
            supports_audio: Whether the model supports audio inputs
            supports_json_mode: Whether the model supports JSON mode
            pricing: Pricing information for the model
            input_modalities: List of supported input modalities (e.g., ["text", "image"]).
            output_modalities: List of supported output modalities (e.g., ["text", "image"]).
            min_version: Minimum version for dated model variants
            aliases: List of aliases for this model
            supported_parameters: List of parameter references supported by this model
            constraints: Dictionary of constraints for validation
            inline_parameters: Dictionary of inline parameter configurations from schema
            web_search_billing: Optional web-search billing policy and rates for the model
        """
        self.model_name = model_name
        self.openai_model_name = openai_model_name
        self.context_window = context_window
        self.max_output_tokens = max_output_tokens
        self.deprecation = deprecation
        self.supports_vision = supports_vision
        self.supports_functions = supports_functions
        self.supports_streaming = supports_streaming
        self.supports_structured = supports_structured
        self.supports_web_search = supports_web_search
        self.supports_audio = supports_audio
        self.supports_json_mode = supports_json_mode
        self.pricing = pricing
        self.input_modalities = input_modalities or []
        self.output_modalities = output_modalities or []
        self.min_version = min_version
        self.aliases = aliases or []
        self.supported_parameters = supported_parameters or []
        self._constraints = constraints or {}
        self._inline_parameters = inline_parameters or {}
        self.web_search_billing = web_search_billing

    @property
    def inline_parameters(self) -> Dict[str, Any]:
        """Inline parameter definitions for this model (if any)."""
        return self._inline_parameters

    @property
    def is_sunset(self) -> bool:
        """Check if the model is sunset."""
        return self.deprecation.status == "sunset"

    @property
    def is_deprecated(self) -> bool:
        """Check if the model is deprecated or sunset."""
        return self.deprecation.status in ["deprecated", "sunset"]

    def get_constraint(self, ref: str) -> Optional[Union[NumericConstraint, EnumConstraint, ObjectConstraint]]:
        """Get a constraint by reference.

        Args:
            ref: Constraint reference (key in constraints dict)

        Returns:
            The constraint or None if not found
        """
        return self._constraints.get(ref)

    def validate_parameter(self, name: str, value: Any, used_params: Optional[Set[str]] = None) -> None:
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

        # Check if we have inline parameter constraints
        if name in self._inline_parameters:
            self._validate_inline_parameter(name, value)
            return

        # Find matching parameter reference
        param_ref = next(
            (p for p in self.supported_parameters if p.ref == name or p.ref.split(".")[-1] == name),
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
        elif isinstance(constraint, ObjectConstraint):
            constraint.validate(name=name, value=value)
        else:
            # This shouldn't happen with proper type checking, but just in case
            raise TypeError(f"Unknown constraint type for '{name}': {type(constraint).__name__}")

    def validate_parameters(self, params: Dict[str, Any], used_params: Optional[Set[str]] = None) -> None:
        """Validate multiple parameters against constraints.

        Args:
            params: Dictionary of parameter names and values to validate
            used_params: Optional set to track used parameters

        Raises:
            ModelRegistryError: If validation fails for any parameter
        """
        for name, value in params.items():
            self.validate_parameter(name, value, used_params)

    def _validate_inline_parameter(self, name: str, value: Any) -> None:
        """Validate a parameter using inline parameter constraints.

        Args:
            name: Parameter name
            value: Parameter value to validate

        Raises:
            ValidationError: If validation fails
        """
        from .errors import ParameterValidationError

        param_config = self._inline_parameters[name]
        param_type = param_config.get("type")

        # Handle numeric parameters (temperature, top_p, etc.)
        if param_type == "numeric":
            if not isinstance(value, (int, float)):
                raise ParameterValidationError(
                    f"Parameter '{name}' expects a numeric value",
                    param_name=name,
                    value=value,
                    model=self.model_name,
                )
            min_val = param_config.get("min")
            max_val = param_config.get("max")

            if min_val is not None and value < min_val:
                raise ParameterValidationError(
                    f"Parameter '{name}' value {value} is below minimum {min_val}",
                    param_name=name,
                    value=value,
                    model=self.model_name,
                )

            if max_val is not None and value > max_val:
                raise ParameterValidationError(
                    f"Parameter '{name}' value {value} is above maximum {max_val}",
                    param_name=name,
                    value=value,
                    model=self.model_name,
                )

        # Handle integer parameters (max_tokens, etc.)
        elif name in ["max_tokens", "n", "logprobs", "top_logprobs"] and isinstance(value, int):
            min_val = param_config.get("min")
            max_val = param_config.get("max")
        # Handle enum parameters declared inline
        elif param_type == "enum":
            allowed_values = param_config.get("enum", [])
            if value not in allowed_values:
                raise ParameterValidationError(
                    f"Parameter '{name}' value '{value}' is not one of: {', '.join(map(str, allowed_values))}",
                    param_name=name,
                    value=value,
                    model=self.model_name,
                )


class ModelRegistry:
    """Registry for model capabilities and validation."""

    _default_instance: Optional["ModelRegistry"] = None
    # Pre-compile regex patterns for improved performance
    _DATE_PATTERN = re.compile(r"^(.*)-(\d{4}-\d{2}-\d{2})$")
    _IS_DATED_MODEL_PATTERN = re.compile(r".*-\d{4}-\d{2}-\d{2}$")
    _instance_lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "ModelRegistry":
        """Get the default registry instance.

        Prefer :py:meth:`get_default` for clarity; this alias remains for
        brevity and historical usage but is *not* a separate code path.

        Returns:
            The singleton :class:`ModelRegistry` instance.
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
        self._constraints: Dict[str, Union[NumericConstraint, EnumConstraint, ObjectConstraint]] = {}
        self._capabilities_lock = threading.RLock()
        # Stats for last load/dump operations (for observability)
        self._last_load_stats: Dict[str, Any] = {}

        # Initialize DataManager for model and overrides data
        self._data_manager = DataManager()

        # Set up caching for get_capabilities
        self.get_capabilities = functools.lru_cache(maxsize=self.config.cache_size)(self._get_capabilities_impl)

        # Auto-copy default constraint files to user directory if they don't exist
        if not config or not config.constraints_path:
            try:
                copy_default_to_user_config(PARAM_CONSTRAINTS_FILENAME)
            except OSError as e:
                log_warning(
                    LogEvent.MODEL_REGISTRY,
                    f"Failed to copy default constraint config: {e}",
                    error=str(e),
                )

        # Check for data updates if auto_update is enabled
        if self.config.auto_update and self._data_manager.should_update_data():
            try:
                success = self._data_manager.check_for_updates()
                if success:
                    log_info(
                        LogEvent.MODEL_REGISTRY,
                        "Auto-update completed successfully",
                    )
                    # Reload capabilities after successful auto-update
                    self._load_capabilities()
            except Exception as e:
                log_warning(
                    LogEvent.MODEL_REGISTRY,
                    f"Failed to auto-update data: {e}",
                    error=str(e),
                )

        self._load_constraints()
        self._load_capabilities()

    def _load_config(self) -> ConfigResult:
        """Load model configuration from file using DataManager.

        Returns:
            ConfigResult: Result of the configuration loading operation
        """
        try:
            # Use DataManager to get models.yaml content
            content = self._data_manager.get_data_file_content("models.yaml")
            if content is None:
                error_msg = "Could not load models.yaml from DataManager"
                log_error(
                    LogEvent.MODEL_REGISTRY,
                    error_msg,
                )
                return ConfigResult(
                    success=False,
                    error=error_msg,
                    path="models.yaml",
                )

            # Validate YAML content before parsing
            if not content.strip():
                error_msg = "models.yaml file is empty"
                log_error(
                    LogEvent.MODEL_REGISTRY,
                    error_msg,
                    path="models.yaml",
                )
                return ConfigResult(
                    success=False,
                    error=error_msg,
                    path="models.yaml",
                )

            # Check for obvious corruption patterns
            if "&" in content and "*" in content:
                # This is a heuristic check for YAML anchors and references
                # which can cause circular reference issues
                try:
                    # Try to detect circular references by checking for repeated anchor patterns
                    import re

                    anchor_pattern = r"&(\w+)"
                    reference_pattern = r"\*(\w+)"

                    anchors = set(re.findall(anchor_pattern, content))
                    references = set(re.findall(reference_pattern, content))

                    # If we have self-referencing anchors, it's likely circular
                    for anchor in anchors:
                        if anchor in references:
                            # Additional check: look for patterns like "&anchor\n  key: *anchor"
                            circular_pattern = rf"&{anchor}.*?\*{anchor}"
                            if re.search(circular_pattern, content, re.DOTALL):
                                error_msg = f"Detected circular reference in YAML with anchor '{anchor}'"
                                log_error(
                                    LogEvent.MODEL_REGISTRY,
                                    error_msg,
                                    path="models.yaml",
                                )
                                return ConfigResult(
                                    success=False,
                                    error=error_msg,
                                    path="models.yaml",
                                )
                except Exception:
                    # If our heuristic check fails, continue with normal parsing
                    pass

            data = yaml.safe_load(content)

            # Additional validation after YAML parsing
            if data is None:
                error_msg = "YAML parsing resulted in None - file may be corrupted"
                log_error(
                    LogEvent.MODEL_REGISTRY,
                    error_msg,
                    path="models.yaml",
                )
                return ConfigResult(
                    success=False,
                    error=error_msg,
                    path="models.yaml",
                )

            if not isinstance(data, dict):
                error_msg = (
                    f"Invalid configuration format in models.yaml: expected dictionary, got {type(data).__name__}"
                )
                log_error(
                    LogEvent.MODEL_REGISTRY,
                    error_msg,
                    path="models.yaml",
                )
                return ConfigResult(
                    success=False,
                    error=error_msg,
                    path="models.yaml",
                )

            # Load and apply provider overrides
            try:
                overrides_data = self._load_overrides()
                if overrides_data:
                    data = self._apply_overrides(data, overrides_data)
            except Exception as e:
                log_warning(
                    LogEvent.MODEL_REGISTRY,
                    f"Failed to load or apply overrides: {e}",
                    error=str(e),
                )

            # Schema version is declared inside the YAML itself; the loader
            # supports schema v1.x with top-level ``models`` mapping.
            return ConfigResult(success=True, data=data, path="models.yaml")
        except yaml.YAMLError as e:
            error_msg = f"YAML parsing error in models.yaml: {e}"
            log_error(
                LogEvent.MODEL_REGISTRY,
                error_msg,
                path="models.yaml",
            )
            return ConfigResult(
                success=False,
                error=error_msg,
                exception=e,
                path="models.yaml",
            )
        except Exception as e:
            error_msg = f"Error loading model registry config: {e}"
            log_warning(
                LogEvent.MODEL_REGISTRY,
                error_msg,
            )
            return ConfigResult(
                success=False,
                error=error_msg,
                exception=e,
                path="models.yaml",
            )

    def _load_overrides(self) -> Optional[Dict[str, Any]]:
        """Load provider overrides from overrides.yaml.

        Returns:
            Dictionary containing overrides data, or None if not available
        """
        try:
            content = self._data_manager.get_data_file_content("overrides.yaml")
            if content is None:
                log_info(
                    LogEvent.MODEL_REGISTRY,
                    "No overrides.yaml file available",
                )
                return None

            if not content.strip():
                log_warning(
                    LogEvent.MODEL_REGISTRY,
                    "overrides.yaml file is empty",
                )
                return None

            data = yaml.safe_load(content)
            if not isinstance(data, dict):
                log_warning(
                    LogEvent.MODEL_REGISTRY,
                    f"Invalid overrides format: expected dictionary, got {type(data).__name__}",
                )
                return None

            return data
        except yaml.YAMLError as e:
            log_warning(
                LogEvent.MODEL_REGISTRY,
                f"YAML parsing error in overrides.yaml: {e}",
            )
            return None
        except Exception as e:
            log_warning(
                LogEvent.MODEL_REGISTRY,
                f"Error loading overrides.yaml: {e}",
            )
            return None

    def _apply_overrides(self, base_data: Dict[str, Any], overrides_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply provider overrides to base model data.

        Args:
            base_data: Base model configuration data
            overrides_data: Provider overrides data

        Returns:
            Updated model configuration with overrides applied
        """
        if "overrides" not in overrides_data:
            log_warning(
                LogEvent.MODEL_REGISTRY,
                "No 'overrides' key found in overrides.yaml",
            )
            return base_data

        # Get provider from environment variable, default to OpenAI
        import os

        provider = os.getenv("OMR_PROVIDER", "openai").lower()

        # Validate provider
        if provider not in ["openai", "azure"]:
            log_warning(
                LogEvent.MODEL_REGISTRY,
                f"Invalid provider '{provider}', defaulting to 'openai'",
            )
            provider = "openai"
        provider_overrides = overrides_data["overrides"].get(provider)

        if not provider_overrides:
            if provider != "openai":
                log_info(
                    LogEvent.MODEL_REGISTRY,
                    f"No overrides found for provider '{provider}', using base OpenAI data",
                )
            # For OpenAI provider, no overrides is expected - return base data
            return base_data

        if "models" not in provider_overrides:
            log_warning(
                LogEvent.MODEL_REGISTRY,
                f"No 'models' section found in {provider} overrides",
            )
            return base_data

        # Deep copy base data to avoid modifying original
        import copy

        result_data = copy.deepcopy(base_data)

        # Apply model-specific overrides
        for model_name, override_config in provider_overrides["models"].items():
            if model_name in result_data.get("models", {}):
                self._merge_model_override(result_data["models"][model_name], override_config)
                log_info(
                    LogEvent.MODEL_REGISTRY,
                    f"Applied {provider} overrides to model '{model_name}'",
                )

        return result_data

    def _merge_model_override(self, base_model: Dict[str, Any], override_config: Dict[str, Any]) -> None:
        """Merge override configuration into base model configuration.

        Args:
            base_model: Base model configuration (modified in place)
            override_config: Override configuration to merge
        """
        for key, value in override_config.items():
            if key == "pricing" and isinstance(value, dict) and isinstance(base_model.get("pricing"), dict):
                # Merge pricing information
                base_model["pricing"].update(value)
            elif key == "capabilities" and isinstance(value, dict):
                # Replace or merge capabilities
                if "capabilities" not in base_model:
                    base_model["capabilities"] = {}
                base_model["capabilities"].update(value)
            elif key == "parameters" and isinstance(value, dict) and isinstance(base_model.get("parameters"), dict):
                # Merge parameters
                base_model["parameters"].update(value)
            else:
                # For other keys, replace entirely
                base_model[key] = value

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

                # Handle nested structure: numeric_constraints and enum_constraints
                for category_name, category_data in data.items():
                    if not isinstance(category_data, dict):
                        log_error(
                            LogEvent.MODEL_REGISTRY,
                            f"Constraint category '{category_name}' must be a dictionary",
                            category=category_data,
                        )
                        continue

                    # Process each constraint in the category
                    for constraint_name, constraint in category_data.items():
                        if not isinstance(constraint, dict):
                            log_error(
                                LogEvent.MODEL_REGISTRY,
                                f"Constraint '{constraint_name}' must be a dictionary",
                                constraint=constraint,
                            )
                            continue

                        constraint_type = constraint.get("type", "")
                        if not constraint_type:
                            log_error(
                                LogEvent.MODEL_REGISTRY,
                                f"Constraint '{constraint_name}' missing required 'type' field",
                                constraint=constraint,
                            )
                            continue

                        # Create full reference name (e.g., "numeric_constraints.temperature")
                        full_ref = f"{category_name}.{constraint_name}"

                        if constraint_type == "numeric":
                            min_value = constraint.get("min_value")
                            max_value = constraint.get("max_value")
                            allow_float = constraint.get("allow_float", True)
                            allow_int = constraint.get("allow_int", True)
                            description = constraint.get("description", "")

                            # Type validation
                            if min_value is not None and not isinstance(min_value, (int, float)):
                                log_error(
                                    LogEvent.MODEL_REGISTRY,
                                    f"Constraint '{constraint_name}' has non-numeric 'min_value' value",
                                    min_value=min_value,
                                )
                                continue

                            if max_value is not None and not isinstance(max_value, (int, float)):
                                log_error(
                                    LogEvent.MODEL_REGISTRY,
                                    f"Constraint '{constraint_name}' has non-numeric 'max_value' value",
                                    max_value=max_value,
                                )
                                continue

                            if not isinstance(allow_float, bool) or not isinstance(allow_int, bool):
                                log_error(
                                    LogEvent.MODEL_REGISTRY,
                                    f"Constraint '{constraint_name}' has non-boolean 'allow_float' or 'allow_int'",
                                    allow_float=allow_float,
                                    allow_int=allow_int,
                                )
                                continue

                            # Create constraint
                            self._constraints[full_ref] = NumericConstraint(
                                min_value=min_value if min_value is not None else 0.0,
                                max_value=max_value,
                                allow_float=allow_float,
                                allow_int=allow_int,
                                description=description,
                            )
                        elif constraint_type == "enum":
                            allowed_values = constraint.get("allowed_values")
                            description = constraint.get("description", "")

                            # Required field validation
                            if allowed_values is None:
                                log_error(
                                    LogEvent.MODEL_REGISTRY,
                                    f"Constraint '{constraint_name}' missing required 'allowed_values' field",
                                    constraint=constraint,
                                )
                                continue

                            # Type validation
                            if not isinstance(allowed_values, list):
                                log_error(
                                    LogEvent.MODEL_REGISTRY,
                                    f"Constraint '{constraint_name}' has non-list 'allowed_values' field",
                                    allowed_values=allowed_values,
                                )
                                continue

                            # Validate all values are strings
                            if not all(isinstance(val, str) for val in allowed_values):
                                log_error(
                                    LogEvent.MODEL_REGISTRY,
                                    f"Constraint '{constraint_name}' has non-string values in 'allowed_values' list",
                                    allowed_values=allowed_values,
                                )
                                continue

                            # Create constraint
                            self._constraints[full_ref] = EnumConstraint(
                                allowed_values=allowed_values,
                                description=description,
                            )
                        elif constraint_type == "object":
                            # Implementation for object constraint type
                            description = constraint.get("description", "")
                            required_keys = constraint.get("required_keys", [])
                            allowed_keys = constraint.get("allowed_keys")

                            # Type validation
                            if not isinstance(required_keys, list):
                                log_error(
                                    LogEvent.MODEL_REGISTRY,
                                    f"Constraint '{constraint_name}' has non-list 'required_keys' field",
                                    required_keys=required_keys,
                                )
                                continue

                            if allowed_keys is not None and not isinstance(allowed_keys, list):
                                log_error(
                                    LogEvent.MODEL_REGISTRY,
                                    f"Constraint '{constraint_name}' has non-list 'allowed_keys' field",
                                    allowed_keys=allowed_keys,
                                )
                                continue

                            # Create constraint
                            self._constraints[full_ref] = ObjectConstraint(
                                description=description,
                                required_keys=required_keys,
                                allowed_keys=allowed_keys,
                            )
                        else:
                            log_error(
                                LogEvent.MODEL_REGISTRY,
                                f"Unknown constraint type '{constraint_type}' for '{constraint_name}'",
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
        # Abort if configuration failed to load
        if not config_result.success or config_result.data is None:
            log_error(
                LogEvent.MODEL_REGISTRY,
                "Failed to load registry configuration",
                path=self.config.registry_path,
                error=getattr(config_result, "error", None),
            )
            return

        # -------------------------------
        # Schema version detection
        # -------------------------------
        from .schema_version import SchemaVersionValidator

        try:
            # Get and validate schema version
            schema_version = SchemaVersionValidator.get_schema_version(config_result.data)

            # Log schema version detection
            from .logging import log_info

            log_info(
                LogEvent.MODEL_REGISTRY,
                "Schema version detected",
                version=schema_version,
                compatible_range=SchemaVersionValidator.get_compatible_range(schema_version),
                path=config_result.path,
            )

            # Check compatibility
            if not SchemaVersionValidator.is_compatible_schema(schema_version):
                log_error(
                    LogEvent.MODEL_REGISTRY,
                    "Unsupported schema version",
                    version=schema_version,
                    supported_ranges=list(SchemaVersionValidator.SUPPORTED_SCHEMA_VERSIONS.values()),
                    path=config_result.path,
                )
                return

            # Validate structure matches version
            if not SchemaVersionValidator.validate_schema_structure(config_result.data, schema_version):
                log_error(
                    LogEvent.MODEL_REGISTRY,
                    "Schema structure validation failed",
                    version=schema_version,
                    path=config_result.path,
                )
                return

            # Route to appropriate loader
            loader_method = SchemaVersionValidator.get_loader_method_name(schema_version)
            if loader_method and hasattr(self, loader_method):
                getattr(self, loader_method)(config_result.data.get("models", {}))
                return
            else:
                log_error(
                    LogEvent.MODEL_REGISTRY,
                    "No loader available for schema version",
                    version=schema_version,
                    path=config_result.path,
                )
                return

        except ValueError as e:
            log_error(
                LogEvent.MODEL_REGISTRY,
                "Schema version validation failed",
                error=str(e),
                path=config_result.path,
            )
            return

    def _load_capabilities_modern(self, models_data: Dict[str, Any]) -> None:
        """Load capabilities from modern schema (1.x) where models are top-level.

        The modern schema (1.0.0+) places every model – base or dated – as a
        direct child of the ``models`` mapping and groups feature flags beneath
        a ``capabilities`` key. This helper converts the structure into
        the ``ModelCapabilities`` dataclass so the public API remains
        unchanged.
        """
        from datetime import date, datetime

        loaded_count: int = 0
        skipped_count: int = 0
        first_error: Optional[str] = None

        for model_name, model_config in models_data.items():
            try:
                # -------------------
                # Context window size
                # -------------------
                context_window_raw = model_config.get("context_window", 0)
                if isinstance(context_window_raw, dict):
                    context_window = int(context_window_raw.get("total", 0) or 0)
                    output_tokens_raw = context_window_raw.get("output") or model_config.get("max_output_tokens", 0)
                    max_output_tokens = int(output_tokens_raw or 0)
                else:
                    context_window = int(context_window_raw or 0)
                    max_output_tokens = int(model_config.get("max_output_tokens", 0) or 0)

                # -------------
                # Capabilities
                # -------------
                caps_block: Dict[str, Any] = model_config.get("capabilities", {})

                supports_vision = bool(
                    caps_block.get(
                        "supports_vision",
                        model_config.get("supports_vision", False),
                    )
                )
                supports_functions = bool(
                    caps_block.get(
                        "supports_function_calling",
                        model_config.get("supports_functions", False),
                    )
                )
                supports_streaming = bool(
                    caps_block.get(
                        "supports_streaming",
                        model_config.get("supports_streaming", False),
                    )
                )
                supports_structured = bool(
                    caps_block.get(
                        "supports_structured_output",
                        model_config.get("supports_structured", False),
                    )
                )
                supports_web_search = bool(
                    caps_block.get(
                        "supports_web_search",
                        model_config.get("supports_web_search", False),
                    )
                )
                supports_audio = bool(
                    caps_block.get(
                        "supports_audio",
                        model_config.get("supports_audio", False),
                    )
                )
                supports_json_mode = bool(
                    caps_block.get(
                        "supports_json_mode",
                        model_config.get("supports_json_mode", False),
                    )
                )

                # -------------
                # Deprecation
                # -------------
                dep_block: Dict[str, Any] = model_config.get("deprecation", {})
                dep_status = dep_block.get("status", "active")

                def _parse_date(val: Any) -> Optional[date]:
                    if val in (None, "", "null"):
                        return None
                    try:
                        return datetime.fromisoformat(str(val)).date()
                    except Exception:
                        return None

                deprecates_on = _parse_date(dep_block.get("deprecates_on"))
                sunsets_on = _parse_date(dep_block.get("sunsets_on")) or _parse_date(dep_block.get("sunset_date"))

                deprecation = DeprecationInfo(
                    status=dep_status,
                    deprecates_on=deprecates_on,
                    sunsets_on=sunsets_on,
                    replacement=dep_block.get("replacement"),
                    migration_guide=dep_block.get("migration_guide"),
                    reason=dep_block.get("reason", dep_status),
                )

                # -------------
                # Min version
                # -------------
                min_version_data = model_config.get("min_version")
                min_version: Optional[ModelVersion] = None
                if min_version_data:
                    try:
                        if isinstance(min_version_data, dict):
                            year = min_version_data.get("year")
                            month = min_version_data.get("month")
                            day = min_version_data.get("day")
                            if year and month and day:
                                min_version = ModelVersion(year=year, month=month, day=day)
                        else:
                            min_version = ModelVersion.from_string(str(min_version_data))
                    except (ValueError, TypeError):
                        # Ignore bad min_version values
                        min_version = None

                # ----------------------
                # Supported parameters
                # ----------------------
                param_refs: List[ParameterReference] = []

                # Extract parameters from parameters block
                parameters_block = model_config.get("parameters", {})
                if parameters_block and isinstance(parameters_block, dict):
                    for param_name, param_config in parameters_block.items():
                        if isinstance(param_config, dict):
                            # Create parameter reference
                            param_refs.append(
                                ParameterReference(
                                    ref=param_name,
                                    description=f"Parameter {param_name}",
                                )
                            )
                    # If we collected inline parameters but there were no explicit supported_parameters,
                    # use the inline list as supported parameters to allow validation.
                    if not param_refs:
                        for param_name in parameters_block.keys():
                            param_refs.append(ParameterReference(ref=param_name, description=f"Parameter {param_name}"))

                # Note: legacy 'supported_parameters' is intentionally not supported.

                # -------------
                # Pricing block
                # -------------
                pricing_block = model_config.get("pricing")
                pricing_obj: Optional[PricingInfo] = None
                if isinstance(pricing_block, dict):
                    try:
                        # Support both unified pricing (scheme/unit) and legacy per-million-token keys
                        if "scheme" in pricing_block and "unit" in pricing_block:
                            pricing_obj = PricingInfo(
                                scheme=typing.cast(
                                    typing.Literal[
                                        "per_token",
                                        "per_minute",
                                        "per_image",
                                        "per_request",
                                    ],
                                    str(pricing_block.get("scheme")),
                                ),
                                unit=typing.cast(
                                    typing.Literal[
                                        "million_tokens",
                                        "minute",
                                        "image",
                                        "request",
                                    ],
                                    str(pricing_block.get("unit")),
                                ),
                                input_cost_per_unit=float(pricing_block.get("input_cost_per_unit", 0.0)),
                                output_cost_per_unit=float(pricing_block.get("output_cost_per_unit", 0.0)),
                                currency=str(pricing_block.get("currency", "USD")),
                                tiers=typing.cast(
                                    typing.Optional[typing.List[typing.Dict[str, typing.Any]]],
                                    pricing_block.get("tiers"),
                                ),
                            )
                        else:
                            # Legacy support (pre-unified): interpret as per_token/million_tokens
                            pricing_obj = PricingInfo(
                                scheme="per_token",
                                unit="million_tokens",
                                input_cost_per_unit=float(pricing_block.get("input_cost_per_million_tokens", 0.0)),
                                output_cost_per_unit=float(pricing_block.get("output_cost_per_million_tokens", 0.0)),
                                currency=str(pricing_block.get("currency", "USD")),
                            )
                    except Exception as e:  # pragma: no cover
                        log_warning(
                            LogEvent.MODEL_REGISTRY,
                            "Invalid pricing block ignored",
                            model=model_name,
                            error=str(e),
                        )

                # -------------
                # Web search billing block (optional)
                # -------------
                web_search_billing: Optional[WebSearchBilling] = None
                billing_block = model_config.get("billing")
                if isinstance(billing_block, dict):
                    ws = billing_block.get("web_search")
                    if isinstance(ws, dict):
                        try:
                            policy = str(ws.get("content_token_policy", "")).strip()
                            if policy in {"included_in_call_fee", "billed_at_model_rate"}:
                                web_search_billing = WebSearchBilling(
                                    call_fee_per_1000=float(ws.get("call_fee_per_1000", 0.0)),
                                    content_token_policy=policy,  # type: ignore[arg-type]
                                    currency=str(ws.get("currency", "USD")),
                                    notes=str(ws.get("notes")) if "notes" in ws else None,
                                )
                        except Exception:
                            web_search_billing = None

                # -------------
                # Build object
                # -------------
                capabilities = ModelCapabilities(
                    model_name=model_name,
                    openai_model_name=model_config.get("openai_name", model_name),
                    context_window=context_window,
                    max_output_tokens=max_output_tokens,
                    deprecation=deprecation,
                    supports_vision=supports_vision,
                    supports_functions=supports_functions,
                    supports_streaming=supports_streaming,
                    supports_structured=supports_structured,
                    supports_web_search=supports_web_search,
                    supports_audio=supports_audio,
                    supports_json_mode=supports_json_mode,
                    pricing=pricing_obj,
                    input_modalities=model_config.get("input_modalities"),
                    output_modalities=model_config.get("output_modalities"),
                    min_version=min_version,
                    aliases=[],
                    supported_parameters=param_refs,
                    constraints=copy.deepcopy(self._constraints),
                    inline_parameters=parameters_block,
                    web_search_billing=web_search_billing,
                )

                with self._capabilities_lock:
                    self._capabilities[model_name] = capabilities
                loaded_count += 1
            except Exception as e:  # pragma: no cover – best-effort parsing
                if first_error is None:
                    first_error = f"{type(e).__name__}: {e}"
                skipped_count += 1
                log_warning(
                    LogEvent.MODEL_REGISTRY,
                    "Failed to load model capabilities",
                    model=model_name,
                    error=str(e),
                )

        # Bookkeep and log summary for observability
        try:
            self._last_load_stats = {
                "total": len(models_data),
                "loaded": loaded_count,
                "skipped": skipped_count,
                "first_error": first_error,
            }
        except Exception:
            pass

        log_info(
            LogEvent.MODEL_REGISTRY,
            "Model load summary",
            total=len(models_data),
            loaded=loaded_count,
            skipped=skipped_count,
        )

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
        with self._capabilities_lock:
            if model in self._capabilities:
                return self._capabilities[model]

        # Check if this is a versioned model
        version_match = self._DATE_PATTERN.match(model)
        if version_match:
            base_name = version_match.group(1)
            version_str = version_match.group(2)

            # Find all capabilities for this base model
            with self._capabilities_lock:
                model_versions = [(k, v) for k, v in self._capabilities.items() if k.startswith(f"{base_name}-")]

            if not model_versions:
                # No versions found for this base model
                # Find aliases that might provide a valid alternative
                with self._capabilities_lock:
                    aliases = [
                        name for name in self._capabilities.keys() if not self._IS_DATED_MODEL_PATTERN.match(name)
                    ]

                # Find if any alias might match the base model
                matching_aliases = [alias for alias in aliases if alias == base_name]

                if matching_aliases:
                    raise ModelNotSupportedError(
                        f"Model '{model}' not found.",
                        model=model,
                        available_models=matching_aliases,
                    )
                else:
                    # No matching aliases either
                    with self._capabilities_lock:
                        available_base_models: set[str] = set(
                            k for k in self._capabilities.keys() if not self._IS_DATED_MODEL_PATTERN.match(k)
                        )
                    raise ModelNotSupportedError(
                        f"Model '{model}' not found. Available base models: {', '.join(sorted(available_base_models))}",
                        model=model,
                        available_models=list(available_base_models),
                    )

            try:
                # Parse version
                requested_version = ModelVersion.from_string(version_str)
            except ValueError as e:
                raise InvalidDateError(str(e))

            # Find the model with the minimum version
            for _unused, caps in model_versions:
                if caps.min_version and requested_version < caps.min_version:
                    raise VersionTooOldError(
                        f"Model version '{model}' is older than the minimum supported "
                        f"version {caps.min_version} for {base_name}.",
                        model=model,
                        min_version=str(caps.min_version),
                        alias=None,
                    )

            # Find the best matching model
            base_model_caps = None
            for _dated_model, caps in model_versions:
                if base_model_caps is None or (
                    caps.min_version
                    and caps.min_version <= requested_version
                    and (not base_model_caps.min_version or caps.min_version > base_model_caps.min_version)
                ):
                    base_model_caps = caps

            if base_model_caps:
                # Create a copy with the requested model name
                new_caps = ModelCapabilities(
                    model_name=base_model_caps.model_name,
                    openai_model_name=model,
                    context_window=base_model_caps.context_window,
                    max_output_tokens=base_model_caps.max_output_tokens,
                    deprecation=base_model_caps.deprecation,
                    supports_vision=base_model_caps.supports_vision,
                    supports_functions=base_model_caps.supports_functions,
                    supports_streaming=base_model_caps.supports_streaming,
                    supports_structured=base_model_caps.supports_structured,
                    supports_web_search=base_model_caps.supports_web_search,
                    supports_audio=base_model_caps.supports_audio,
                    supports_json_mode=base_model_caps.supports_json_mode,
                    pricing=base_model_caps.pricing,
                    input_modalities=base_model_caps.input_modalities,
                    output_modalities=base_model_caps.output_modalities,
                    min_version=base_model_caps.min_version,
                    aliases=base_model_caps.aliases,
                    supported_parameters=base_model_caps.supported_parameters,
                    constraints=base_model_caps._constraints,
                )
                return new_caps

        # If we get here, the model is not supported
        with self._capabilities_lock:
            available_models: set[str] = set(
                k for k in self._capabilities.keys() if not self._IS_DATED_MODEL_PATTERN.match(k)
            )
        raise ModelNotSupportedError(
            f"Model '{model}' not found. Available base models: {', '.join(sorted(available_models))}",
            model=model,
            available_models=list(available_models),
        )

    def get_parameter_constraint(self, ref: str) -> Union[NumericConstraint, EnumConstraint, ObjectConstraint]:
        """Get a parameter constraint by reference.

        Args:
            ref: Reference string (e.g., "numeric_constraints.temperature")

        Returns:
            The constraint object (NumericConstraint or EnumConstraint or ObjectConstraint)

        Raises:
            ConstraintNotFoundError: If the constraint is not found
        """
        if ref not in self._constraints:
            raise ConstraintNotFoundError(
                f"Constraint reference '{ref}' not found in registry",
                ref=ref,
            )
        return self._constraints[ref]

    def assert_model_active(self, model: str) -> None:
        """Assert that a model is active and warn if deprecated.

        Args:
            model: Model name to check

        Raises:
            ModelSunsetError: If the model is sunset
            ModelNotSupportedError: If the model is not found

        Warns:
            DeprecationWarning: If the model is deprecated
        """
        capabilities = self.get_capabilities(model)
        assert_model_active(model, capabilities.deprecation)

    def get_sunset_headers(self, model: str) -> dict[str, str]:
        """Get RFC-compliant HTTP headers for model deprecation status.

        Args:
            model: Model name

        Returns:
            Dictionary of HTTP headers

        Raises:
            ModelNotSupportedError: If the model is not found
        """
        capabilities = self.get_capabilities(model)
        return sunset_headers(capabilities.deprecation)

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
                            headers["If-Modified-Since"] = metadata["last_modified"]
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
                path=str(meta_path),  # Convert to string in case meta_path is None
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

        # Check required sections for both schema versions
        if "models" in config:
            # New schema – nothing else to validate here for presence
            pass
        else:
            raise ValueError("Remote configuration missing 'models' section")

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
        try:
            # Get remote config
            config_url = url or (
                "https://raw.githubusercontent.com/yaniv-golan/openai-model-registry/main/data/models.yaml"
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

            # Check for updates only if not forcing and not validating
            if not force:
                result = self.check_for_updates(url=url)
                if result.status == RefreshStatus.ALREADY_CURRENT:
                    return RefreshResult(
                        success=True,
                        status=RefreshStatus.ALREADY_CURRENT,
                        message="Registry is already up to date",
                    )

            # Use DataManager to handle the update
            try:
                # Force update through DataManager
                if self._data_manager.force_update():
                    log_info(
                        LogEvent.MODEL_REGISTRY,
                        "Successfully updated registry data via DataManager",
                    )
                else:
                    # Fallback to manual update if DataManager fails
                    # Note: This fallback has limitations - it only updates models.yaml
                    # without overrides.yaml or checksums.txt, which may cause desync
                    log_warning(
                        LogEvent.MODEL_REGISTRY,
                        "DataManager update failed, using limited fallback (models.yaml only)",
                    )
                    target_path = get_user_data_dir() / "models.yaml"
                    with open(target_path, "w") as f:
                        yaml.safe_dump(remote_config, f)

                    # Try to download overrides.yaml and checksums.txt if possible
                    try:
                        overrides_url = "https://raw.githubusercontent.com/yaniv-golan/openai-model-registry/main/data/overrides.yaml"
                        checksums_url = "https://raw.githubusercontent.com/yaniv-golan/openai-model-registry/main/data/checksums.txt"

                        # Simple fallback downloads with checksum verification
                        try:
                            import requests
                        except ImportError:
                            requests = None  # type: ignore

                        if requests is not None:
                            try:
                                # Download checksums.txt first for verification
                                checksums_resp = requests.get(checksums_url, timeout=30)
                                if checksums_resp.status_code == 200:
                                    checksums_content = checksums_resp.text
                                    checksums_path = get_user_data_dir() / "checksums.txt"

                                    # Parse checksums for verification
                                    checksums = {}
                                    for line in checksums_content.strip().split("\n"):
                                        if line.strip() and " " in line:
                                            parts = line.strip().split(" ", 1)
                                            if len(parts) == 2:
                                                checksums[parts[1]] = parts[0]

                                    # Download overrides.yaml
                                    overrides_resp = requests.get(overrides_url, timeout=30)
                                    if overrides_resp.status_code == 200:
                                        overrides_content = overrides_resp.text

                                        # Verify checksum if available
                                        if "overrides.yaml" in checksums:
                                            import hashlib

                                            actual_hash = hashlib.sha256(overrides_content.encode()).hexdigest()
                                            expected_hash = checksums["overrides.yaml"]

                                            if actual_hash == expected_hash:
                                                overrides_path = get_user_data_dir() / "overrides.yaml"
                                                with open(overrides_path, "w") as f:
                                                    f.write(overrides_content)
                                                log_info(
                                                    LogEvent.MODEL_REGISTRY,
                                                    "Downloaded and verified overrides.yaml in fallback",
                                                )
                                            else:
                                                log_warning(
                                                    LogEvent.MODEL_REGISTRY,
                                                    f"Checksum mismatch for overrides.yaml in fallback: expected {expected_hash}, got {actual_hash}",
                                                )
                                        else:
                                            # No checksum available, save anyway but warn
                                            overrides_path = get_user_data_dir() / "overrides.yaml"
                                            with open(overrides_path, "w") as f:
                                                f.write(overrides_content)
                                            log_warning(
                                                LogEvent.MODEL_REGISTRY,
                                                "Downloaded overrides.yaml in fallback without checksum verification",
                                            )

                                    # Save checksums.txt after successful verification
                                    with open(checksums_path, "w") as f:
                                        f.write(checksums_content)
                                    log_info(LogEvent.MODEL_REGISTRY, "Downloaded checksums.txt in fallback")

                            except requests.RequestException as e:
                                log_warning(
                                    LogEvent.MODEL_REGISTRY,
                                    f"Failed to download additional files in fallback: {e}",
                                )
                    except Exception as e:
                        log_warning(
                            LogEvent.MODEL_REGISTRY,
                            f"Error in fallback additional file download: {e}",
                        )
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

        # Set up the URL with fallback handling
        primary_url = url or (
            "https://raw.githubusercontent.com/yaniv-golan/openai-model-registry/main/data/models.yaml"
        )

        # Define fallback URLs in case primary fails
        fallback_urls = [
            "https://github.com/yaniv-golan/openai-model-registry/raw/main/data/models.yaml",
        ]

        urls_to_try = [primary_url] + fallback_urls

        try:
            # Use a lock when checking and comparing versions to prevent race conditions
            with self.__class__._instance_lock:
                # First check with DataManager
                if self._data_manager.should_update_data():
                    latest_release = self._data_manager._fetch_latest_data_release()
                    if latest_release:
                        latest_version = latest_release.get("tag_name", "")
                        current_version = self._data_manager._get_current_version()
                        if (
                            current_version
                            and self._data_manager._compare_versions(latest_version, current_version) <= 0
                        ):
                            return RefreshResult(
                                success=True,
                                status=RefreshStatus.ALREADY_CURRENT,
                                message=f"Registry is up to date (version {current_version})",
                            )
                        else:
                            return RefreshResult(
                                success=True,
                                status=RefreshStatus.UPDATE_AVAILABLE,
                                message=f"Update available: {current_version or 'bundled'} -> {latest_version}",
                            )

                # Fallback to original HTTP check with URL fallback
                remote_config = None
                for config_url in urls_to_try:
                    try:
                        response = requests.get(config_url, timeout=10)
                        response.raise_for_status()

                        # Parse the remote config
                        remote_config = yaml.safe_load(response.text)
                        if isinstance(remote_config, dict):
                            break
                        else:
                            log_warning(
                                LogEvent.MODEL_REGISTRY,
                                f"Remote config from {config_url} is not a valid dictionary",
                            )
                    except (requests.RequestException, yaml.YAMLError) as e:
                        log_warning(
                            LogEvent.MODEL_REGISTRY,
                            f"Failed to fetch from {config_url}: {e}",
                        )
                        continue

                if remote_config is None:
                    return RefreshResult(
                        success=False,
                        status=RefreshStatus.ERROR,
                        message="Could not fetch remote config from any URL",
                    )

                # Get local config for comparison
                local_config = self._load_config()
                if not local_config.success:
                    return RefreshResult(
                        success=False,
                        status=RefreshStatus.ERROR,
                        message=f"Could not load local config: {local_config.error}",
                    )

                # Compare versions (simplified comparison)
                remote_version = remote_config.get("version", "unknown")
                local_version = local_config.data.get("version", "unknown") if local_config.data else "unknown"

                if remote_version == local_version:
                    return RefreshResult(
                        success=True,
                        status=RefreshStatus.ALREADY_CURRENT,
                        message=f"Registry is up to date (version {local_version})",
                    )
                else:
                    return RefreshResult(
                        success=True,
                        status=RefreshStatus.UPDATE_AVAILABLE,
                        message=f"Update available: {local_version} -> {remote_version}",
                    )

        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return RefreshResult(
                    success=False,
                    status=RefreshStatus.ERROR,
                    message="Registry not found at any of the configured URLs",
                )
            else:
                return RefreshResult(
                    success=False,
                    status=RefreshStatus.ERROR,
                    message=f"HTTP error {e.response.status_code}: {e}",
                )
        except requests.RequestException as e:
            return RefreshResult(
                success=False,
                status=RefreshStatus.ERROR,
                message=f"Network error: {e}",
            )
        except Exception as e:
            return RefreshResult(
                success=False,
                status=RefreshStatus.ERROR,
                message=f"Unexpected error: {e}",
            )

    def check_data_updates(self) -> bool:
        """Check if data updates are available using DataManager.

        Returns:
            True if updates are available, False otherwise
        """
        try:
            if not self._data_manager.should_update_data():
                return False

            latest_release = self._data_manager._fetch_latest_data_release()
            if not latest_release:
                return False

            latest_version = latest_release.get("tag_name", "")
            current_version = self._data_manager._get_current_version()

            return not (current_version and self._data_manager._compare_versions(latest_version, current_version) <= 0)
        except Exception:
            return False

    def get_update_info(self) -> UpdateInfo:
        """Get detailed information about available updates.

        Returns:
            UpdateInfo object containing update details
        """
        try:
            if not self._data_manager.should_update_data():
                return UpdateInfo(
                    update_available=False,
                    current_version=self._data_manager._get_current_version(),
                    current_version_date=None,
                    latest_version=None,
                    latest_version_date=None,
                    download_url=None,
                    update_size_estimate=None,
                    latest_version_description=None,
                    accumulated_changes=[],
                    error_message="Updates are disabled via environment variable",
                )

            latest_release = self._data_manager._fetch_latest_data_release()
            if not latest_release:
                return UpdateInfo(
                    update_available=False,
                    current_version=self._data_manager._get_current_version(),
                    current_version_date=None,
                    latest_version=None,
                    latest_version_date=None,
                    download_url=None,
                    update_size_estimate=None,
                    latest_version_description=None,
                    accumulated_changes=[],
                    error_message="No releases found on GitHub",
                )

            latest_version = latest_release.get("tag_name", "")
            current_version = self._data_manager._get_current_version()

            # Get current version info with date
            current_version_info = self._data_manager._get_current_version_info()
            current_version_date = current_version_info.get("published_at") if current_version_info else None

            update_available = not (
                current_version and self._data_manager._compare_versions(latest_version, current_version) <= 0
            )

            # Get accumulated changes between current and latest version
            accumulated_changes = []
            if update_available:
                accumulated_changes = self._data_manager.get_accumulated_changes(current_version, latest_version)

            # Estimate update size based on assets
            update_size_estimate = None
            total_size = 0
            assets = latest_release.get("assets", [])
            for asset in assets:
                if asset.get("name") in ["models.yaml", "overrides.yaml", "checksums.txt"]:
                    total_size += asset.get("size", 0)

            if total_size > 0:
                if total_size < 1024:
                    update_size_estimate = f"{total_size} bytes"
                elif total_size < 1024 * 1024:
                    update_size_estimate = f"{total_size / 1024:.1f} KB"
                else:
                    update_size_estimate = f"{total_size / (1024 * 1024):.1f} MB"

            # Extract one-sentence description from latest release body
            latest_version_description = None
            if latest_release.get("body"):
                latest_version_description = self._data_manager._extract_change_summary(latest_release.get("body", ""))

            return UpdateInfo(
                update_available=update_available,
                current_version=current_version,
                current_version_date=current_version_date,
                latest_version=latest_version,
                latest_version_date=latest_release.get("published_at"),
                download_url=latest_release.get("html_url"),
                update_size_estimate=update_size_estimate,
                latest_version_description=latest_version_description,
                accumulated_changes=accumulated_changes,
                error_message=None,
            )

        except Exception as e:
            return UpdateInfo(
                update_available=False,
                current_version=self._data_manager._get_current_version(),
                current_version_date=None,
                latest_version=None,
                latest_version_date=None,
                download_url=None,
                update_size_estimate=None,
                latest_version_description=None,
                accumulated_changes=[],
                error_message=str(e),
            )

    def update_data(self, force: bool = False) -> bool:
        """Update model registry data using DataManager.

        Args:
            force: If True, force update regardless of current version

        Returns:
            True if update was successful, False otherwise
        """
        try:
            if force:
                success = self._data_manager.force_update()
            else:
                success = self._data_manager.check_for_updates()

            if success:
                # Reload capabilities after successful update
                self._load_capabilities()

            return success
        except Exception:
            return False

    def manual_update_workflow(self, prompt_user_func: Optional[Callable[[UpdateInfo], bool]] = None) -> bool:
        """Manual update workflow with user approval.

        Args:
            prompt_user_func: Optional function to prompt user for approval.
                            Should take UpdateInfo as parameter and return bool.
                            If None, uses a default console prompt.

        Returns:
            True if update was performed, False otherwise
        """
        try:
            # Get update information
            update_info = self.get_update_info()

            if update_info.error_message:
                log_error(
                    LogEvent.MODEL_REGISTRY,
                    f"Failed to check for updates: {update_info.error_message}",
                )
                return False

            if not update_info.update_available:
                log_info(
                    LogEvent.MODEL_REGISTRY,
                    f"Registry is up to date (version {update_info.current_version or 'bundled'})",
                )
                return False

            # Use custom prompt function or default
            if prompt_user_func is None:
                prompt_user_func = self._default_update_prompt

            # Ask user for approval
            if prompt_user_func(update_info):
                log_info(
                    LogEvent.MODEL_REGISTRY,
                    f"User approved update from {update_info.current_version or 'bundled'} to {update_info.latest_version}",
                )

                # Perform the update
                success = self.update_data()

                if success:
                    log_info(
                        LogEvent.MODEL_REGISTRY,
                        f"Successfully updated to {update_info.latest_version}",
                    )
                else:
                    log_error(
                        LogEvent.MODEL_REGISTRY,
                        "Update failed",
                    )

                return success
            else:
                log_info(
                    LogEvent.MODEL_REGISTRY,
                    "User declined update",
                )
                return False

        except Exception as e:
            log_error(
                LogEvent.MODEL_REGISTRY,
                f"Manual update workflow failed: {e}",
            )
            return False

    def _default_update_prompt(self, update_info: UpdateInfo) -> bool:
        """Default console prompt for update approval.

        Args:
            update_info: Information about the available update

        Returns:
            True if user approves, False otherwise
        """
        print("\n🔄 OpenAI Model Registry Update Available")
        print(f"   Current version: {update_info.current_version or 'bundled'}")
        print(f"   Latest version:  {update_info.latest_version}")

        if update_info.current_version_date:
            print(f"   Current date:    {update_info.current_version_date}")
        if update_info.latest_version_date:
            print(f"   Latest date:     {update_info.latest_version_date}")
        if update_info.update_size_estimate:
            print(f"   Download size:   {update_info.update_size_estimate}")
        if update_info.latest_version_description:
            print(f"   Description:     {update_info.latest_version_description}")

        # Show accumulated changes
        if update_info.accumulated_changes:
            print("\n📝 Changes since your last update:")
            for change in update_info.accumulated_changes:
                print(f"   • {change['version']} ({change['date'][:10] if change['date'] else 'Unknown date'})")
                print(f"     {change['description']}")

        print(f"\n🔗 Release info: {update_info.download_url}")

        try:
            response = input("\nWould you like to update now? [y/N]: ").strip().lower()
            return response in ("y", "yes")
        except (KeyboardInterrupt, EOFError):
            return False

    def get_data_version(self) -> Optional[str]:
        """Get the current data version.

        Returns:
            Current data version string, or None if using bundled data
        """
        try:
            return self._data_manager._get_current_version()
        except Exception:
            return None

    def get_data_info(self) -> Dict[str, Any]:
        """Get information about data configuration and status.

        Returns:
            Dictionary containing data configuration information
        """
        try:
            info: Dict[str, Any] = {
                "data_directory": str(self._data_manager._data_dir),
                "current_version": self._data_manager._get_current_version(),
                "updates_enabled": self._data_manager.should_update_data(),
                "environment_variables": {
                    "OMR_DISABLE_DATA_UPDATES": os.getenv("OMR_DISABLE_DATA_UPDATES"),
                    "OMR_DATA_VERSION_PIN": os.getenv("OMR_DATA_VERSION_PIN"),
                    "OMR_DATA_DIR": os.getenv("OMR_DATA_DIR"),
                },
                "data_files": {},
            }

            # Check data file status
            for filename in ["models.yaml", "overrides.yaml"]:
                file_path = self._data_manager.get_data_file_path(filename)
                info["data_files"][filename] = {
                    "path": str(file_path) if file_path else None,
                    "exists": file_path is not None,
                    "using_bundled": file_path is None,
                }

            return info
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def cleanup() -> None:
        """Clean up the registry instance."""
        with ModelRegistry._instance_lock:
            ModelRegistry._default_instance = None

    def list_providers(self) -> List[str]:
        """List all providers available in the overrides configuration.

        Returns:
            List of provider names found in overrides data
        """
        import os

        providers = set()

        # Add the current provider
        current_provider = os.getenv("OMR_PROVIDER", "openai").lower()
        providers.add(current_provider)

        # Add providers from overrides
        if hasattr(self, "_overrides") and self._overrides:
            overrides_data = self._overrides.get("overrides", {})
            for provider_name in overrides_data.keys():
                providers.add(provider_name.lower())

        return sorted(list(providers))

    def dump_effective(self) -> Dict[str, Any]:
        """Return the fully merged provider-adjusted dataset for the current provider.

        Returns:
            Dictionary containing the effective model capabilities after provider overrides
        """
        import os
        from datetime import datetime

        current_provider = os.getenv("OMR_PROVIDER", "openai").lower()
        effective_data: Dict[str, Any] = {}
        total_models = 0
        serialized = 0
        skipped_for_dump = 0

        for model_name in self.models:
            total_models += 1
            try:
                capabilities = self.get_capabilities(model_name)
                effective_data[model_name] = {
                    "context_window": {
                        "total": capabilities.context_window,
                        "input": getattr(capabilities, "input_context_window", None),
                        "output": capabilities.max_output_tokens,
                    },
                    "pricing": (
                        {
                            "scheme": getattr(capabilities.pricing, "scheme", "per_token"),
                            "unit": getattr(capabilities.pricing, "unit", "million_tokens"),
                            "input_cost_per_unit": getattr(capabilities.pricing, "input_cost_per_unit", 0.0),
                            "output_cost_per_unit": getattr(capabilities.pricing, "output_cost_per_unit", 0.0),
                            "currency": getattr(capabilities.pricing, "currency", "USD"),
                            "tiers": getattr(capabilities.pricing, "tiers", None),
                        }
                        if getattr(capabilities, "pricing", None)
                        else {
                            "scheme": "per_token",
                            "unit": "million_tokens",
                            "input_cost_per_unit": 0.0,
                            "output_cost_per_unit": 0.0,
                            "currency": "USD",
                            "tiers": None,
                        }
                    ),
                    "supports_vision": capabilities.supports_vision,
                    "supports_function_calling": getattr(capabilities, "supports_functions", False),
                    "supports_streaming": capabilities.supports_streaming,
                    "supports_structured_output": getattr(capabilities, "supports_structured", False),
                    "supports_json_mode": getattr(capabilities, "supports_json_mode", False),
                    "supports_web_search": getattr(capabilities, "supports_web_search", False),
                    "supports_audio": getattr(capabilities, "supports_audio", False),
                    "billing": (
                        {"web_search": asdict(cast(WebSearchBilling, capabilities.web_search_billing))}
                        if getattr(capabilities, "web_search_billing", None)
                        else None
                    ),
                    "provider": current_provider,
                    "parameters": getattr(capabilities, "parameters", {}),
                    "input_modalities": getattr(
                        capabilities, "input_modalities", getattr(capabilities, "modalities", [])
                    ),
                    "output_modalities": getattr(capabilities, "output_modalities", []),
                    "deprecation": {
                        "status": capabilities.deprecation.status,
                        "deprecates_on": getattr(capabilities.deprecation, "deprecates_on", None),
                        "sunsets_on": getattr(capabilities.deprecation, "sunsets_on", None),
                        "replacement": getattr(capabilities.deprecation, "replacement", None),
                        "reason": getattr(capabilities.deprecation, "reason", None),
                        "migration_guide": getattr(capabilities.deprecation, "migration_guide", None),
                    },
                }
                serialized += 1
            except Exception as e:
                skipped_for_dump += 1
                log_warning(
                    LogEvent.MODEL_REGISTRY,
                    "Failed to serialize model for dump_effective",
                    model=model_name,
                    error=str(e),
                )

        return {
            "provider": current_provider,
            "models": effective_data,
            "metadata": {
                "schema_version": "1.0.0",
                "generated_at": str(datetime.now().isoformat()),
                "data_sources": self.get_data_info(),
                "summary": {
                    "total": total_models,
                    "serialized": serialized,
                    "skipped": skipped_for_dump,
                    "load_stats": getattr(self, "_last_load_stats", None),
                },
            },
        }

    def get_raw_data_paths(self) -> Dict[str, Optional[str]]:
        """Return canonical paths for raw data files (models.yaml and overrides.yaml).

        Returns:
            Dictionary with 'models' and 'overrides' keys containing file paths or None if bundled
        """
        import os
        from pathlib import Path

        paths: Dict[str, Optional[str]] = {}

        # Get models.yaml path
        if hasattr(self, "_data_manager"):
            # Try to get the actual file path from data manager
            user_data_dir = get_user_data_dir()
            models_path = user_data_dir / "models.yaml"
            if models_path.exists():
                paths["models"] = str(models_path)
            else:
                # Check for environment override
                env_path = os.getenv("OMR_MODEL_REGISTRY_PATH")
                if env_path and Path(env_path).exists():
                    paths["models"] = env_path
                else:
                    paths["models"] = None  # Bundled

            # Get overrides.yaml path
            overrides_path = user_data_dir / "overrides.yaml"
            if overrides_path.exists():
                paths["overrides"] = str(overrides_path)
            else:
                paths["overrides"] = None  # Bundled
        else:
            paths["models"] = None
            paths["overrides"] = None

        return paths

    def clear_cache(self, files: Optional[List[str]] = None) -> None:
        """Delete cached data files in the user data directory.

        Args:
            files: Optional list of specific files to clear. If None, clears all known cache files.
        """
        user_data_dir = get_user_data_dir()

        # Default files to clear if none specified
        if files is None:
            files = ["models.yaml", "overrides.yaml", "checksums.txt"]

        cleared_files = []
        for filename in files:
            file_path = user_data_dir / filename
            try:
                if file_path.exists():
                    file_path.unlink()
                    cleared_files.append(str(file_path))
            except (OSError, PermissionError) as e:
                log_warning(LogEvent.MODEL_REGISTRY, f"Failed to clear cache file {file_path}: {e}")

        if cleared_files:
            log_info(LogEvent.MODEL_REGISTRY, f"Cleared {len(cleared_files)} cache files: {', '.join(cleared_files)}")

    def get_bundled_data_content(self, filename: str) -> Optional[str]:
        """Get bundled data file content using public APIs.

        Args:
            filename: Name of the data file (e.g., 'models.yaml', 'overrides.yaml')

        Returns:
            File content as string, or None if not available
        """
        if hasattr(self, "_data_manager"):
            return self._data_manager._get_bundled_data_content(filename)
        return None

    def get_raw_model_data(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get raw model data without provider overrides.

        Args:
            model_name: Name of the model to get raw data for

        Returns:
            Raw model data dictionary, or None if not found
        """
        try:
            # Get raw models.yaml content
            raw_paths = self.get_raw_data_paths()
            models_path = raw_paths.get("models")

            from pathlib import Path

            if models_path and Path(models_path).exists():
                # Load from user data file
                with open(models_path, "r") as f:
                    import yaml

                    raw_data = yaml.safe_load(f)
            else:
                # Load from bundled data
                content = self.get_bundled_data_content("models.yaml")
                if content:
                    import yaml

                    raw_data = yaml.safe_load(content)
                else:
                    return None

            # Extract the specific model from raw data
            if isinstance(raw_data, dict) and "models" in raw_data:
                models = typing.cast(Dict[str, Any], raw_data["models"])  # ensure typed
                if model_name in models:
                    base_obj = models[model_name]
                    model_data: Dict[str, Any] = dict(base_obj) if isinstance(base_obj, dict) else {}
                    model_data["name"] = model_name
                    model_data["metadata"] = {"source": "raw", "provider_applied": None}
                    return model_data

            return None

        except Exception:
            return None

    @property
    def models(self) -> Dict[str, ModelCapabilities]:
        """Get a read-only view of registered models."""
        with self._capabilities_lock:
            return dict(self._capabilities)


def get_registry() -> ModelRegistry:
    """Get the model registry singleton instance.

    This is a convenience function for getting the registry instance.

    Returns:
        ModelRegistry: The singleton registry instance
    """
    return ModelRegistry.get_instance()


# Usage note:
# Prefer the thread-safe singleton helper unless you need a standalone instance:
#   from openai_model_registry import get_registry
