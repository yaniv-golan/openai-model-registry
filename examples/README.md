# OpenAI Model Registry Examples

This directory contains example scripts demonstrating how to use the `openai_model_registry` package.

## Basic Usage

[basic_usage.py](./basic_usage.py) - Shows how to:

- Get information about available models
- Check model capabilities (context window, max tokens, etc.)
- Validate parameters for different models

Run the example:

```bash
python examples/basic_usage.py
```

## Advanced Use Cases

More advanced examples will be added here in the future, such as:

- Custom registry configuration
- Using the registry with OpenAI API calls
- Handling model versioning in production code

## CLI Integration Example

The `cli_integration.py` example demonstrates how to integrate the OpenAI Model Registry into a CLI application. This example showcases:

1. **Automatic Update Notifications**: Non-intrusive checks for registry updates that run periodically
1. **Registry Update Command**: A dedicated command to update the registry with user confirmation
1. **Parameter Validation**: Validating model parameters against model capabilities
1. **Token Limit Enforcement**: Enforcing context window and output token limits

### Running the Example

```bash
# Install required dependencies
pip install click

# Run the example CLI
python examples/cli_integration.py --help

# Try the completion command
python examples/cli_integration.py completion --model gpt-4 --prompt "Hello, world!" --temperature 0.7

# Update the registry
python examples/cli_integration.py update-registry
```

### Key Features

The example implements several key features:

#### Non-intrusive Update Checks

```python
def get_update_notification(quiet: bool = False) -> Optional[str]:
    """Check if registry updates are available and return notification message if needed."""
    # Checks if it's time to check for updates (once every 7 days by default)
    # Returns a notification message if updates are available
```

#### Update Registry Command

```python
@cli.command("update-registry")
@click.option("--url", help="URL to fetch registry updates from", default=None)
@click.option("--force", is_flag=True, help="Force update even if registry is current")
@click.option("--auto-confirm", "-y", is_flag=True, help="Automatically confirm update")
def update_registry_command(...):
    """Update the model registry with the latest model information."""
    # Checks for updates
    # Prompts for confirmation (unless auto-confirm is set)
    # Updates the registry
```

#### Model Parameter Validation

```python
def validate_model_parameters(model: str, params: Dict[str, Any]) -> None:
    """Validate that model parameters are supported by the model."""
    # Gets model capabilities
    # Validates parameters against model capabilities
    # Enforces token limits
```

This example provides a complete template for integrating the Model Registry into your own CLI applications.
