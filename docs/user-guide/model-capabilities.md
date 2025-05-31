# Model Capabilities

This guide explains how to work with model capabilities in the OpenAI Model Registry.

## What are Model Capabilities?

Model capabilities represent the features, limitations, and parameters supported by a specific model. These include:

- Context window size
- Maximum output tokens
- Support for streaming
- Support for structured output
- Support for web search
- Supported parameters and their constraints

**Note on Naming Conventions:**

- **`gpt-4`** → resolves to the latest dated GPT-4 release (`gpt-4o-2025-05-13`).
- **`*-mini`** → a lower-cost, smaller-context sibling model.
- **Structured output** means the model supports JSON schema / function calling.
- **Web search** means the model can search the web for up-to-date information.

For a complete guide on model naming and selection, see [Model Aliases and Naming Conventions](model-aliases.md).

## Accessing Model Capabilities

You can access model capabilities through the `ModelRegistry` class:

```python
from openai_model_registry import ModelRegistry

# Get the registry instance
registry = ModelRegistry.get_default()

# Get capabilities for a model
capabilities = registry.get_capabilities("gpt-4o")

# Access capability information
print(f"Context window: {capabilities.context_window}")
print(f"Max output tokens: {capabilities.max_output_tokens}")
print(f"Supports structured output: {capabilities.supports_structured}")
print(f"Supports streaming: {capabilities.supports_streaming}")
print(f"Supports web search: {capabilities.supports_web_search}")
# Expected output: Context window: 128000
#                  Max output tokens: 16384
#                  Supports structured output: True
#                  Supports streaming: True
#                  Supports web search: True
```

## Model Aliases

Some models have aliases - different names that refer to the same underlying model. For example, a dated model version might have an alias to the base model name.

```python
from openai_model_registry import ModelRegistry

registry = ModelRegistry.get_default()

# Get capabilities for a model
capabilities = registry.get_capabilities("gpt-4o")

# Check if the model has aliases
if capabilities.aliases:
    print(f"Aliases for this model: {', '.join(capabilities.aliases)}")
# Expected output: (may vary based on model configuration)
```

## Comparing Model Capabilities

You can compare capabilities between different models:

```python
from openai_model_registry import ModelRegistry

registry = ModelRegistry.get_default()

gpt4o = registry.get_capabilities("gpt-4o")
gpt4o_mini = registry.get_capabilities("gpt-4o-mini")

print(f"GPT-4o context window: {gpt4o.context_window}")
print(f"GPT-4o-mini context window: {gpt4o_mini.context_window}")

print(f"GPT-4o max output tokens: {gpt4o.max_output_tokens}")
print(f"GPT-4o-mini max output tokens: {gpt4o_mini.max_output_tokens}")
# Expected output: GPT-4o context window: 128000
#                  GPT-4o-mini context window: 128000
#                  GPT-4o max output tokens: 16384
#                  GPT-4o-mini max output tokens: 16384
```

## Capabilities for Dated Versions

The registry supports dated model versions, which have specific capabilities that may differ from the base model:

```python
from openai_model_registry import ModelRegistry

registry = ModelRegistry.get_default()

# Get capabilities for a dated version
capabilities = registry.get_capabilities("gpt-4o-2024-05-13")

# These capabilities might differ from the base "gpt-4o" model
print(f"Context window: {capabilities.context_window}")
# Expected output: Context window: 128000
```

## Model Deprecation Status

Models can have deprecation information that helps you understand their lifecycle:

```python
from openai_model_registry import ModelRegistry

registry = ModelRegistry.get_default()

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
# Expected output: Deprecation status: active
```

## Checking Model Status

You can also check if a model is active before using it:

```python
from openai_model_registry import ModelRegistry
from openai_model_registry.deprecation import ModelSunsetError

registry = ModelRegistry.get_default()

try:
    # This will raise an exception if the model is sunset
    registry.assert_model_active("gpt-4o")
    print("Model is active and safe to use")
except ModelSunsetError as e:
    print(f"Model is sunset: {e}")
    # Use the replacement model if available
    if e.replacement:
        capabilities = registry.get_capabilities(e.replacement)
# Expected output: Model is active and safe to use
```

## Web Search Support

Some models can search the web for up-to-date information. The OpenAI Model Registry uses a single boolean flag, `supports_web_search`, to indicate this capability. However, how web search is invoked and its behavior differs between OpenAI's Chat Completions API and Responses API.

> **⚠️ Azure OpenAI Users:** If you're using Azure OpenAI endpoints, please note that standard Azure Chat Completions and Responses APIs **do not support** the `web_search_preview` tool, regardless of what `supports_web_search` indicates. This is a platform limitation, not a model limitation. See our [Azure OpenAI Usage Guide](azure-openai.md) for detailed guidance and alternative approaches.

### Two Approaches to Web Search

1. **Chat Completions API (Always Searches):**

   - **Models:** Special "search-preview" models like `gpt-4o-search-preview` and `gpt-4o-mini-search-preview`.
   - **Behavior:** These models automatically perform a web search *before every response*.
   - **Use Case:** Suitable when you require web-augmented answers for every user query.
   - **Limitations:** May have a restricted set of supported API parameters compared to standard chat models.

1. **Responses API (Conditional, Tool-Based Search):**

   - **Models:** Reasoning-enabled models such as `gpt-4o`, `gpt-4.1` (excluding `gpt-4.1-nano`), and the "O-series" (`o1`, `o3`, etc.).
   - **Behavior:** These models can use web search as a *tool*. The model intelligently decides whether a web search is necessary to answer the current query.
   - **Use Case:** Offers more flexibility, as web search is only performed when needed, potentially saving costs and reducing latency.
   - **Invocation:** Requires using the `/v1/responses` API endpoint and including `{"type": "web_search_preview"}` in the `tools` array of your request.

### How the Registry Captures This

The Model Registry simplifies this by:

- **Unified Flag:** Using `capabilities.supports_web_search` (boolean) to indicate if a model *can* perform web search, regardless of the API.
- **Descriptive Information:** The `description` field for search-preview models in the underlying `models.yml` often clarifies their "always searches" behavior (e.g., "GPT-4o with built-in web search for Chat Completions API (always searches)").
- **Model Naming:** Following OpenAI's naming (e.g., `-search-preview` suffix for Chat API models).

The registry's role is to inform your application if web search is *available*. It's the application's responsibility to use the correct API endpoint and parameters based on the chosen model and desired search behavior.

### Example: Checking and Using Web Search

```python
from openai_model_registry import ModelRegistry

# Assuming 'openai' client is initialized

registry = ModelRegistry.get_default()


def get_web_augmented_response(model_name: str, query: str):
    try:
        capabilities = registry.get_capabilities(model_name)
    except Exception as e:
        print(f"Error getting capabilities for {model_name}: {e}")
        return None

    if not capabilities.supports_web_search:
        print(
            f"Model {model_name} does not support web search. Using standard completion."
        )
        # Fallback to standard chat completion if web search is not supported
        # This is a simplified example; you might have different fallback logic
        try:
            response = openai.chat.completions.create(
                model=model_name,  # Or a default non-web-search model
                messages=[{"role": "user", "content": query}],
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error with standard completion for {model_name}: {e}")
            return None

    # Determine API and invocation based on model name convention
    if model_name.endswith("-search-preview"):
        print(f"Using Chat Completions API for {model_name} (always searches).")
        try:
            response = openai.chat.completions.create(
                model=model_name, messages=[{"role": "user", "content": query}]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error with Chat API for {model_name}: {e}")
            return None
    else:
        print(f"Using Responses API for {model_name} (conditional search).")
        try:
            response = openai.responses.create(
                model=model_name,
                tools=[{"type": "web_search_preview"}],
                input=query,
                # Note: The actual 'input' structure for Responses API
                # might be more complex depending on your needs (e.g., messages list)
            )
            # Process Responses API output (may differ from Chat Completions)
            # This is a simplified example
            if hasattr(response, "output") and response.output:
                return response.output[0].text.value  # Example access
            return "Response format from Responses API needs specific handling."
        except Exception as e:
            print(f"Error with Responses API for {model_name}: {e}")
            return None


# Test cases
# print(get_web_augmented_response("gpt-4o-search-preview", "What's the weather like today?"))
# print(get_web_augmented_response("gpt-4o", "Latest news on AI advancements?"))
# print(get_web_augmented_response("gpt-4.1-nano", "Tell me a joke.")) # Should use fallback
```

**Key Considerations:**

- **`gpt-4.1-nano`:** Explicitly does **not** support web search, even though other `gpt-4.1` variants do. The registry correctly reflects this (`supports_web_search: false`).
- **API Endpoint:** Remember to use `/v1/chat/completions` for search-preview models and `/v1/responses` for tool-based search with other compatible models.
- **Parameter Validation:** Web search specific parameters (e.g., `web_search_options`, `user_location`) are handled and validated by OpenAI's API, not by this registry. The registry only indicates the *capability's existence*.

## Next Steps

Now that you understand model capabilities, learn about [Parameter Validation](parameter-validation.md) to ensure your application uses valid parameter values.
