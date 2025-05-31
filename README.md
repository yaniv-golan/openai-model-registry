# OpenAI Model Registry

[![PyPI version](https://img.shields.io/pypi/v/openai-model-registry.svg)](https://pypi.org/project/openai-model-registry/)
[![Python Versions](https://img.shields.io/pypi/pyversions/openai-model-registry.svg)](https://pypi.org/project/openai-model-registry/)
[![CI Status](https://github.com/yaniv-golan/openai-model-registry/workflows/Python%20CI/badge.svg)](https://github.com/yaniv-golan/openai-model-registry/actions)
[![codecov](https://codecov.io/gh/yaniv-golan/openai-model-registry/branch/main/graph/badge.svg)](https://codecov.io/gh/yaniv-golan/openai-model-registry)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python package that provides information about OpenAI models and validates parameters before API calls.

📚 **[View the Documentation](https://yaniv-golan.github.io/openai-model-registry/)**

## Why Use OpenAI Model Registry?

OpenAI's models have different context-window sizes, parameter ranges, and feature support. If you guess wrong, the API returns an error—often in production.

**OpenAI Model Registry keeps an up-to-date, local catalog of every model's limits and capabilities, letting you validate calls _before_ you send them.**

Typical benefits:

- Catch invalid `temperature`, `top_p`, and `max_tokens` values locally.
- Swap models confidently by comparing context windows and features.
- Work fully offline—perfect for CI or air-gapped environments.

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

````python
from openai_model_registry import ModelRegistry

# Get information about a model
registry = ModelRegistry.get_default()
model = registry.get_capabilities("gpt-4o")

# Access model limits
print(f"Context window: {model.context_window} tokens")
print(f"Max output: {model.max_output_tokens} tokens")
# Expected output: Context window: 128000 tokens
#                  Max output: 16384 tokens

# Check if parameter values are valid
model.validate_parameter("temperature", 0.7)  # Valid - no error
try:
    model.validate_parameter("temperature", 3.0)  # Invalid - raises ValueError
except ValueError as e:
    print(f"Error: {e}")
# Expected output: Error: Parameter 'temperature' must be between 0 and 2...

# Check model features
if model.supports_structured:
    print("This model supports Structured Output")
# Expected output: This model supports Structured Output

➡️ **Keeping it fresh:** run `openai-model-registry-update` (CLI) or `registry.refresh_from_remote()` whenever OpenAI ships new models.

> **🔵 Azure OpenAI Users:** If you're using Azure OpenAI endpoints, be aware of platform-specific limitations, especially for web search capabilities. See our [Azure OpenAI documentation](docs/user-guide/azure-openai.md) for guidance.

## Practical Use Cases

### Validating Parameters Before API Calls

```python
import openai
from openai_model_registry import ModelRegistry

# Initialize registry and client
registry = ModelRegistry.get_default()
client = openai.OpenAI()  # Requires OPENAI_API_KEY environment variable

def call_openai(model, messages, **params):
    # Validate parameters before making API call
    capabilities = registry.get_capabilities(model)
    for param_name, value in params.items():
        capabilities.validate_parameter(param_name, value)

    # Now make the API call
    return client.chat.completions.create(model=model, messages=messages, **params)

# Example usage
messages = [{"role": "user", "content": "Hello!"}]
response = call_openai("gpt-4o", messages, temperature=0.7, max_tokens=100)
# Expected output: Successful API call with validated parameters
````

### Managing Token Limits

```python
from openai_model_registry import ModelRegistry

# Initialize registry
registry = ModelRegistry.get_default()


def truncate_prompt(prompt, max_tokens):
    """Simple truncation function (you'd implement proper tokenization)"""
    # This is a simplified example - use tiktoken for real tokenization
    words = prompt.split()
    if len(words) <= max_tokens:
        return prompt
    return " ".join(words[:max_tokens])


def prepare_prompt(model_name, prompt, max_output=None):
    capabilities = registry.get_capabilities(model_name)

    # Use model's max output if not specified
    max_output = max_output or capabilities.max_output_tokens

    # Calculate available tokens for input
    available_tokens = capabilities.context_window - max_output

    # Ensure prompt fits within available tokens
    return truncate_prompt(prompt, available_tokens)


# Example usage
long_prompt = "This is a very long prompt that might exceed token limits..."
safe_prompt = prepare_prompt("gpt-4o", long_prompt, max_output=1000)
# Expected output: Truncated prompt that fits within token limits
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

```text
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

registry = ModelRegistry.get_default()
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

## Next Steps

- 📚 **Examples** – real-world scripts in [`examples/`](examples).
- 🤝 **Contributing** – see [CONTRIBUTING.md](CONTRIBUTING.md).
- 📝 **Changelog** – see [CHANGELOG.md](CHANGELOG.md) for recent updates.

## Contributing

We 💜 external contributions! Start with [CONTRIBUTING.md](CONTRIBUTING.md) and our Code of Conduct.

## Need Help?

Open an [issue](../../issues) or start a discussion—questions, ideas, and feedback are welcome!

## License

MIT License - See [LICENSE](./LICENSE) for details.
