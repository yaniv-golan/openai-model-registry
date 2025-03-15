#!/usr/bin/env python3
"""Example of basic registry usage."""

from openai_model_registry import ModelRegistry


def print_model_info(model_name):
    """Print information about a model.
    
    Args:
        model_name: Name of the model to look up
    """
    try:
        registry = ModelRegistry.get_instance()
        capabilities = registry.get_capabilities(model_name)
        
        print(f"Model: {model_name}")
        print(f"  Context window: {capabilities.context_window}")
        print(f"  Max output tokens: {capabilities.max_output_tokens}")
        print(f"  Supports structured output: {capabilities.supports_structured}")
        print(f"  Supports streaming: {capabilities.supports_streaming}")
        
        # Get supported parameters
        params = [ref.ref.split(".")[1] for ref in capabilities.supported_parameters]
        print(f"  Supported parameters: {', '.join(sorted(params))}")
        
        # Print aliases if any
        if capabilities.aliases:
            print(f"  Aliases: {', '.join(sorted(capabilities.aliases))}")
            
        print()
    except Exception as e:
        print(f"Error getting information for {model_name}: {e}")


def main():
    """Run the example."""
    # Print information for basic models
    models_to_check = ["gpt-4o", "gpt-4o-mini", "o1"]
    
    for model in models_to_check:
        print_model_info(model)
    
    # Demonstrate parameter validation
    registry = ModelRegistry.get_instance()
    gpt4o = registry.get_capabilities("gpt-4o")
    
    print("Parameter validation examples:")
    try:
        # Valid parameter
        gpt4o.validate_parameter("temperature", 0.7)
        print("  ✅ temperature=0.7 is valid")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    try:
        # Invalid parameter
        gpt4o.validate_parameter("temperature", 3.0)
        print("  ✓ temperature=3.0 is valid")
    except Exception as e:
        print(f"  ❌ temperature=3.0 - {e}")
    
    # O1 model has different parameters
    o1 = registry.get_capabilities("o1")
    
    try:
        # Valid parameter for O1
        o1.validate_parameter("reasoning_effort", "medium")
        print("  ✅ reasoning_effort=medium is valid for O1")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    try:
        # Not supported on O1
        o1.validate_parameter("temperature", 0.7)
        print("  ✓ temperature is valid for O1")
    except Exception as e:
        print(f"  ❌ temperature - {e}")


if __name__ == "__main__":
    main() 