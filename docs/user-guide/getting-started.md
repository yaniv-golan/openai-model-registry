# Getting Started

This guide will help you install the OpenAI Model Registry and start using its features.

## Installation

Install the OpenAI Model Registry package using pip:

```bash
pip install openai-model-registry
```

## Basic Usage

Here's a simple example to get started:

```python
from openai_model_registry import ModelRegistry

# Get the registry instance (singleton)
registry = ModelRegistry.get_instance()

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

## Next Steps

Now that you have the basics, explore the following topics:

- [Model Capabilities](model-capabilities.md) - Learn about model capabilities and how to use them
- [Parameter Validation](parameter-validation.md) - Deep dive into parameter validation
- [Advanced Usage](advanced-usage.md) - Explore advanced features like custom configurations and registry updates
