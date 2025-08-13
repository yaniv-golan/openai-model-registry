# Parameter Validation

This guide explains how to validate parameters against model constraints using the OpenAI Model Registry.

## Why Validate Parameters?

Parameter validation ensures that your application uses valid values for model parameters, preventing runtime errors when calling the OpenAI API. Different models may have different constraints for the same parameter.

## Basic Parameter Validation

You can validate parameters through the model capabilities object:

```python
from openai_model_registry import ModelRegistry

registry = ModelRegistry.get_default()
capabilities = registry.get_capabilities("gpt-4o")

# Validate a temperature value
try:
    capabilities.validate_parameter("temperature", 0.7)
    print("✅ Valid temperature")
except ValueError as e:
    print(f"❌ Invalid temperature: {e}")
# Expected output: ✅ Valid temperature
```

## Handling Validation Errors

Validation errors provide detailed information about why a parameter is invalid:

```python
from openai_model_registry import ModelRegistry

registry = ModelRegistry.get_default()
capabilities = registry.get_capabilities("gpt-4o")

try:
    # Invalid temperature (outside of allowed range)
    capabilities.validate_parameter("temperature", 3.0)
except Exception as e:
    print(f"Validation error: {e}")
    # Expected output: Validation error: Parameter 'temperature' must be between 0 and 2.
    # Description: Controls randomness: Lowering results in less random completions.
    # Current value: 3.0
```

## Common Parameter Types

### Numeric Parameters

Numeric parameters typically have constraints for:

- Minimum value
- Maximum value
- Whether the parameter allows floats, integers, or both

Examples of numeric parameters:

- `temperature`: Controls randomness (typically 0-2)
- `top_p`: Controls diversity via nucleus sampling (typically 0-1)
- `max_tokens`: Controls maximum completion length (typically 1-model_max)

### Enum Parameters

Enum parameters accept only specific string values from a predefined list.

Examples of enum parameters:

- `response_format`: Format of the model's output (e.g., "text", "json_schema")
- `reasoning_effort` (O1 model): Level of reasoning effort (e.g., "low", "medium", "high")

## Model-Specific Parameters

Different models may support different parameters. For example, the O1 model has parameters not available in other models:

```python
from openai_model_registry import ModelRegistry

# Initialize registry
registry = ModelRegistry.get_default()

# Get O1 capabilities
o1_capabilities = registry.get_capabilities("o1")

# Validate O1-specific parameter
try:
    o1_capabilities.validate_parameter("reasoning_effort", "medium")
    print("reasoning_effort 'medium' is valid for O1")
except Exception as e:
    print(f"Invalid parameter: {e}")
# Expected output: reasoning_effort 'medium' is valid for O1
```

## Getting Supported Parameters

You can retrieve the list of parameters supported by a specific model:

```python
from openai_model_registry import ModelRegistry

registry = ModelRegistry.get_default()
capabilities = registry.get_capabilities("gpt-4o")

# Get supported parameters (inline)
param_names = list((capabilities.inline_parameters or {}).keys())
print(f"Supported parameters: {', '.join(sorted(param_names))}")
# Expected output: Supported parameters: max_tokens, temperature, top_p, ...
```

## Next Steps

Now that you understand parameter validation, learn about [Advanced Usage](advanced-usage.md) for more complex scenarios and registry management.

## Recommended defaults (chat models)

These are sensible starting points for common chat models. Adjust for your app:

- Temperature: 0.7
- Top_p: 1.0
- Max tokens: choose per model up to its max_output_tokens
- Response format: "text" (use JSON mode where supported for structured outputs)

Note: Not all models expose all knobs (e.g., O1 family does not support classic sampling controls). Check `omr --format json models get <model> --parameters-only` to see what a given model supports.
