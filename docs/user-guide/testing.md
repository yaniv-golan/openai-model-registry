# Testing with OpenAI Model Registry

This guide shows how to test your applications that use the OpenAI Model Registry, including working with pytest, pyfakefs, and mocking strategies.

## Overview

When testing applications that use OpenAI Model Registry, you may encounter challenges related to:

- **Filesystem interactions** - The registry reads configuration from disk
- **Singleton behavior** - The default registry instance is cached
- **Cross-platform paths** - The registry uses platform-specific directories
- **Network operations** - Registry updates fetch data from remote sources

This guide provides patterns and best practices for handling these scenarios in your tests.

## Basic Testing Patterns

### Simple Mocking

For basic tests where you just need to mock registry responses:

```python
import pytest
from unittest.mock import Mock, patch
from openai_model_registry import ModelRegistry, ModelCapabilities


def test_my_function_with_mocked_registry():
    """Test your function with a completely mocked registry."""

    # Create a mock capabilities object
    mock_capabilities = Mock(spec=ModelCapabilities)
    mock_capabilities.context_window = 4096
    mock_capabilities.max_output_tokens = 1024
    mock_capabilities.supports_streaming = True

    # Mock the registry
    mock_registry = Mock(spec=ModelRegistry)
    mock_registry.get_capabilities.return_value = mock_capabilities

    with patch(
        "openai_model_registry.ModelRegistry.get_default", return_value=mock_registry
    ):

        # Your application code here
        result = my_function_that_uses_registry("gpt-4o")

        # Verify the registry was called correctly
        mock_registry.get_capabilities.assert_called_once_with("gpt-4o")
        assert result.expected_property == expected_value
```

### Testing with Real Registry Data

If you want to test with actual registry data but control the configuration:

```python
import tempfile
from pathlib import Path
from unittest.mock import patch
from openai_model_registry import ModelRegistry, RegistryConfig


def test_my_function_with_real_registry():
    """Test with real registry using temporary configuration."""

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a custom registry configuration
        temp_registry_file = Path(temp_dir) / "models.yml"
        temp_constraints_file = Path(temp_dir) / "constraints.yml"

        # Copy or create test configuration files
        # (you can copy from the package's config directory)

        config = RegistryConfig(
            registry_path=str(temp_registry_file),
            constraints_path=str(temp_constraints_file),
        )

        registry = ModelRegistry(config)

        # Test your code with this registry
        result = my_function_that_uses_registry_instance(registry, "gpt-4o")
        assert result.is_valid
```

## Testing with pyfakefs

When your tests need to interact with the filesystem (especially when using pyfakefs), you need to handle the registry's cross-platform directory behavior.

### Case 1: Mock the Directory Functions

The cleanest approach is to mock the platformdirs functions:

```python
import pytest
from pathlib import Path
from unittest.mock import patch
from openai_model_registry import ModelRegistry


def test_my_app_with_fake_registry_paths(fs):
    """Test your app with fake filesystem paths."""

    # Set up fake directories
    fake_data_dir = Path("/fake_data/openai-model-registry")
    fake_config_dir = Path("/fake_config/openai-model-registry")

    fs.makedirs(fake_data_dir, exist_ok=True)
    fs.makedirs(fake_config_dir, exist_ok=True)

    # Create fake registry file
    fake_models_file = fake_data_dir / "models.yml"
    fs.create_file(
        fake_models_file,
        contents="""
version: "1.1.0"
dated_models:
  test-model-2024-01-01:
    context_window: 4096
    max_output_tokens: 1024
    deprecation:
      status: "active"
      reason: "test model"
aliases:
  test-model: "test-model-2024-01-01"
""",
    )

    # Mock the directory functions
    with patch(
        "openai_model_registry.config_paths.get_user_data_dir",
        return_value=fake_data_dir,
    ), patch(
        "openai_model_registry.config_paths.get_user_config_dir",
        return_value=fake_config_dir,
    ):

        # Clear any cached registry instances
        ModelRegistry.cleanup()

        # Test your application
        result = my_application_function()

        # Your assertions here
        assert result.model_used == "test-model"
```

### Case 2: Environment Variable Override

Use environment variables to redirect the registry to fake locations:

```python
import pytest
from unittest.mock import patch


def test_my_app_with_custom_registry_path(fs, monkeypatch):
    """Test using environment variable to set custom registry path."""

    # Create fake registry file
    custom_registry_path = "/custom/registry/models.yml"
    fs.create_file(
        custom_registry_path,
        contents="""
version: "1.1.0"
dated_models:
  custom-model-2024-01-01:
    context_window: 8192
    max_output_tokens: 2048
    deprecation:
      status: "active"
      reason: "custom model"
aliases:
  custom-model: "custom-model-2024-01-01"
""",
    )

    # Set environment variable
    monkeypatch.setenv("MODEL_REGISTRY_PATH", custom_registry_path)

    # Clear registry cache to pick up new environment
    ModelRegistry.cleanup()

    # Test your application
    result = my_app_function_that_uses_custom_model()
    assert "custom-model" in result.models_used
```

## Testing Registry Updates and Network Operations

When testing code that triggers registry updates:

```python
import pytest
from unittest.mock import Mock, patch
from openai_model_registry import ModelRegistry
from openai_model_registry.registry import RefreshStatus


def test_my_app_handles_registry_updates():
    """Test your app's behavior when registry updates are available."""

    with patch("requests.get") as mock_get, patch(
        "openai_model_registry.config_paths.get_user_data_dir"
    ) as mock_data_dir:

        # Mock successful update response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
version: "1.2.0"
dated_models: {}
aliases: {}
"""
        mock_get.return_value = mock_response

        # Test your application's update handling
        result = my_app_check_for_updates()

        assert result.update_available == True
        assert result.handled_correctly == True


def test_my_app_handles_network_errors():
    """Test your app's behavior when registry updates fail."""

    with patch("requests.get") as mock_get:
        # Mock network error
        mock_get.side_effect = ConnectionError("Network unavailable")

        # Test your application's error handling
        result = my_app_check_for_updates()

        assert result.update_failed == True
        assert result.fallback_used == True
```

## Testing Different Model Configurations

Test how your application handles different model scenarios:

```python
import pytest
from unittest.mock import Mock
from openai_model_registry import ModelCapabilities
from openai_model_registry.deprecation import DeprecationInfo


@pytest.fixture
def deprecated_model_capabilities():
    """Create capabilities for a deprecated model."""
    deprecation = DeprecationInfo(
        status="deprecated",
        deprecates_on=None,
        sunsets_on=None,
        replacement="gpt-4o",
        migration_guide="Use gpt-4o instead",
        reason="Model deprecated",
    )

    capabilities = Mock(spec=ModelCapabilities)
    capabilities.context_window = 8192
    capabilities.max_output_tokens = 1024
    capabilities.deprecation = deprecation
    capabilities.is_deprecated = True

    return capabilities


def test_my_app_handles_deprecated_models(deprecated_model_capabilities):
    """Test your app's handling of deprecated models."""

    with patch("openai_model_registry.ModelRegistry.get_default") as mock_registry:
        mock_registry.return_value.get_capabilities.return_value = (
            deprecated_model_capabilities
        )

        result = my_app_select_model("deprecated-model")

        # Verify your app handles deprecation appropriately
        assert result.warning_shown == True
        assert result.suggested_alternative == "gpt-4o"


@pytest.fixture
def high_capacity_model():
    """Create capabilities for a high-capacity model."""
    capabilities = Mock(spec=ModelCapabilities)
    capabilities.context_window = 1000000  # 1M tokens
    capabilities.max_output_tokens = 32768
    capabilities.supports_streaming = True
    capabilities.supports_structured = True

    return capabilities


def test_my_app_uses_high_capacity_features(high_capacity_model):
    """Test your app leverages high-capacity model features."""

    with patch("openai_model_registry.ModelRegistry.get_default") as mock_registry:
        mock_registry.return_value.get_capabilities.return_value = high_capacity_model

        result = my_app_process_large_document("huge-document.txt")

        assert result.used_streaming == True
        assert result.context_exceeded == False
```

## Best Practices

### 1. Always Clear Registry Cache

The registry uses singleton behavior, so clear the cache between tests:

```python
import pytest
from openai_model_registry import ModelRegistry


@pytest.fixture(autouse=True)
def clear_registry_cache():
    """Automatically clear registry cache before each test."""
    ModelRegistry.cleanup()
    yield
    ModelRegistry.cleanup()
```

### 2. Use Realistic Test Data

When creating fake registry data, use realistic model configurations:

```python
# Good - includes all required fields
REALISTIC_MODEL_CONFIG = """
version: "1.1.0"
dated_models:
  test-model-2024-01-01:
    context_window: 128000
    max_output_tokens: 16384
    supports_streaming: true
    supports_structured: true
    supported_parameters:
      - ref: "numeric_constraints.temperature"
      - ref: "numeric_constraints.top_p"
    deprecation:
      status: "active"
      deprecates_on: null
      sunsets_on: null
      replacement: null
      migration_guide: null
      reason: "active"
    min_version:
      year: 2024
      month: 1
      day: 1
aliases:
  test-model: "test-model-2024-01-01"
"""
```

### 3. Test Error Conditions

Test how your app handles registry errors:

```python
def test_my_app_handles_missing_models():
    """Test app behavior when requested model doesn't exist."""

    with patch("openai_model_registry.ModelRegistry.get_default") as mock_registry:
        from openai_model_registry import ModelNotSupportedError

        mock_registry.return_value.get_capabilities.side_effect = (
            ModelNotSupportedError("Model not found", model="nonexistent-model")
        )

        result = my_app_use_model("nonexistent-model")

        assert result.used_fallback_model == True
        assert result.error_logged == True
```

### 4. Test Parameter Validation Integration

If your app validates parameters using the registry:

```python
def test_my_app_validates_parameters_correctly():
    """Test that your app properly validates model parameters."""

    # Mock a model with specific parameter constraints
    mock_capabilities = Mock()
    mock_capabilities.validate_parameter.side_effect = [
        None,  # temperature=0.7 is valid
        ValueError("temperature must be between 0 and 2"),  # temperature=3.0 is invalid
    ]

    with patch("openai_model_registry.ModelRegistry.get_default") as mock_registry:
        mock_registry.return_value.get_capabilities.return_value = mock_capabilities

        # Test valid parameters
        result1 = my_app_call_openai("gpt-4o", temperature=0.7)
        assert result1.parameters_valid == True

        # Test invalid parameters
        result2 = my_app_call_openai("gpt-4o", temperature=3.0)
        assert result2.validation_error == True
        assert result2.error_message == "temperature must be between 0 and 2"
```

## Integration Testing

For integration tests that need the full registry behavior:

```python
def test_end_to_end_with_real_registry():
    """Integration test using the actual registry."""

    # Use the real registry (ensure it's properly installed)
    registry = ModelRegistry.get_default()

    # Test with a model you know exists
    try:
        capabilities = registry.get_capabilities("gpt-4o")
        result = my_complete_workflow("gpt-4o", "test prompt")

        assert result.model_used == "gpt-4o"
        assert result.context_within_limits == True

    except Exception as e:
        pytest.skip(f"Integration test skipped due to registry issue: {e}")
```

This testing approach ensures your application properly integrates with the OpenAI Model Registry while maintaining test reliability and isolation.
