# ModelCapabilities

The `ModelCapabilities` class represents the capabilities, constraints, and parameters for a specific OpenAI model.

## Class Reference

::: openai_model_registry.registry.ModelCapabilities
    options:
      show_root_heading: false
      show_source: true

## Usage Examples

### Accessing Basic Properties

```python
from openai_model_registry import ModelRegistry

registry = ModelRegistry.get_instance()
capabilities = registry.get_capabilities("gpt-4o")

# Access basic properties
print(f"Model name: {capabilities.openai_model_name}")
print(f"Context window: {capabilities.context_window}")
print(f"Max output tokens: {capabilities.max_output_tokens}")
print(f"Supports streaming: {capabilities.supports_streaming}")
print(f"Supports structured output: {capabilities.supports_structured}")

# Check for aliases
if capabilities.aliases:
    print(f"Aliases: {', '.join(capabilities.aliases)}")
```

### Validating Parameters

```python
from openai_model_registry import ModelRegistry, ModelRegistryError

registry = ModelRegistry.get_instance()
capabilities = registry.get_capabilities("gpt-4o")

# Validate a parameter
try:
    capabilities.validate_parameter("temperature", 0.7)
    print("Temperature 0.7 is valid")
except ModelRegistryError as e:
    print(f"Invalid parameter: {e}")

# Validate with context (tracking used parameters)
used_params = set()
capabilities.validate_parameter("temperature", 0.7, used_params)
print(f"Used parameters: {used_params}")  # Contains 'temperature'

# Validate multiple parameters
params_to_validate = {
    "temperature": 0.7,
    "top_p": 0.9,
    "max_completion_tokens": 500
}

for param_name, value in params_to_validate.items():
    try:
        capabilities.validate_parameter(param_name, value, used_params)
        print(f"✓ {param_name}={value} is valid")
    except ModelRegistryError as e:
        print(f"✗ {param_name}={value} is invalid: {e}")
```

### Working with Parameter Constraints

```python
from openai_model_registry import ModelRegistry

registry = ModelRegistry.get_instance()
capabilities = registry.get_capabilities("gpt-4o")

# Get a specific constraint
temperature_constraint = capabilities.get_constraint("temperature")
if temperature_constraint:
    print(f"Type: {type(temperature_constraint).__name__}")
    print(f"Min value: {temperature_constraint.min_value}")
    print(f"Max value: {temperature_constraint.max_value}")
    print(f"Description: {temperature_constraint.description}")

# List all parameter references
for param_ref in capabilities.supported_parameters:
    constraint = capabilities.get_constraint(param_ref.ref)
    print(f"Parameter: {param_ref.ref}")
    print(f"  Description: {param_ref.description}")
    print(f"  Constraint type: {type(constraint).__name__ if constraint else 'None'}")
```

### Creating Custom Capabilities

```python
from openai_model_registry import ModelRegistry
from openai_model_registry.registry import ModelCapabilities
from openai_model_registry.constraints import NumericConstraint, EnumConstraint
from typing import Dict, Union

# Get existing constraints for reference
registry = ModelRegistry.get_instance()
base_capabilities = registry.get_capabilities("gpt-4o")

# Create custom capabilities (with basic properties)
custom_capabilities = ModelCapabilities(
    model_name="custom-model",
    openai_model_name="custom-model",
    context_window=8192,
    max_output_tokens=4096,
    supports_streaming=True,
    supports_structured=True,
)

# Add aliases
custom_capabilities.aliases = ["custom-alias"]

# Copy supported parameters from base model
custom_capabilities.supported_parameters = base_capabilities.supported_parameters

# Add constraints manually
constraints: Dict[str, Union[NumericConstraint, EnumConstraint]] = {
    "temperature": NumericConstraint(
        min_value=0.0,
        max_value=1.0,
        allow_float=True,
        allow_int=True,
        description="Custom temperature description"
    ),
    "response_format": EnumConstraint(
        allowed_values=["text", "json_schema"],
        description="Custom response format description"
    )
}
custom_capabilities._constraints = constraints

# Use custom capabilities
custom_capabilities.validate_parameter("temperature", 0.7)
```
