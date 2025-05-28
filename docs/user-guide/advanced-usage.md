# Advanced Usage

This guide covers advanced features and configuration options for the OpenAI Model Registry.

## Custom Registry Configuration

By default, the registry loads its data from predefined locations. You can customize this with the `RegistryConfig` class:

```python
from openai_model_registry import ModelRegistry, RegistryConfig

# Create a custom configuration
config = RegistryConfig(
    registry_path="/path/to/custom/registry.yml",
    constraints_path="/path/to/custom/constraints.yml",
    auto_update=True,
    cache_size=200,
)

# Initialize registry with the custom configuration
registry = ModelRegistry(config)

# Use the registry
capabilities = registry.get_capabilities("gpt-4o")
# Expected output: Successfully loads capabilities with custom configuration
```

The `RegistryConfig` class supports the following options:

- `registry_path`: Custom path to the registry YAML file
- `constraints_path`: Custom path to the constraints YAML file
- `auto_update`: Whether to automatically update the registry
- `cache_size`: Size of the model capabilities cache

## Multiple Registry Instances

With the new API, you can create multiple registry instances with different configurations:

```python
from openai_model_registry import ModelRegistry, RegistryConfig

# Create registries for different environments
prod_config = RegistryConfig(registry_path="/path/to/prod/registry.yml")
staging_config = RegistryConfig(registry_path="/path/to/staging/registry.yml")

prod_registry = ModelRegistry(prod_config)
staging_registry = ModelRegistry(staging_config)

# Use different registries as needed
prod_capabilities = prod_registry.get_capabilities("gpt-4o")
staging_capabilities = staging_registry.get_capabilities("gpt-4o")
# Expected output: Successfully loads capabilities from different registry instances
```

This is particularly useful for testing or when you need to support different configurations in the same application.

## API Deprecation Notice

**Note:** `get_instance()` is deprecated; use `get_default()`.

The `get_instance()` method has been deprecated in favor of `get_default()` for better clarity and consistency. While `get_instance()` still works for backward compatibility, new code should use `get_default()`.

```python
# ❌ Deprecated (but still works)
registry = ModelRegistry.get_instance()

# ✅ Recommended
registry = ModelRegistry.get_default()
```

## Registry Updates

The registry data can be updated from an upstream source. This is useful for keeping the registry in sync with the latest model capabilities:

```python
from openai_model_registry import ModelRegistry
from openai_model_registry.registry import RefreshStatus

# Get registry instance
registry = ModelRegistry.get_default()

# Check for updates first
check_result = registry.check_for_updates()
if check_result.status == RefreshStatus.UPDATE_AVAILABLE:
    print(f"Update available: {check_result.message}")

    # Refresh from remote source
    refresh_result = registry.refresh_from_remote()

    if refresh_result.success:
        print("Registry updated successfully")
    else:
        print(f"Update failed: {refresh_result.message}")
elif check_result.status == RefreshStatus.ALREADY_CURRENT:
    print("Registry is already up to date")
else:
    print(f"Update check failed: {check_result.message}")
```

## Schema Versioning and Backward Compatibility

The registry supports multiple schema versions with full backward compatibility:

```python
# The registry automatically handles different schema versions
# v1.0.0: Original format with basic model definitions
# v1.1.0+: Enhanced format with deprecation metadata and improved structure

# Both formats are supported seamlessly
registry = ModelRegistry.get_default()

# Works with any schema version
capabilities = registry.get_capabilities("gpt-4o")

# Deprecation information is available for all models
# (defaults to "active" status for models without explicit deprecation data)
print(f"Status: {capabilities.deprecation.status}")
# Expected output: Status: active
```

## Model Data Accuracy

The registry maintains accurate model information based on official OpenAI documentation:

```python
# Model release dates are accurate to OpenAI's official announcements
capabilities = registry.get_capabilities("gpt-4o-2024-05-13")  # Correct release date
print(f"Model: {capabilities.model_name}")

# Streaming capabilities reflect current API support
o1_mini = registry.get_capabilities("o1-mini")
print(f"O1-mini supports streaming: {o1_mini.supports_streaming}")  # True

o1_latest = registry.get_capabilities("o1-2024-12-17")
print(
    f"O1-2024-12-17 supports streaming: {o1_latest.supports_streaming}"
)  # False (not yet in public API)

# Deprecation dates use null values for unknown timelines instead of placeholder dates
print(
    f"Deprecates on: {capabilities.deprecation.deprecates_on}"
)  # None for active models
```

## Command Line Interface

The package provides a command-line interface for updating the registry:

```bash
# Update the registry from the default source
openai-model-registry-update

# Update with verbose output
openai-model-registry-update --verbose

# Use a custom source URL
openai-model-registry-update --source https://custom-source.example/registry.json
```

## Working with Parameter References

The registry uses parameter references to define relationships between parameters:

```python
from openai_model_registry import ModelRegistry

registry = ModelRegistry.get_default()
capabilities = registry.get_capabilities("gpt-4o")

# Get all parameter references
for param_ref in capabilities.supported_parameters:
    print(f"Parameter reference: {param_ref.ref}")
    print(f"  Description: {param_ref.description}")

    # Access the constraint directly
    constraint = capabilities.get_constraint(param_ref.ref)
    if hasattr(constraint, "min_value"):
        print(f"  Min value: {constraint.min_value}")
        print(f"  Max value: {constraint.max_value}")
```

## Validation with Context

Some parameters have interdependencies or contextual validation requirements. You can track which parameters have been used:

```python
from openai_model_registry import ModelRegistry

registry = ModelRegistry.get_default()
capabilities = registry.get_capabilities("gpt-4o")

# Create a set to track used parameters
used_params = set()

# Validate temperature
capabilities.validate_parameter("temperature", 0.7, used_params)

# Validate top_p (these params might be mutually exclusive or have interdependencies)
capabilities.validate_parameter("top_p", 0.9, used_params)

# used_params now contains ["temperature", "top_p"]
print(f"Used parameters: {used_params}")
# Expected output: Used parameters: {'temperature', 'top_p'}
```

## Error Handling

The library uses a consistent exception-based approach for error handling. Each error type provides detailed context to help diagnose and handle specific error conditions:

```python
from openai_model_registry import (
    ModelRegistry,
    ModelRegistryError,
    ModelNotSupportedError,
    ParameterNotSupportedError,
    ConstraintNotFoundError,
)

try:
    registry = ModelRegistry.get_default()

    # Try to get capabilities for a model
    try:
        capabilities = registry.get_capabilities("nonexistent-model")
    except ModelNotSupportedError as e:
        print(f"Model not found: {e.model}")
        print(f"Available models: {e.available_models}")
        # Fallback to a default model
        capabilities = registry.get_capabilities("gpt-4o")

    # Validate parameters with specific error handling
    try:
        capabilities.validate_parameter("temperature", 3.0)
    except ParameterNotSupportedError as e:
        print(f"Parameter '{e.param_name}' is not supported for model '{e.model}'")
        # Skip this parameter
    except ModelRegistryError as e:
        print(f"Parameter validation failed: {e}")
        # Use a default valid value
        print("Using default temperature of 0.7")
        temperature = 0.7

    # Get constraint information
    try:
        constraint = registry.get_parameter_constraint(
            "numeric_constraints.temperature"
        )
        print(f"Min value: {constraint.min_value}, Max value: {constraint.max_value}")
    except ConstraintNotFoundError as e:
        print(f"Constraint reference '{e.ref}' not found")

except Exception as e:
    print(f"Unexpected error: {e}")
    # Implement fallback mechanism
```

### Exception Hierarchy

The library provides a hierarchical set of exceptions:

- `ModelRegistryError`: Base class for all registry errors
  - `ConfigurationError`: Base class for configuration-related errors
    - `ConfigFileNotFoundError`: Configuration file not found
    - `InvalidConfigFormatError`: Invalid configuration format
  - `ModelVersionError`: Base class for version-related errors
    - `InvalidDateError`: Invalid date format in a model version
    - `ModelFormatError`: Invalid model name format
    - `VersionTooOldError`: Model version is too old
  - `ParameterValidationError`: Base class for parameter validation errors
    - `ParameterNotSupportedError`: Parameter not supported for model
    - `TokenParameterError`: Token-related parameter error
  - `ConstraintNotFoundError`: Constraint reference not found
  - `NetworkError`: Error during network operations
  - `ModelNotSupportedError`: Model not supported by registry

## Logging Configuration

The library uses standard Python logging. You can configure it like any other Python logger:

```python
import logging
from openai_model_registry import get_logger

# Configure the root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Get the library logger
logger = get_logger()

# Add custom handlers if needed
file_handler = logging.FileHandler("registry.log")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(file_handler)
```

The package logger name is "openai_model_registry".

## Performance Optimization

For applications that make frequent validation calls, consider caching capabilities:

```python
from openai_model_registry import ModelRegistry
import functools


# Create a cache of model capabilities
@functools.lru_cache(maxsize=16)
def get_cached_capabilities(model_name):
    registry = ModelRegistry.get_default()
    return registry.get_capabilities(model_name)


# Use cached capabilities
capabilities = get_cached_capabilities("gpt-4o")
capabilities.validate_parameter("temperature", 0.7)
```
