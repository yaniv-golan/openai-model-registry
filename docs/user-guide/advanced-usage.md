# Advanced Usage

This guide covers advanced features and configuration options for the OpenAI Model Registry.

## Custom Registry Configuration

The registry uses a modern data management system with automatic updates and fallback mechanisms. You can customize this with the `RegistryConfig` class:

```python
from openai_model_registry import ModelRegistry, RegistryConfig

# Create a custom configuration
config = RegistryConfig(
    registry_path="/path/to/custom/registry.yml",  # Optional: custom registry path
    constraints_path="/path/to/custom/constraints.yml",  # Custom constraints path
    auto_update=True,  # Enable automatic updates
    cache_size=200,  # Increase cache size
)

# Initialize registry with the custom configuration
registry = ModelRegistry(config)

# Use the registry
capabilities = registry.get_capabilities("gpt-4o")
# Expected output: Successfully loads capabilities with custom configuration
```

The `RegistryConfig` class supports the following options:

- `registry_path`: Custom path to the registry YAML file (if None, DataManager handles loading)
- `constraints_path`: Custom path to the constraints YAML file
- `auto_update`: Whether to automatically update the registry
- `cache_size`: Size of the model capabilities cache

## Data Management System

The registry uses a modern DataManager that provides:

- **Automatic Updates**: Fetches latest model data from GitHub releases
- **Version Tracking**: Maintains version information and update history
- **Fallback Mechanisms**: Environment variable → User directory → Bundled data
- **Data Validation**: Comprehensive validation for downloaded data

### Environment Variables

Control data management behavior with these environment variables:

```bash
# Disable automatic data updates (useful for CI/tests)
export OMR_DISABLE_DATA_UPDATES=1

# Pin to a specific data version
export OMR_DATA_VERSION_PIN=v1.2.3

# Use custom data directory
export OMR_DATA_DIR=/path/to/custom/data

# Override registry path (for testing)
export OMR_MODEL_REGISTRY_PATH=/path/to/test/models.yaml
```

### Data Update API

The registry provides methods for managing data updates:

```python
from openai_model_registry import ModelRegistry

registry = ModelRegistry.get_default()

# Check if updates are available
if registry.check_data_updates():
    print("Updates are available!")

    # Update the data
    if registry.update_data():
        print("Data updated successfully")
    else:
        print("Update failed")

# Force update regardless of current version
registry.update_data(force=True)

# Get current data version
version = registry.get_data_version()
print(f"Current version: {version}")

# Get detailed data information
info = registry.get_data_info()
print(f"Data directory: {info['data_directory']}")
print(f"Updates enabled: {info['updates_enabled']}")
```

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

## Accessing the Singleton

Use `get_default()` to access the singleton instance.

```python
registry = ModelRegistry.get_default()
```

## Registry Updates

The registry supports both automatic and manual updates through the DataManager system:

```python
from openai_model_registry import ModelRegistry
from openai_model_registry.registry import RefreshStatus

# Get registry instance
registry = ModelRegistry.get_default()

# Check for updates using DataManager
if registry.check_data_updates():
    print("DataManager updates are available")

    # Update using DataManager
    if registry.update_data():
        print("Registry updated successfully via DataManager")
    else:
        print("DataManager update failed")

# Legacy update method (also available)
check_result = registry.check_for_updates()
if check_result.status == RefreshStatus.UPDATE_AVAILABLE:
    print(f"Legacy update available: {check_result.message}")

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

## Programmatic updates (recommended pattern)

For the minimal snippet, see Getting Started → Keeping Data Up-to-Date. Below is the same pattern using the typed enum and intended for adaptation in advanced scenarios (scheduling, retries/backoff, metrics):

```python
from openai_model_registry import ModelRegistry
from openai_model_registry.registry import RefreshStatus

registry = ModelRegistry.get_default()

try:
    result = registry.check_for_updates()
    if result.status is RefreshStatus.UPDATE_AVAILABLE:
        # Apply the update (writes to user data dir or OMR_DATA_DIR)
        registry.update_data()
except Exception:
    # Never crash the application due to update issues
    pass
```

Notes:

- The library automatically honors `OMR_DISABLE_DATA_UPDATES` and `OMR_DATA_VERSION_PIN`.
- No network calls occur during normal loads; network is used only on explicit update checks/applies.
- `OMR_MODEL_REGISTRY_PATH` is a read‑only override and is never modified by updates.

For advanced patterns (scheduling, retries/backoff, version pinning strategies, multi‑registry setups), adapt the above to your app’s lifecycle (e.g., run on startup or on a cron/scheduler, add retry/backoff, emit metrics/logs on update checks).

## Data Loading Priority

The registry loads data with the following priority:

1. **Environment Variable**: `OMR_MODEL_REGISTRY_PATH` (if set and file exists)
1. **User Data Directory**: `~/Library/Application Support/openai-model-registry/models.yaml` (macOS)
1. **Bundled Data**: Included with the package as fallback

This ensures reliable operation even without network access while allowing customization for testing and development.

## Schema Versioning

The registry uses semantic versioning for schema compatibility:

```python
# The registry automatically detects and validates schema versions
# Current supported range: 1.x (>=1.0.0, <2.0.0)
# Schema version is read from the 'version' field in data files

registry = ModelRegistry.get_default()

# Works with any compatible schema version
capabilities = registry.get_capabilities("gpt-4o")

# All models include comprehensive metadata
print(f"Status: {capabilities.deprecation.status}")
print(f"Context window: {capabilities.context_window:,}")
print(f"Supports vision: {capabilities.supports_vision}")
# Expected output: Status: active
```

### Schema Version Detection

The registry uses proper semantic versioning:

- **Version field**: Schema version is read from the `version` field in configuration files
- **Compatibility checking**: Uses semver ranges (e.g., ">=1.0.0,\<2.0.0" for 1.x support)
- **Validation**: Ensures data structure matches the declared schema version
- **Error handling**: Clear error messages for unsupported or invalid versions

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

The package provides command-line interfaces for managing registry data:

### Data Management CLI (Legacy Script)

```bash
# Check current data status
python -m openai_model_registry.scripts.data_update check

# Update data files
python -m openai_model_registry.scripts.data_update update

# Force update to latest version
python -m openai_model_registry.scripts.data_update update --force

# Show data configuration
python -m openai_model_registry.scripts.data_update info

# Clean local data files
python -m openai_model_registry.scripts.data_update clean
```

### Legacy Registry Update CLI (Legacy Script)

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
    print(f"Parameter: {param_ref.ref}")
    if param_ref.max_value is not None:
        print(f"  Max value: {param_ref.max_value}")
    if param_ref.min_value is not None:
        print(f"  Min value: {param_ref.min_value}")
```

## Error Handling

The registry provides comprehensive error handling for various scenarios:

```python
from openai_model_registry import ModelRegistry
from openai_model_registry.errors import (
    ModelNotSupportedError,
    ParameterValidationError,
    ConfigurationError,
)

registry = ModelRegistry.get_default()

try:
    capabilities = registry.get_capabilities("non-existent-model")
except ModelNotSupportedError as e:
    print(f"Model not supported: {e}")

try:
    capabilities = registry.get_capabilities("gpt-4o")
    capabilities.validate_parameter("temperature", 5.0)  # Invalid value
except ParameterValidationError as e:
    print(f"Parameter validation failed: {e}")

try:
    # This might fail if data files are corrupted
    registry._load_capabilities()
except ConfigurationError as e:
    print(f"Configuration error: {e}")
```

### Error Hierarchy

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
```

The registry itself uses LRU caching for capabilities, so repeated calls to `get_capabilities()` for the same model are automatically optimized.

## Data files and provider overrides

The registry composes its effective dataset from two YAML files in `data/`:

- `models.yaml`: Canonical base dataset for all models (capabilities, parameters,
  pricing, deprecation, billing).
- `overrides.yaml`: Provider-specific diffs applied on top of `models.yaml`.

### Provider selection

- Default provider: `openai`.
- Override via environment `OMR_PROVIDER` or CLI flag `--provider <openai|azure>`.

### Structure of overrides.yaml

```yaml
overrides:
  azure:
    models:
      gpt-4o:
        pricing:
          input_cost_per_unit: 5.0
          output_cost_per_unit: 20.0
        parameters:
          max_tokens:
            max: 12000
        capabilities:
          tools:
            - file_search
```

- Top-level key is `overrides`.
- Under each provider (e.g., `azure`), a `models` map contains partial model
  entries. Only the fields you want to change need to be present.
- Unknown models under a provider are ignored; the base dataset remains intact.

### Merge semantics

When building the effective dataset, the registry loads `models.yaml` and then
applies provider overrides. Merge behavior mirrors the implementation in
`ModelRegistry._apply_overrides()` and `_merge_model_override()`:

- pricing (dict): merged with base pricing via shallow update
- capabilities (dict): merged with base capabilities via shallow update
- parameters (dict): merged with base parameters via shallow update
- other top-level fields: replaced entirely

Notes:

- Shallow updates mean nested dictionaries are updated key-by-key, but lists are
  replaced as whole values. This keeps overrides concise and predictable.
- If no overrides exist for the selected provider, the base `models.yaml` data is
  used as-is.

### Inspecting raw vs effective data

Use the CLI to compare the on-disk raw files with the provider-merged effective
dataset:

```bash
# Dump effective (merged) dataset
omr data dump --effective --format json | jq '.'

# Dump raw base dataset (no provider merge)
omr data dump --raw --format yaml

# Per-model views
omr models get gpt-4o                # effective (default)
omr models get gpt-4o --raw --format yaml
```

### Where updates are written

Data updates write `models.yaml` and `overrides.yaml` to the user data directory
by default (or `OMR_DATA_DIR` if set). The `OMR_MODEL_REGISTRY_PATH` override is
read-only and is never modified by updates.
