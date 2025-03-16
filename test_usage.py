#!/usr/bin/env python3
"""Test script for validating registry usage."""


from openai_model_registry import ModelRegistry


def main() -> None:
    """Run basic registry usage tests."""
    # Get registry instance
    registry = ModelRegistry.get_instance()

    # Get available models
    print(f"Available models: {sorted(registry.models.keys())}")

    # Test model capabilities
    model = "gpt-4o"
    caps = registry.get_capabilities(model)
    print(f"\nModel: {model}")
    print(f"  Context window: {caps.context_window}")
    print(f"  Max tokens: {caps.max_output_tokens}")
    print(f"  Supports structured: {caps.supports_structured}")
    print(f"  Supports streaming: {caps.supports_streaming}")

    # Test parameter validation
    params_to_test = {
        "temperature": 0.7,
        "top_p": 0.9,
        "max_completion_tokens": 500,
    }

    print("\nParameter validation:")
    for param_name, value in params_to_test.items():
        try:
            caps.validate_parameter(param_name, value)
            print(f"  ✅ {param_name}={value} - Validation successful")
        except Exception as e:
            print(f"  ❌ {param_name}={value} - Validation error: {e}")

    # Test invalid parameter
    try:
        caps.validate_parameter("temperature", 3.0)
        print("  ❌ temperature=3.0 - Should have failed but passed")
    except Exception as e:
        print(f"  ✅ temperature=3.0 - Correctly failed with: {e}")

    # Test O1 model parameter validation
    try:
        o1_caps = registry.get_capabilities("o1")
        print("\nModel: o1")
        print(f"  Context window: {o1_caps.context_window}")
        print(f"  Max tokens: {o1_caps.max_output_tokens}")

        # Test reasoning effort parameter
        o1_caps.validate_parameter("reasoning_effort", "medium")
        print("  ✅ reasoning_effort=medium - Validation successful")

        try:
            o1_caps.validate_parameter("reasoning_effort", "invalid")
            print("  ❌ reasoning_effort=invalid - Should have failed but passed")
        except Exception as e:
            print(f"  ✅ reasoning_effort=invalid - Correctly failed with: {e}")

    except Exception as e:
        print(f"  ❌ O1 model test failed: {e}")

if __name__ == "__main__":
    main()
