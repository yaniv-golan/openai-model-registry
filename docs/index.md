# OpenAI Model Registry Documentation

Welcome to the documentation for OpenAI Model Registry, a lightweight Python package for validating OpenAI model parameters and capabilities.

## Why Use OpenAI Model Registry?

OpenAI's models have different context-window sizes, parameter ranges, and feature support. If you guess wrong, the API returns an error—often in production.

**OpenAI Model Registry keeps an up-to-date, local catalog of every model's limits and capabilities, letting you validate calls _before_ you send them.**

Typical benefits:

- Catch invalid `temperature`, `top_p`, and `max_tokens` values locally.
- Swap models confidently by comparing context windows and features.
- Work fully offline—perfect for CI or air-gapped environments.
- Automatic updates from GitHub releases keep your data current.

## Overview

OpenAI Model Registry provides a centralized registry of OpenAI model information with automatic updates from GitHub releases. It validates parameters against model-specific schemas, retrieves model capabilities, and includes comprehensive deprecation tracking with accurate model metadata. It offers programmatic access to model-card data (capabilities, parameters, pricing, deprecations) for both OpenAI and Azure providers. Pricing is kept up to date automatically via CI using [ostruct](https://github.com/yaniv-golan/ostruct). The registry uses semantic versioning for schema compatibility and provides robust fallback mechanisms for offline usage.

## Installation

```bash
pip install openai-model-registry
```

## For AI Assistants and LLMs

This project includes an [`llms.txt`](/llms.txt) file following the [llmstxt.org](https://llmstxt.org/) specification. This provides comprehensive, token-efficient documentation designed specifically for AI assistants to understand and help users work with the OpenAI Model Registry programmatically.

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

# Check for data updates
if registry.check_data_updates():
    print("Updates are available!")
    registry.update_data()  # Update to latest model data
```

➡️ **Keeping it fresh:** The registry automatically checks for updates, or you can manually run `registry.update_data()` or the CLI `python -m openai_model_registry.scripts.data_update update`.

## Important Notes

> **🔵 Azure OpenAI Users:** If you're using Azure OpenAI endpoints, please be aware of platform-specific limitations, especially regarding web search capabilities. See our [Azure OpenAI Usage Guide](user-guide/azure-openai.md) for detailed guidance.

## API Reference

Please see the [API Reference](api/index.md) for detailed information about the package's classes and methods.

## User Guide

For more detailed usage instructions, see the [User Guide](user-guide/index.md).

## Contributing

Contributions are welcome! Please see our [Contributing Guide](contributing.md) for more details.
