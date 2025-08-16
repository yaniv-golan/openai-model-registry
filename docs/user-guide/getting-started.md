# Getting Started

This guide will help you install the OpenAI Model Registry and start using its features.

## Installation

### Core Library
Install the OpenAI Model Registry package using pip:

```bash
pip install openai-model-registry
```

### With CLI Tools
If you want to use the `omr` command-line interface, install with the CLI extra:

```bash
pip install openai-model-registry[cli]
```

> **💡 Which installation should I choose?**
> - **Core only**: Perfect for programmatic use in applications, scripts, or libraries
> - **With CLI**: Adds command-line tools for interactive exploration and debugging

## Basic Usage

Here's a simple example to get started:

```python
from openai_model_registry import ModelRegistry

# Get the registry instance (singleton)
registry = ModelRegistry.get_default()

# Get capabilities for a specific model
capabilities = registry.get_capabilities("gpt-4o")

# Access model information
print(f"Context window: {capabilities.context_window}")
print(f"Max output tokens: {capabilities.max_output_tokens}")
print(f"Supports streaming: {capabilities.supports_streaming}")
print(f"Supports structured output: {capabilities.supports_structured}")
```

## Model Validation

You can validate parameters against a model's constraints:

```python
try:
    # Valid parameter
    capabilities.validate_parameter("temperature", 0.7)
    print("Temperature 0.7 is valid")

    # Invalid parameter
    capabilities.validate_parameter("temperature", 3.0)
    print("This won't be reached")
except Exception as e:
    print(f"Invalid parameter: {e}")
```

## Keeping Data Up-to-Date

You can check and apply data updates programmatically or via the CLI.

Programmatically:

```python
from openai_model_registry import ModelRegistry
from openai_model_registry.registry import RefreshStatus

registry = ModelRegistry.get_default()

result = registry.check_for_updates()
if result.status is RefreshStatus.UPDATE_AVAILABLE:
    registry.update_data()
```

Via CLI:

```bash
# Check for updates (exit code 10 if update is available)
omr --format json update check

# Apply updates
omr update apply
```

The library honors `OMR_DISABLE_DATA_UPDATES` and `OMR_DATA_VERSION_PIN`. Updates write to the user data directory (or `OMR_DATA_DIR`), never to `OMR_MODEL_REGISTRY_PATH`.

## Next Steps

Now that you have the basics, explore the following topics:

- [Model Capabilities](model-capabilities.md) - Learn about model capabilities and how to use them
- [Parameter Validation](parameter-validation.md) - Deep dive into parameter validation
- [Advanced Usage](advanced-usage.md) - Explore advanced features like custom configurations and registry updates
