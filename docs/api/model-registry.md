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
registry = ModelRegistry.get_default()

# Or create a custom instance with specific configuration
config = RegistryConfig(
    registry_path="/custom/path/registry.yml",
    constraints_path="/custom/path/constraints.yml",
    auto_update=False,
    cache_size=200,
)
custom_registry = ModelRegistry(config)
```

### Getting Model Capabilities

```python
from openai_model_registry import ModelRegistry

# Get the default registry instance
registry = ModelRegistry.get_default()

# Get capabilities for a specific model
capabilities = registry.get_capabilities("gpt-4o")
print(f"Context window: {capabilities.context_window}")
```

### Listing Available Models

```python
from openai_model_registry import ModelRegistry

registry = ModelRegistry.get_default()

# List all available models
models = registry.list_models()
for model in models:
    print(f"Model: {model}")
```

### Updating the Registry

```python
from openai_model_registry import ModelRegistry

registry = ModelRegistry.get_default()

# Check if a model exists
if registry.has_model("gpt-4o"):
    print("Model exists in registry")
else:
    print("Model not found")
```

### Working with Model Versions

```python
from openai_model_registry import ModelRegistry, ModelVersion

registry = ModelRegistry.get_default()

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

```python
from openai_model_registry import ModelRegistry

registry = ModelRegistry.get_default()

# Update registry from remote source
try:
    result = registry.refresh_from_remote()
    print(f"Update result: {result}")
except Exception as e:
    print(f"Update failed: {e}")
```

```python
from openai_model_registry import ModelRegistry

registry = ModelRegistry.get_default()

# Check for updates without applying them
try:
    result = registry.check_for_updates()
    if result.needs_update:
        print("Updates available!")
        print(f"Current version: {result.current_version}")
        print(f"Latest version: {result.latest_version}")
except Exception as e:
    print(f"Update check failed: {e}")
```
