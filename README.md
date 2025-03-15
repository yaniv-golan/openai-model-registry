# OpenAI Model Registry

A lightweight Python package for validating OpenAI model parameters and capabilities.

## Features

- Provides a centralized registry of OpenAI model information
- Validates model parameters against model-specific schemas
- Returns model capabilities (context window, max tokens, streaming support)
- Handles model aliases and version detection
- Automatic updates of model registry from official sources
- Works offline with fallback registry data

## Installation

```bash
pip install openai-model-registry
```

## Basic Usage

```python
from openai_model_registry import ModelRegistry

# Get the registry instance
registry = ModelRegistry.get_instance()

# Get model capabilities
capabilities = registry.get_capabilities("gpt-4o")

print(f"Context window: {capabilities.context_window}")
print(f"Max output tokens: {capabilities.max_output_tokens}")
print(f"Supports streaming: {capabilities.supports_streaming}")

# Validate parameters
try:
    capabilities.validate_parameter("temperature", 0.7)  # Valid
    print("Parameter is valid")
    
    capabilities.validate_parameter("temperature", 3.0)  # Invalid
except ValueError as e:
    print(f"Invalid parameter: {e}")

# Check if model supports a feature
if capabilities.supports_structured:
    print("Model supports structured output")
```

## Advanced Usage

See the [examples directory](./examples) for more detailed usage examples.

## Command Line Interface

Update the local registry data:

```bash
openai-model-registry-update
```

## License

MIT License - See [LICENSE](./LICENSE) for details.
