# Azure OpenAI Usage

This guide explains important considerations when using the OpenAI Model Registry with Azure OpenAI endpoints.

## Overview

Azure OpenAI provides access to OpenAI's models through Microsoft's cloud infrastructure, but there are important differences in feature support compared to OpenAI's direct API. The most significant difference relates to **web search capabilities**.

## Web Search Limitations on Azure

### Standard Azure OpenAI APIs (Chat & Responses)

**⚠️ Important**: Standard Azure OpenAI Chat Completions and Responses APIs **do not support** the `web_search_preview` tool, even for models that our registry indicates have `supports_web_search: true`.

```python
from openai_model_registry import ModelRegistry

registry = ModelRegistry.get_default()
capabilities = registry.get_capabilities("gpt-4o")

# This will return True (the model itself supports web search)
print(f"Model supports web search: {capabilities.supports_web_search}")
# Output: Model supports web search: True

# However, if you're using Azure OpenAI standard endpoints:
# - *.openai.azure.com/openai/deployments/.../chat/completions
# - *.openai.azure.com/openai/deployments/.../responses
# Using web_search_preview tool will FAIL with an error
```

### Why This Limitation Exists

Microsoft's Azure OpenAI documentation explicitly states that the `web_search_preview` tool is "not currently supported" in standard Azure endpoints. This is a platform-level limitation, not a model limitation.

The OpenAI Model Registry reflects the **underlying model capabilities** as defined by OpenAI. When these models are deployed through Azure's infrastructure, certain features may be restricted or unavailable.

## Recommended Approach for Azure Users

### 1. Check Your Endpoint Type

Before using web search capabilities, determine if you're using Azure OpenAI:

```python
import openai
from openai_model_registry import ModelRegistry

# Initialize your OpenAI client (however you normally do it)
client = openai.OpenAI(
    api_key="your-azure-api-key",
    base_url="https://your-resource.openai.azure.com/openai/deployments/your-deployment",
)


# Check if you're using Azure
def is_azure_endpoint(client):
    """Check if the OpenAI client is configured for Azure."""
    base_url = str(client.base_url) if client.base_url else ""
    return "openai.azure.com" in base_url


# Get model capabilities with Azure consideration
def get_web_search_capability(model_name, client):
    """Get accurate web search capability considering Azure limitations."""
    registry = ModelRegistry.get_default()
    capabilities = registry.get_capabilities(model_name)

    # Model supports web search, but check if endpoint allows it
    model_supports_search = capabilities.supports_web_search
    endpoint_supports_search = not is_azure_endpoint(client)

    return model_supports_search and endpoint_supports_search


# Usage
registry = ModelRegistry.get_default()
can_use_web_search = get_web_search_capability("gpt-4o", client)

if can_use_web_search:
    print("✅ You can use web search with this model and endpoint")
    # Proceed with web_search_preview tool
else:
    print("❌ Web search not available (check model support and endpoint type)")
    # Use alternative approach or skip web search
```

### 2. Alternative Approaches for Azure Users

If you need web search functionality with Azure OpenAI, consider these options:

#### Option A: Use Azure Assistants API (Preview)

Azure's newer Assistants API includes a "Browse" tool that provides web search via Bing:

```python
# Note: This requires Azure Assistants API, not standard Chat/Responses API
# The Browse tool must be enabled in Azure AI Studio

# Example Azure Assistant with Browse tool (pseudo-code)
# This is different from standard chat completions
assistant_client = AzureAssistantsClient(...)
assistant = assistant_client.create_assistant(
    model="gpt-4o",
    tools=[{"type": "browse"}],  # Azure's Browse tool, not web_search_preview
)
```

#### Option B: External Search Integration

Implement your own search integration using Bing Search API or other services:

```python
from openai_model_registry import ModelRegistry


def enhanced_azure_chat(client, model, messages, use_search=False):
    """Enhanced chat function with optional external search for Azure."""
    registry = ModelRegistry.get_default()
    capabilities = registry.get_capabilities(model)

    # Check if this is an Azure endpoint
    if is_azure_endpoint(client) and use_search:
        # Use external search API (Bing, Google, etc.)
        search_results = perform_external_search(messages[-1]["content"])

        # Enhance the prompt with search results
        enhanced_message = {
            "role": "user",
            "content": f"{messages[-1]['content']}\n\nSearch results: {search_results}",
        }
        messages = messages[:-1] + [enhanced_message]

    # Make standard chat completion call (no web_search_preview tool)
    return client.chat.completions.create(
        model=model,
        messages=messages,
        # Note: No tools parameter for Azure standard endpoints
    )
```

## Platform-Specific Capability Detection

For applications that need to work across both OpenAI direct and Azure endpoints:

```python
from openai_model_registry import ModelRegistry
from typing import Dict, Any


class PlatformAwareCapabilities:
    """Wrapper that provides platform-aware capability checking."""

    def __init__(self, client):
        self.registry = ModelRegistry.get_default()
        self.client = client
        self.is_azure = self._detect_azure()

    def _detect_azure(self) -> bool:
        """Detect if client is using Azure endpoint."""
        base_url = str(self.client.base_url) if self.client.base_url else ""
        return "openai.azure.com" in base_url

    def get_effective_capabilities(self, model_name: str) -> Dict[str, Any]:
        """Get capabilities adjusted for the current platform."""
        capabilities = self.registry.get_capabilities(model_name)

        # Create a dictionary of effective capabilities
        effective_caps = {
            "model_name": capabilities.model_name,
            "context_window": capabilities.context_window,
            "max_output_tokens": capabilities.max_output_tokens,
            "supports_structured": capabilities.supports_structured,
            "supports_streaming": capabilities.supports_streaming,
            # Adjust web search based on platform
            "supports_web_search": capabilities.supports_web_search
            and not self.is_azure,
            "platform": "azure" if self.is_azure else "openai_direct",
        }

        return effective_caps


# Usage
platform_caps = PlatformAwareCapabilities(client)
effective_capabilities = platform_caps.get_effective_capabilities("gpt-4o")

print(f"Platform: {effective_capabilities['platform']}")
print(f"Effective web search support: {effective_capabilities['supports_web_search']}")
```

## Best Practices for Azure Users

### 1. Always Check Platform Before Using Web Search

```python
# ✅ Good: Check platform first
if not is_azure_endpoint(client) and capabilities.supports_web_search:
    # Use web_search_preview tool
    tools = [{"type": "web_search_preview"}]
else:
    # Skip web search or use alternatives
    tools = []

response = client.chat.completions.create(model=model, messages=messages, tools=tools)
```

```python
# ❌ Bad: Using registry info without platform consideration
capabilities = registry.get_capabilities("gpt-4o")
if capabilities.supports_web_search:
    # This will fail on Azure standard endpoints!
    tools = [{"type": "web_search_preview"}]
```

### 2. Graceful Fallback Implementation

```python
def robust_chat_completion(client, model, messages, prefer_web_search=False):
    """Chat completion with robust handling of web search availability."""
    registry = ModelRegistry.get_default()
    capabilities = registry.get_capabilities(model)

    # Determine if web search is actually available
    web_search_available = capabilities.supports_web_search and not is_azure_endpoint(
        client
    )

    tools = []
    if prefer_web_search and web_search_available:
        tools.append({"type": "web_search_preview"})

    try:
        return client.chat.completions.create(
            model=model, messages=messages, tools=tools
        )
    except Exception as e:
        if "web_search" in str(e).lower() and tools:
            # Fallback: retry without web search
            print("Web search failed, retrying without search...")
            return client.chat.completions.create(
                model=model,
                messages=messages,
                # No tools parameter
            )
        raise  # Re-raise if it's a different error
```

### 3. Environment-Specific Configuration

```python
import os
from openai_model_registry import ModelRegistry


def get_search_strategy():
    """Get the appropriate search strategy based on environment."""
    if os.getenv("OPENAI_API_TYPE") == "azure":
        return "external_search"  # Use Bing API or other external search
    elif os.getenv("AZURE_ASSISTANTS_ENABLED") == "true":
        return "azure_browse_tool"  # Use Azure Assistants Browse tool
    else:
        return "openai_web_search"  # Use OpenAI's web_search_preview


def create_search_enabled_request(model, messages):
    """Create request with appropriate search strategy."""
    registry = ModelRegistry.get_default()
    capabilities = registry.get_capabilities(model)
    strategy = get_search_strategy()

    if not capabilities.supports_web_search:
        strategy = "no_search"

    if strategy == "openai_web_search":
        return {
            "model": model,
            "messages": messages,
            "tools": [{"type": "web_search_preview"}],
        }
    elif strategy == "external_search":
        # Enhance messages with external search results
        enhanced_messages = add_external_search_context(messages)
        return {"model": model, "messages": enhanced_messages}
    # ... handle other strategies
```

## Summary

- **The OpenAI Model Registry correctly reflects model capabilities** as defined by OpenAI
- **Azure's standard endpoints don't support `web_search_preview`** regardless of model capabilities
- **Always check your endpoint type** before attempting to use web search features
- **Consider Azure Assistants API** for web search functionality on Azure
- **Implement graceful fallbacks** for robust cross-platform applications

For the most up-to-date information on Azure OpenAI feature support, consult [Microsoft's Azure OpenAI documentation](https://docs.microsoft.com/en-us/azure/cognitive-services/openai/).
