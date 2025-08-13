"""JSON output formatter for CLI."""

import datetime as _dt
import json
import sys
from enum import Enum as _Enum
from typing import Any, Dict, List, Optional, TextIO


def _default_serializer(obj: Any) -> Any:
    """Serialize otherwise non-JSON-serializable objects.

    - datetime/date -> ISO 8601 string
    - Enum -> value (fallback to name)
    - Fallback -> str(obj)
    """
    if isinstance(obj, (_dt.datetime, _dt.date)):
        return obj.isoformat()
    if isinstance(obj, _Enum):
        return getattr(obj, "value", obj.name)
    return str(obj)


def format_json(data: Any, output: Optional[TextIO] = None, indent: int = 2) -> None:
    """Format data as JSON and write to output.

    Args:
        data: Data to format
        output: Output stream (defaults to stdout)
        indent: JSON indentation level
    """
    if output is None:
        output = sys.stdout

    json.dump(
        data,
        output,
        indent=indent,
        ensure_ascii=False,
        sort_keys=True,
        default=_default_serializer,
    )
    output.write("\n")


def format_models_list_json(models: Dict[str, Any]) -> Dict[str, Any]:
    """Format models list for JSON output.

    Args:
        models: Models data

    Returns:
        Formatted data structure
    """
    # Sort models by name for stable output
    sorted_models = [{"name": name, **model_data} for name, model_data in sorted(models.items())]
    return {"models": sorted_models, "count": len(models)}


def format_providers_json(providers: List[str], current: str) -> Dict[str, Any]:
    """Format providers data for JSON output.

    Args:
        providers: List of available providers
        current: Current active provider

    Returns:
        Formatted data structure
    """
    # Sort providers for stable output
    sorted_providers = sorted(providers)
    return {"providers": sorted_providers, "current": current, "count": len(providers)}


def format_data_paths_json(paths: Dict[str, Any]) -> Dict[str, Any]:
    """Format data paths for JSON output.

    Args:
        paths: Path information

    Returns:
        Formatted data structure
    """
    return {
        "data_sources": paths,
        "resolution_order": [
            "OMR_MODEL_REGISTRY_PATH environment variable",
            "OMR_DATA_DIR environment variable",
            "User data directory",
            "Bundled package data",
        ],
    }


def format_cache_info_json(cache_info: Dict[str, Any]) -> Dict[str, Any]:
    """Format cache information for JSON output.

    Args:
        cache_info: Cache information

    Returns:
        Formatted data structure
    """
    return {
        "cache_directory": cache_info.get("directory"),
        "files": cache_info.get("files", []),
        "total_size_bytes": cache_info.get("total_size", 0),
        "file_count": len(cache_info.get("files", [])),
    }


def format_env_vars_json(env_vars: Dict[str, Optional[str]]) -> Dict[str, Any]:
    """Format environment variables for JSON output.

    Args:
        env_vars: Environment variables

    Returns:
        Formatted data structure
    """
    return {
        "environment_variables": {key: {"value": value, "set": value is not None} for key, value in env_vars.items()},
        "set_count": sum(1 for v in env_vars.values() if v is not None),
        "total_count": len(env_vars),
    }
