"""Tests for pricing field presence and schema normalization."""

import os
from pathlib import Path
from typing import Generator

import pytest
import yaml

from openai_model_registry.pricing import PricingInfo
from openai_model_registry.registry import ModelRegistry, RegistryConfig


@pytest.fixture()
def registry_with_pricing(
    tmp_path: Path,
) -> Generator[ModelRegistry, None, None]:
    """Create a registry instance backed by a config that includes pricing."""
    # Build temporary config dir
    config_dir = tmp_path / "cfg"
    config_dir.mkdir()

    # Parameter constraints (minimal – only one numeric constraint)
    constraints_path = config_dir / "parameter_constraints.yml"
    constraints_path.write_text(
        yaml.dump(
            {
                "numeric_constraints": {
                    "temperature": {
                        "type": "numeric",
                        "min_value": 0.0,
                        "max_value": 2.0,
                        "allow_float": True,
                        "allow_int": False,
                    }
                }
            }
        )
    )

    # Models config with pricing / modalities
    models_path = config_dir / "models.yaml"
    models_path.write_text(
        yaml.dump(
            {
                "version": "1.0.0",
                "models": {
                    "gpt-test": {
                        "context_window": 10000,
                        "max_output_tokens": 2048,
                        "capabilities": {
                            "supports_audio": True,
                            "supports_json_mode": True,
                        },
                        "pricing": {
                            "scheme": "per_token",
                            "unit": "million_tokens",
                            "input_cost_per_unit": 1.23,
                            "output_cost_per_unit": 4.56,
                            "currency": "USD",
                        },
                        "input_modalities": ["text", "audio"],
                        "parameters": {
                            "temperature": {
                                "type": "numeric",
                                "min": 0.0,
                                "max": 2.0,
                                "default": 1.0,
                                "allow_float": True,
                            }
                        },
                    }
                },
            }
        )
    )

    # Point environment variables at these files
    orig_registry_path = os.environ.get("OMR_MODEL_REGISTRY_PATH")
    orig_constraints_path = os.environ.get("OMR_PARAMETER_CONSTRAINTS_PATH")

    os.environ["OMR_MODEL_REGISTRY_PATH"] = str(models_path)
    os.environ["OMR_PARAMETER_CONSTRAINTS_PATH"] = str(constraints_path)

    try:
        registry = ModelRegistry(
            RegistryConfig(
                registry_path=str(models_path),
                constraints_path=str(constraints_path),
            )
        )
        yield registry
    finally:
        # Restore env
        if orig_registry_path is not None:
            os.environ["OMR_MODEL_REGISTRY_PATH"] = orig_registry_path
        else:
            os.environ.pop("OMR_MODEL_REGISTRY_PATH", None)

        if orig_constraints_path is not None:
            os.environ["OMR_PARAMETER_CONSTRAINTS_PATH"] = orig_constraints_path
        else:
            os.environ.pop("OMR_PARAMETER_CONSTRAINTS_PATH", None)

        ModelRegistry._default_instance = None


def test_pricing_and_modalities(registry_with_pricing: ModelRegistry) -> None:
    """Verify new fields (pricing, modalities, audio/JSON flags) are parsed."""
    caps = registry_with_pricing.get_capabilities("gpt-test")

    # Pricing assertions
    assert isinstance(caps.pricing, PricingInfo)
    assert caps.pricing.scheme == "per_token"
    assert caps.pricing.unit == "million_tokens"
    assert caps.pricing.input_cost_per_unit == 1.23
    assert caps.pricing.output_cost_per_unit == 4.56

    # Capability flags
    assert caps.supports_audio is True
    assert caps.supports_json_mode is True

    # Modalities list (input only)
    assert set(getattr(caps, "input_modalities", [])) == {"text", "audio"}

    # Parameter validation still works with new schema
    caps.validate_parameter("temperature", 0.5)
