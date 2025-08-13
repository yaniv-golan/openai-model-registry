#!/usr/bin/env python3
"""Convert data YAML files to unified pricing schema and normalize capabilities.

This script updates:
 - data/models.yaml
 - data/overrides.yaml

Unified pricing schema fields:
   pricing:
     scheme: per_token|per_minute|per_image|per_request
     unit: million_tokens|minute|image|request
     input_cost_per_unit: float
     output_cost_per_unit: float
     currency: USD

Normalization of capabilities:
 Adds missing boolean keys with defaults False for:
  - supports_vision, supports_streaming, supports_function_calling,
    supports_structured_output, supports_json_mode, supports_web_search,
    supports_audio
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = ROOT / "data" / "models.yaml"
OVERRIDES_PATH = ROOT / "data" / "overrides.yaml"
CHECKSUMS_PATH = ROOT / "data" / "checksums.txt"


DEFAULT_CAP_KEYS = [
    "supports_vision",
    "supports_streaming",
    "supports_function_calling",
    "supports_structured_output",
    "supports_json_mode",
    "supports_web_search",
    "supports_audio",
]


def load_yaml(path: Path) -> Dict[str, Any]:
    """Load YAML mapping from a file path.

    Raises:
        ValueError: if the root is not a mapping.
    """
    with path.open("r", encoding="utf-8") as f:
        data: Any = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping at {path}, got {type(data).__name__}")
    return cast(Dict[str, Any], data)


def dump_yaml(data: Dict[str, Any], path: Path) -> None:
    """Write mapping to YAML with stable ordering."""
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def convert_pricing_block(pricing: Dict[str, Any], model_name: str) -> Dict[str, Any]:
    """Convert legacy pricing fields to unified pricing schema for a model."""
    # Detect existing unified fields
    if isinstance(pricing, dict) and {"scheme", "unit"}.issubset(pricing.keys()):
        # Already unified; ensure field names
        pricing.setdefault("input_cost_per_unit", pricing.pop("input_cost_per_million_tokens", 0.0))
        pricing.setdefault("output_cost_per_unit", pricing.pop("output_cost_per_million_tokens", 0.0))
        pricing.setdefault("currency", pricing.get("currency", "USD"))
        return pricing

    # Legacy → unified
    input_cost = float(pricing.get("input_cost_per_million_tokens", 0.0))
    output_cost = float(pricing.get("output_cost_per_million_tokens", 0.0))
    currency = str(pricing.get("currency", "USD"))

    # Heuristics for non-token models
    name = model_name.lower()
    if "whisper" in name:
        scheme, unit = "per_minute", "minute"
    elif "dall-e" in name or "dalle" in name:
        scheme, unit = "per_image", "image"
    elif name.startswith("tts-") or "tts" in name:
        scheme, unit = "per_request", "request"
    else:
        scheme, unit = "per_token", "million_tokens"

    return {
        "scheme": scheme,
        "unit": unit,
        "input_cost_per_unit": input_cost,
        "output_cost_per_unit": output_cost,
        "currency": currency,
    }


def normalize_capabilities(cap: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure capability booleans exist with default False values."""
    if not isinstance(cap, dict):
        cap = {}
    for key in DEFAULT_CAP_KEYS:
        cap.setdefault(key, False)
    return cap


def update_models() -> None:
    """Update data/models.yaml pricing fields and capabilities normalization."""
    data = load_yaml(MODELS_PATH)
    models = data.get("models", {})
    for model_name, model in models.items():
        # pricing
        if "pricing" in model:
            model["pricing"] = convert_pricing_block(model["pricing"], model_name)
        # capabilities
        model["capabilities"] = normalize_capabilities(model.get("capabilities", {}))
    data["models"] = models
    dump_yaml(data, MODELS_PATH)


def update_overrides() -> None:
    """Update data/overrides.yaml pricing fields to unified schema."""
    if not OVERRIDES_PATH.exists():
        return
    data = load_yaml(OVERRIDES_PATH)
    overrides = data.get("overrides", {})
    for provider, provider_overrides in overrides.items():
        models = provider_overrides.get("models", {})
        for model_name, model in models.items():
            if "pricing" in model:
                model["pricing"] = convert_pricing_block(model["pricing"], model_name)
        provider_overrides["models"] = models
        overrides[provider] = provider_overrides
    data["overrides"] = overrides
    dump_yaml(data, OVERRIDES_PATH)


def recompute_checksums() -> None:
    """Recompute SHA256 checksums for data files and write checksums.txt."""
    import hashlib

    def sha256(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    lines = []
    for fname in ["models.yaml", "overrides.yaml"]:
        fpath = ROOT / "data" / fname
        if fpath.exists():
            lines.append(f"{sha256(fpath)} {fname}")
    CHECKSUMS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Run conversion and checksum recompute pipeline."""
    update_models()
    update_overrides()
    recompute_checksums()
    print("Conversion complete.")


if __name__ == "__main__":
    main()
