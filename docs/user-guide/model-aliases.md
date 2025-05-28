# Model Aliases and Naming Conventions

This guide explains how OpenAI model names work, including aliases, dated versions, and feature indicators.

## Understanding Model Names

OpenAI uses different naming patterns for their models, and the Model Registry handles all these variations seamlessly.

### Base Model Names

Base model names refer to the latest version of a model family:

```python
from openai_model_registry import ModelRegistry

registry = ModelRegistry.get_default()

# These all refer to model families
gpt4o = registry.get_capabilities("gpt-4o")
gpt4o_mini = registry.get_capabilities("gpt-4o-mini")
o1 = registry.get_capabilities("o1")
# Expected output: Successfully loads latest version capabilities
```

### Dated Model Versions

OpenAI releases specific dated versions of models. These have exact release dates in their names:

```python
# Dated versions with specific capabilities
gpt4o_dated = registry.get_capabilities("gpt-4o-2024-05-13")
o1_dated = registry.get_capabilities("o1-2024-12-17")

print(f"GPT-4o dated version: {gpt4o_dated.openai_model_name}")
print(f"O1 dated version: {o1_dated.openai_model_name}")
# Expected output: GPT-4o dated version: gpt-4o-2024-05-13
#                  O1 dated version: o1-2024-12-17
```

### Model Aliases

Some models have aliases - alternative names that point to the same underlying model:

```python
# Check for aliases
capabilities = registry.get_capabilities("gpt-4o")

if capabilities.aliases:
    print(f"Aliases for gpt-4o: {', '.join(capabilities.aliases)}")
else:
    print("No aliases found for this model")
# Expected output: (varies based on model configuration)
```

## Naming Conventions

### Mini Models

Models with `-mini` in the name are typically:

- Lower cost alternatives
- Smaller context windows (but still substantial)
- Faster response times
- Suitable for simpler tasks

```python
# Compare mini vs full model
gpt4o = registry.get_capabilities("gpt-4o")
gpt4o_mini = registry.get_capabilities("gpt-4o-mini")

print(f"GPT-4o context: {gpt4o.context_window}")
print(f"GPT-4o-mini context: {gpt4o_mini.context_window}")
print(f"GPT-4o cost tier: Standard")
print(f"GPT-4o-mini cost tier: Lower")
# Expected output: GPT-4o context: 128000
#                  GPT-4o-mini context: 128000
#                  GPT-4o cost tier: Standard
#                  GPT-4o-mini cost tier: Lower
```

### Model Families

Different model families have different strengths:

- **GPT-4o**: Optimized for speed and efficiency
- **O1**: Reasoning-focused models with longer thinking time
- **GPT-4**: Previous generation with proven reliability

```python
# Compare model families
gpt4o = registry.get_capabilities("gpt-4o")
o1 = registry.get_capabilities("o1")

print(f"GPT-4o supports streaming: {gpt4o.supports_streaming}")
print(f"O1 supports streaming: {o1.supports_streaming}")
print(f"GPT-4o supports structured output: {gpt4o.supports_structured}")
print(f"O1 supports structured output: {o1.supports_structured}")
# Expected output: GPT-4o supports streaming: True
#                  O1 supports streaming: True
#                  GPT-4o supports structured output: True
#                  O1 supports structured output: True
```

## Feature Indicators

### Structured Output Support

Models that support structured output can return JSON following a specific schema:

```python
# Check structured output support
capabilities = registry.get_capabilities("gpt-4o")

if capabilities.supports_structured:
    print("✅ This model supports JSON schema / structured output")
    print("You can use response_format with json_schema")
else:
    print("❌ This model does not support structured output")
# Expected output: ✅ This model supports JSON schema / structured output
#                  You can use response_format with json_schema
```

### Streaming Support

Most modern models support streaming responses:

```python
# Check streaming support
capabilities = registry.get_capabilities("gpt-4o")

if capabilities.supports_streaming:
    print("✅ This model supports streaming responses")
    print("You can use stream=True in your API calls")
else:
    print("❌ This model does not support streaming")
# Expected output: ✅ This model supports streaming responses
#                  You can use stream=True in your API calls
```

## Model Selection Guidelines

### When to Use Different Models

**Use GPT-4o when:**

- You need fast responses
- Working with general-purpose tasks
- Cost efficiency is important
- Streaming is required

**Use O1 when:**

- Complex reasoning is required
- Mathematical or logical problems
- Code analysis and generation
- You can wait for longer response times

**Use Mini variants when:**

- Simple tasks or queries
- High volume applications
- Cost optimization is critical
- Fast turnaround needed

```python
# Example: Choosing model based on task complexity
def choose_model_for_task(task_complexity):
    registry = ModelRegistry.get_default()

    if task_complexity == "simple":
        return registry.get_capabilities("gpt-4o-mini")
    elif task_complexity == "reasoning":
        return registry.get_capabilities("o1")
    else:
        return registry.get_capabilities("gpt-4o")


# Example usage
simple_task_model = choose_model_for_task("simple")
reasoning_task_model = choose_model_for_task("reasoning")
general_task_model = choose_model_for_task("general")

print(f"Simple tasks: {simple_task_model.openai_model_name}")
print(f"Reasoning tasks: {reasoning_task_model.openai_model_name}")
print(f"General tasks: {general_task_model.openai_model_name}")
# Expected output: Simple tasks: gpt-4o-mini
#                  Reasoning tasks: o1
#                  General tasks: gpt-4o
```

## Working with Model Versions

### Checking Model Information

```python
from openai_model_registry import ModelRegistry

registry = ModelRegistry.get_default()


def analyze_model(model_name):
    """Analyze a model's capabilities and naming."""
    capabilities = registry.get_capabilities(model_name)

    print(f"\n=== {model_name} ===")
    print(f"Official name: {capabilities.openai_model_name}")
    print(f"Context window: {capabilities.context_window:,} tokens")
    print(f"Max output: {capabilities.max_output_tokens:,} tokens")
    print(f"Supports streaming: {capabilities.supports_streaming}")
    print(f"Supports structured output: {capabilities.supports_structured}")

    if capabilities.aliases:
        print(f"Aliases: {', '.join(capabilities.aliases)}")

    return capabilities


# Analyze different models
models_to_check = ["gpt-4o", "gpt-4o-mini", "o1"]
for model in models_to_check:
    analyze_model(model)
# Expected output: Detailed analysis of each model's capabilities
```

## Next Steps

Now that you understand model naming and features, explore:

- [Parameter Validation](parameter-validation.md) - Learn how different models have different parameter constraints
- [Advanced Usage](advanced-usage.md) - Discover advanced registry features
- [Model Capabilities](model-capabilities.md) - Deep dive into model capability details
