# Advanced Usage

This guide covers advanced features and configuration options for the OpenAI Model Registry.

## Custom Registry Location

By default, the registry loads its data from a predefined location. You can customize this location:

```python
from openai_model_registry import ModelRegistry

# Initialize registry with a custom path
registry = ModelRegistry(registry_path="/path/to/custom/registry")

# Use the registry
capabilities = registry.get_capabilities("gpt-4o")
```

## Registry Updates

The registry data can be updated from an upstream source. This is useful for keeping the registry in sync with the latest model capabilities:

```python
from openai_model_registry import ModelRegistry
from openai_model_registry.registry import RegistryUpdateStatus

# Get registry instance
registry = ModelRegistry.get_instance()

# Update the registry
update_result = registry.update_registry()

# Check update status
if update_result.status == RegistryUpdateStatus.SUCCESS:
    print("Registry updated successfully")
    print(f"Added models: {update_result.added_models}")
    print(f"Updated models: {update_result.updated_models}")
elif update_result.status == RegistryUpdateStatus.NO_CHANGE:
    print("Registry is already up to date")
else:
    print(f"Update failed: {update_result.error}")
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

registry = ModelRegistry.get_instance()
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

registry = ModelRegistry.get_instance()
capabilities = registry.get_capabilities("gpt-4o")

# Create a set to track used parameters
used_params = set()

# Validate temperature
capabilities.validate_parameter("temperature", 0.7, used_params)

# Validate top_p (these params might be mutually exclusive or have interdependencies)
capabilities.validate_parameter("top_p", 0.9, used_params)

# used_params now contains ["temperature", "top_p"]
print(f"Used parameters: {used_params}")
```

## Error Handling Strategies

For robust applications, you might want to implement error handling strategies:

```python
from openai_model_registry import ModelRegistry, ModelRegistryError, ModelNotSupportedError

try:
    registry = ModelRegistry.get_instance()
    
    # Try to get capabilities for a model
    try:
        capabilities = registry.get_capabilities("nonexistent-model")
    except ModelNotSupportedError as e:
        print(f"Model not found: {e}")
        # Fallback to a default model
        capabilities = registry.get_capabilities("gpt-4o")
        
    # Validate parameters with error handling
    try:
        capabilities.validate_parameter("temperature", 3.0)
    except ModelRegistryError as e:
        print(f"Parameter validation failed: {e}")
        # Use a default valid value
        print("Using default temperature of 0.7")
        temperature = 0.7
        
except Exception as e:
    print(f"Unexpected error: {e}")
    # Implement fallback mechanism
```

## Performance Optimization

For applications that make frequent validation calls, consider caching capabilities:

```python
from openai_model_registry import ModelRegistry
import functools

# Create a cache of model capabilities
@functools.lru_cache(maxsize=16)
def get_cached_capabilities(model_name):
    registry = ModelRegistry.get_instance()
    return registry.get_capabilities(model_name)

# Use cached capabilities
capabilities = get_cached_capabilities("gpt-4o")
capabilities.validate_parameter("temperature", 0.7)
```
