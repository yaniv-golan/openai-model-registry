# Model Capabilities

This guide explains how to work with model capabilities in the OpenAI Model Registry.

## What are Model Capabilities?

Model capabilities represent the features, limitations, and parameters supported by a specific model. These include:

- Context window size
- Maximum output tokens
- Support for streaming
- Support for structured output
- Supported parameters and their constraints

## Accessing Model Capabilities

You can access model capabilities through the `ModelRegistry` class:

```python
from openai_model_registry import ModelRegistry

# Get the registry instance
registry = ModelRegistry.get_instance()

# Get capabilities for a specific model
capabilities = registry.get_capabilities("gpt-4o")

# Access basic capabilities
print(f"Context window: {capabilities.context_window}")
print(f"Max output tokens: {capabilities.max_output_tokens}")
print(f"Supports streaming: {capabilities.supports_streaming}")
print(f"Supports structured output: {capabilities.supports_structured}")
```

## Model Aliases

Some models have aliases - different names that refer to the same underlying model. For example, a dated model version might have an alias to the base model name.

```python
# Get capabilities for a model
capabilities = registry.get_capabilities("gpt-4o")

# Check if the model has aliases
if capabilities.aliases:
    print(f"Aliases for this model: {', '.join(capabilities.aliases)}")
```

## Comparing Model Capabilities

You can compare capabilities between different models:

```python
gpt4o = registry.get_capabilities("gpt-4o")
gpt4o_mini = registry.get_capabilities("gpt-4o-mini")

print(f"GPT-4o context window: {gpt4o.context_window}")
print(f"GPT-4o-mini context window: {gpt4o_mini.context_window}")

print(f"GPT-4o max output tokens: {gpt4o.max_output_tokens}")
print(f"GPT-4o-mini max output tokens: {gpt4o_mini.max_output_tokens}")
```

## Capabilities for Dated Versions

The registry supports dated model versions, which have specific capabilities that may differ from the base model:

```python
# Get capabilities for a dated version
capabilities = registry.get_capabilities("gpt-4o-2024-05-13")

# These capabilities might differ from the base "gpt-4o" model
print(f"Context window: {capabilities.context_window}")
```

## Model Deprecation Status

Models can have deprecation information that helps you understand their lifecycle:

```python
# Get capabilities for a model
capabilities = registry.get_capabilities("gpt-4o")

# Check deprecation status
print(f"Deprecation status: {capabilities.deprecation.status}")

if capabilities.is_deprecated:
    print("⚠️  This model is deprecated")
    if capabilities.deprecation.replacement:
        print(f"Recommended replacement: {capabilities.deprecation.replacement}")
    if capabilities.deprecation.migration_guide:
        print(f"Migration guide: {capabilities.deprecation.migration_guide}")

if capabilities.is_sunset:
    print("🚫 This model is sunset and no longer available")

# Get HTTP headers for deprecation status
headers = registry.get_sunset_headers("gpt-4o")
if headers:
    print(f"Sunset headers: {headers}")
```

## Checking Model Status

You can also check if a model is active before using it:

```python
from openai_model_registry.deprecation import ModelSunsetError

try:
    # This will raise an exception if the model is sunset
    registry.assert_model_active("gpt-4o")
    print("Model is active and safe to use")
except ModelSunsetError as e:
    print(f"Model is sunset: {e}")
    # Use the replacement model if available
    if e.replacement:
        capabilities = registry.get_capabilities(e.replacement)
```

## Next Steps

Now that you understand model capabilities, learn about [Parameter Validation](parameter-validation.md) to ensure your application uses valid parameter values.
