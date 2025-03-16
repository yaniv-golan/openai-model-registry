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

### CLI Integration Example

The package includes an example of integrating the Model Registry into a CLI application:

```python
# Create a CLI app with model registry update command
@cli.command("update-registry")
@click.option("--force", is_flag=True, help="Force update even if registry is current")
def update_registry_command(force: bool) -> None:
    """Update the model registry with the latest model information."""
    registry = ModelRegistry.get_instance()
    result = registry.refresh_from_remote(force=force)
    if result.success:
        click.echo("Model registry updated successfully.")
    else:
        click.echo(f"Update failed: {result.message}")

# Automatically check for updates
def get_update_notification() -> Optional[str]:
    """Check if registry updates are available and return notification message."""
    registry = ModelRegistry.get_instance()
    result = registry.check_for_updates()
    if result.status.name == "UPDATE_AVAILABLE":
        return "Model registry updates are available. Run 'myapp update-registry'."
    return None
```

For a complete example including features like parameter validation and update notifications, see [examples/cli_integration.py](./examples/cli_integration.py).

## Command Line Interface

Update the local registry data:

```bash
openai-model-registry-update
```

## Registry Configuration

### Local Registry

The registry data is stored locally in the following locations:

- **Model Registry**: `{package_directory}/config/models.yml`
  - Override with environment variable: `MODEL_REGISTRY_PATH`

- **Parameter Constraints**: `{package_directory}/config/parameter_constraints.yml`
  - Override with environment variable: `PARAMETER_CONSTRAINTS_PATH`

Example of setting custom paths:

```python
import os

# Set custom registry paths
os.environ["MODEL_REGISTRY_PATH"] = "/path/to/custom/models.yml"
os.environ["PARAMETER_CONSTRAINTS_PATH"] = "/path/to/custom/parameter_constraints.yml"

# Then initialize the registry
from openai_model_registry import ModelRegistry
registry = ModelRegistry.get_instance()
```

### Remote Registry

When updating the registry, data is fetched from:

- **Default Remote URL**: `https://raw.githubusercontent.com/openai-model-registry/openai-model-registry/main/src/openai_model_registry/config/models.yml`

You can specify a custom URL when updating:

```python
# Using a custom URL
registry.refresh_from_remote(url="https://example.com/custom-models.yml")

# Check for updates from a custom source
result = registry.check_for_updates(url="https://example.com/custom-models.yml")
```

Or via command line:

```bash
openai-model-registry-update --url https://example.com/custom-models.yml
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
