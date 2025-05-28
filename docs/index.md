# OpenAI Model Registry Documentation

Welcome to the documentation for OpenAI Model Registry, a lightweight Python package for validating OpenAI model parameters and capabilities.

## Why Use OpenAI Model Registry?

OpenAI's models have different context-window sizes, parameter ranges, and feature support. If you guess wrong, the API returns an error—often in production.

**OpenAI Model Registry keeps an up-to-date, local catalog of every model's limits and capabilities, letting you validate calls _before_ you send them.**

Typical benefits:

- Catch invalid `temperature`, `top_p`, and `max_tokens` values locally.
- Swap models confidently by comparing context windows and features.
- Work fully offline—perfect for CI or air-gapped environments.

## Overview

OpenAI Model Registry provides a centralized registry of OpenAI model information, validates parameters against model-specific schemas, and retrieves model capabilities. The registry includes comprehensive deprecation tracking, accurate model metadata, and supports multiple schema versions with full backward compatibility.

## Installation

```bash
pip install openai-model-registry
```

## Quick Start

```python
from openai_model_registry import ModelRegistry

# Get the registry instance
registry = ModelRegistry.get_default()

# Get model capabilities
capabilities = registry.get_capabilities("gpt-4o")

print(f"Context window: {capabilities.context_window}")
print(f"Max output tokens: {capabilities.max_output_tokens}")
print(f"Supports streaming: {capabilities.supports_streaming}")
# Expected output: Context window: 128000
#                  Max output tokens: 16384
#                  Supports streaming: True

# Check deprecation status
print(f"Deprecation status: {capabilities.deprecation.status}")
if capabilities.is_deprecated:
    print("⚠️  This model is deprecated")
# Expected output: Deprecation status: active

➡️ **Keeping it fresh:** run `openai-model-registry-update` (CLI) or `registry.refresh_from_remote()` whenever OpenAI ships new models.

## API Reference

Please see the [API Reference](api/index.md) for detailed information about the package's classes and methods.

## User Guide

For more detailed usage instructions, see the [User Guide](user-guide/index.md).

## Contributing

Contributions are welcome! Please see our [Contributing Guide](contributing.md) for more details.
```
