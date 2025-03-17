# OpenAI Model Registry

[![PyPI version](https://img.shields.io/pypi/v/openai-model-registry.svg)](https://pypi.org/project/openai-model-registry/)
[![Python Versions](https://img.shields.io/pypi/pyversions/openai-model-registry.svg)](https://pypi.org/project/openai-model-registry/)
[![CI Status](https://github.com/yaniv-golan/openai-model-registry/workflows/Python%20CI/badge.svg)](https://github.com/yaniv-golan/openai-model-registry/actions)
[![codecov](https://codecov.io/gh/yaniv-golan/openai-model-registry/branch/main/graph/badge.svg)](https://codecov.io/gh/yaniv-golan/openai-model-registry)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python package that provides information about OpenAI models and validates parameters before API calls.

📚 **[View the Documentation](https://yaniv-golan.github.io/openai-model-registry/)**

## What This Package Does

- Helps you avoid invalid API calls by validating parameters ahead of time
- Provides accurate information about model capabilities (context windows, token limits)
- Handles model aliases and different model versions
- Works offline with locally stored model information
- Keeps model information up-to-date with optional updates

## Installation

```bash
pip install openai-model-registry
```

## Simple Example

```python
from openai_model_registry import ModelRegistry

# Get information about a model
registry = ModelRegistry.get_instance()
model = registry.get_capabilities("gpt-4o")

# Access model limits
print(f"Context window: {model.context_window} tokens")
print(f"Max output: {model.max_output_tokens} tokens")

# Check if parameter values are valid
model.validate_parameter("temperature", 0.7)  # Valid - no error
try:
    model.validate_parameter("temperature", 3.0)  # Invalid - raises ValueError
except ValueError as e:
    print(f"Error: {e}")

# Check model features
if model.supports_structured:
    print("This model supports Structured Output")
```

## Practical Use Cases

### Validating Parameters Before API Calls

```python
def call_openai(model, messages, **params):
    # Validate parameters before making API call
    capabilities = registry.get_capabilities(model)
    for param_name, value in params.items():
        capabilities.validate_parameter(param_name, value)

    # Now make the API call
    return client.chat.completions.create(model=model, messages=messages, **params)
```

### Managing Token Limits

```python
def prepare_prompt(model_name, prompt, max_output=None):
    capabilities = registry.get_capabilities(model_name)

    # Use model's max output if not specified
    max_output = max_output or capabilities.max_output_tokens

    # Calculate available tokens for input
    available_tokens = capabilities.context_window - max_output

    # Ensure prompt fits within available tokens
    return truncate_prompt(prompt, available_tokens)
```

## Key Features

- **Model Information**: Get context window size, token limits, and supported features
- **Parameter Validation**: Check if parameter values are valid for specific models
- **Version Support**: Works with date-based models (e.g., "o3-mini-2025-01-31")
- **Offline Usage**: Functions without internet using local registry data
- **Updates**: Optional updates to keep model information current

## Command Line Usage

Update your local registry data:

```bash
openai-model-registry-update
```

## Configuration

The registry uses local files for model information:

```
# Default locations (XDG Base Directory spec)
Linux: ~/.config/openai-model-registry/
macOS: ~/Library/Application Support/openai-model-registry/
Windows: %LOCALAPPDATA%\openai-model-registry\
```

You can specify custom locations:

```python
import os

# Use custom registry files
os.environ["MODEL_REGISTRY_PATH"] = "/path/to/custom/models.yml"
os.environ["PARAMETER_CONSTRAINTS_PATH"] = "/path/to/custom/parameter_constraints.yml"

# Then initialize registry
from openai_model_registry import ModelRegistry
registry = ModelRegistry.get_instance()
```

## Documentation

For more details, see:

- [Getting Started Guide](https://yaniv-golan.github.io/openai-model-registry/user-guide/getting-started/)
- [API Reference](https://yaniv-golan.github.io/openai-model-registry/api/)
- [Examples](./examples/)

## Development

```bash
# Install dependencies (requires Poetry)
poetry install

# Run tests
poetry run pytest

# Run linting
poetry run pre-commit run --all-files
```

## License

MIT License - See [LICENSE](./LICENSE) for details.
