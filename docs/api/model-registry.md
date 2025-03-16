# ModelRegistry

The `ModelRegistry` class is the primary entry point for accessing model capabilities and validating parameters.

## Class Reference

::: openai_model_registry.registry.ModelRegistry
    options:
      show_root_heading: false
      show_source: true

## Usage Examples

### Initializing the Registry

```python
from openai_model_registry import ModelRegistry

# Get the default singleton instance
registry = ModelRegistry.get_instance()

# Or create a custom instance with a specific path
custom_registry = ModelRegistry(registry_path="/path/to/registry")
```

### Getting Model Capabilities

```python
from openai_model_registry import ModelRegistry

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
from openai_model_registry.registry import RegistryUpdateStatus

registry = ModelRegistry.get_instance()

# Update the registry from the default source
update_result = registry.update_registry()

# Check the result
if update_result.status == RegistryUpdateStatus.SUCCESS:
    print("Registry updated successfully")
    if update_result.added_models:
        print(f"New models: {', '.join(update_result.added_models)}")
    if update_result.updated_models:
        print(f"Updated models: {', '.join(update_result.updated_models)}")
elif update_result.status == RegistryUpdateStatus.NO_CHANGE:
    print("Registry is already up to date")
else:
    print(f"Update failed: {update_result.error}")
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
```
