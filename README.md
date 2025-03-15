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

## Development

### Setup Development Environment

This project uses Poetry for dependency management:

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### Pre-commit Hooks

We use pre-commit hooks to enforce code quality:

```bash
# Install pre-commit hooks
poetry run pre-commit install

# Run hooks manually
poetry run pre-commit run --all-files
```

### Testing

```bash
# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=openai_model_registry
```

### CI/CD Pipeline

The repository uses GitHub Actions for continuous integration and deployment:

- **CI**: Runs on all pushes to main and pull requests, ensuring code quality and tests pass
- **Release**: Automatically publishes to PyPI when a new release is created

See the workflows in the `.github/workflows` directory for more details.
