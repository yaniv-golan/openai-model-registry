# OpenAI Model Registry

[![PyPI version](https://img.shields.io/pypi/v/openai-model-registry.svg)](https://pypi.org/project/openai-model-registry/)
[![Python Versions](https://img.shields.io/pypi/pyversions/openai-model-registry.svg)](https://pypi.org/project/openai-model-registry/)
[![CI Status](https://github.com/yaniv-golan/openai-model-registry/workflows/Python%20CI/badge.svg)](https://github.com/yaniv-golan/openai-model-registry/actions)
[![codecov](https://codecov.io/gh/yaniv-golan/openai-model-registry/branch/main/graph/badge.svg)](https://codecov.io/gh/yaniv-golan/openai-model-registry)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

📚 **[View the Documentation](https://yaniv-golan.github.io/openai-model-registry/)** - Comprehensive guides and API reference

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

The registry data is stored locally following the [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html), with the following lookup order:

1. **Environment Variables** (if set):
   - `MODEL_REGISTRY_PATH` for model registry
   - `PARAMETER_CONSTRAINTS_PATH` for parameter constraints

2. **User Configuration Directory**:
   - Linux: `~/.config/openai-model-registry/`
   - macOS: `~/Library/Application Support/openai-model-registry/`
   - Windows: `%LOCALAPPDATA%\openai-model-registry\`

3. **Package Installation Directory** (fallback):
   - `{package_directory}/config/`

The specific files used are:

- **Model Registry**: `models.yml`
- **Parameter Constraints**: `parameter_constraints.yml`

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

## API Reference

The OpenAI Model Registry provides a comprehensive API for working with OpenAI models, their capabilities, and parameter validation.

### Core Classes

#### `ModelRegistry`

The central singleton class that maintains the registry of models and their capabilities.

```python
from openai_model_registry import ModelRegistry

# Get the singleton instance
registry = ModelRegistry.get_instance()
```

**Key Methods:**

- `get_capabilities(model: str) -> ModelCapabilities`: Get the capabilities for a model
- `get_parameter_constraint(ref: str) -> Union[NumericConstraint, EnumConstraint]`: Get a parameter constraint by reference
- `refresh_from_remote(url: Optional[str] = None, force: bool = False) -> RegistryUpdateResult`: Update the registry from a remote source
- `check_for_updates(url: Optional[str] = None) -> RegistryUpdateResult`: Check if updates are available

#### `ModelCapabilities`

Represents the capabilities and constraints of a specific model.

```python
# Get model capabilities
capabilities = registry.get_capabilities("gpt-4o")

# Access properties
context_window = capabilities.context_window
max_tokens = capabilities.max_output_tokens
supports_streaming = capabilities.supports_streaming
```

**Properties:**

- `context_window: int`: Maximum context window size in tokens
- `max_output_tokens: int`: Maximum output tokens the model can generate
- `supports_structured: bool`: Whether the model supports structured output (JSON mode)
- `supports_streaming: bool`: Whether the model supports streaming responses
- `supported_parameters: List[ParameterReference]`: List of supported parameter references
- `description: str`: Human-readable description of the model
- `min_version: Optional[ModelVersion]`: Minimum supported version for dated models
- `openai_model_name: Optional[str]`: The model name as used in the OpenAI API
- `aliases: List[str]`: List of aliases for this model

**Methods:**

- `validate_parameter(param_name: str, value: Any) -> None`: Validate a parameter against the model's constraints

### Parameter Constraints

#### `NumericConstraint`

Defines constraints for numeric parameters like temperature or top_p.

**Properties:**

- `min_value: float`: Minimum allowed value
- `max_value: Optional[float]`: Maximum allowed value (can be None for model-dependent limits)
- `description: str`: Human-readable description
- `allow_float: bool`: Whether float values are allowed
- `allow_int: bool`: Whether integer values are allowed

#### `EnumConstraint`

Defines constraints for string-enum parameters like reasoning_effort.

**Properties:**

- `allowed_values: List[str]`: List of allowed string values
- `description: str`: Human-readable description

### Version Handling

#### `ModelVersion`

Represents a model version in the format YYYY-MM-DD.

```python
from openai_model_registry import ModelVersion

# Create a version
version = ModelVersion(2024, 8, 1)

# Parse from string
version = ModelVersion.from_string("2024-08-01")

# Compare versions
is_newer = version > ModelVersion(2024, 7, 15)
```

**Properties:**

- `year: int`: Year component
- `month: int`: Month component
- `day: int`: Day component

**Methods:**

- `from_string(version_str: str) -> ModelVersion`: Create a version from a string
- `parse_from_model(model: str) -> Optional[Tuple[str, ModelVersion]]`: Parse a model name into base name and version

#### `RegistryUpdateStatus`

Enum representing the status of a registry update operation.

**Values:**

- `UP_TO_DATE`: Registry is already up to date
- `UPDATE_AVAILABLE`: Updates are available
- `UPDATED`: Registry was successfully updated
- `ERROR`: An error occurred during the update

#### `RegistryUpdateResult`

Result of a registry update operation.

**Properties:**

- `status: RegistryUpdateStatus`: Status of the update
- `message: str`: Human-readable message
- `success: bool`: Whether the operation was successful
- `old_version: Optional[str]`: Previous registry version
- `new_version: Optional[str]`: New registry version

### Error Classes

#### `ModelRegistryError`

Base class for all registry-related errors.

#### `ModelVersionError`

Base class for version-related errors.

#### `InvalidDateError`

Raised when a model version has an invalid date format.

#### `VersionTooOldError`

Raised when a model version is older than the minimum supported version.

**Properties:**

- `model: str`: The requested model
- `min_version: str`: The minimum supported version
- `alias: Optional[str]`: A suggested alias to use instead

#### `ModelNotSupportedError`

Raised when a model is not supported by the registry.

**Properties:**

- `model: Optional[str]`: The requested model
- `available_models: Optional[Union[List[str], Set[str], Dict[str, Any]]]`: Available models

#### `TokenParameterError`

Raised when there's an issue with token-related parameters.

**Properties:**

- `param_name: str`: The parameter name
- `value: Any`: The invalid value
