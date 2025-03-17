# ModelRegistry

The `ModelRegistry` class is the primary entry point for accessing model capabilities and validating parameters.

## Class Reference

::: openai_model_registry.registry.ModelRegistry
    options:
      show_root_heading: false
      show_source: true

::: openai_model_registry.registry.RegistryConfig
    options:
      show_root_heading: true
      show_source: true

## Usage Examples

### Initializing the Registry

```python
from openai_model_registry import ModelRegistry
from openai_model_registry.registry import RegistryConfig

# Get the default singleton instance
registry = ModelRegistry.get_instance()

# Or create a custom instance with specific configuration
config = RegistryConfig(
    registry_path="/custom/path/registry.yml",
    constraints_path="/custom/path/constraints.yml",
    auto_update=False,
    cache_size=200
)
custom_registry = ModelRegistry(config)
```

### Getting Model Capabilities

```python
from openai_model_registry import ModelRegistry

# Use the default registry
registry = ModelRegistry.get_instance()

# Get capabilities for a specific model
capabilities = registry.get_capabilities("gpt-4o")

# Get capabilities for a dated version
dated_capabilities = registry.get_capabilities("gpt-4o-2024-05-13")
```

### Listing Available Models

```python
from openai_model_registry import ModelRegistry

registry = ModelRegistry.get_instance()

# Get all models as a dictionary
all_models = registry.models

# Print all available models
for model_name in sorted(all_models.keys()):
    print(model_name)
```

### Updating the Registry

```python
from openai_model_registry import ModelRegistry
from openai_model_registry.registry import RefreshStatus

registry = ModelRegistry.get_instance()

# Check for updates
refresh_result = registry.check_for_updates()
if refresh_result.status == RefreshStatus.UPDATE_AVAILABLE:
    print("Update is available")

# Update the registry from the default source
update_result = registry.refresh_from_remote()

# Check the result
if update_result.success:
    print("Registry updated successfully")
else:
    print(f"Update failed: {update_result.message}")
```

### Working with Model Versions

```python
from openai_model_registry import ModelRegistry, ModelVersion

registry = ModelRegistry.get_instance()

# Parse a version from a model string
model = "gpt-4o-2024-05-13"
version = ModelVersion.from_string("2024-05-13")

print(f"Year: {version.year}")
print(f"Month: {version.month}")
print(f"Day: {version.day}")

# Check if a version is newer than another
newer_version = ModelVersion.from_string("2024-06-01")
if newer_version > version:
    print(f"{newer_version} is newer than {version}")

# Check if a model name follows the dated format pattern
if hasattr(ModelVersion, "is_dated_model"):
    is_dated = ModelVersion.is_dated_model("gpt-4o-2024-05-13")
    print(f"Is a dated model: {is_dated}")  # True

    is_dated = ModelVersion.is_dated_model("gpt-4o")
    print(f"Is a dated model: {is_dated}")  # False
```
