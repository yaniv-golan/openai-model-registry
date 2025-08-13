"""Model inspection commands for the OMR CLI."""

import sys
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional, TextIO

import click

from ...registry import ModelRegistry
from ..formatters import (
    create_console,
    format_json,
    format_models_list_json,
    format_models_table,
)
from ..utils import ExitCode, handle_error, validate_format_support


def _collect_available_columns() -> List[str]:
    """Dynamically collect available column dotted paths from effective data.

    Returns:
        Sorted list of dotted paths that users may pass to --columns.
    """
    try:
        registry = ModelRegistry.get_default()
        effective = registry.dump_effective().get("models", {})
        if not effective:
            # Fallback to a sensible default set when no models are loaded
            return [
                "name",
                "context_window.total",
                "context_window.input",
                "context_window.output",
                "pricing.input_cost_per_unit",
                "pricing.output_cost_per_unit",
                "pricing.unit",
                "supports_vision",
                "supports_function_calling",
                "supports_streaming",
                "provider",
            ]

        paths: set[str] = set(["name"])  # name is always supported
        # Inspect a sample of models to collect keys
        for model_data in list(effective.values())[:50]:
            if isinstance(model_data, dict):
                for key, value in model_data.items():
                    if isinstance(value, dict):
                        for sub_key in value.keys():
                            paths.add(f"{key}.{sub_key}")
                            # Capture third-level keys (e.g., billing.web_search.call_fee_per_1000)
                            if isinstance(value.get(sub_key), dict):
                                for sub2_key in value[sub_key].keys():
                                    paths.add(f"{key}.{sub_key}.{sub2_key}")
                    else:
                        paths.add(str(key))
        # Users usually want these canonical names regardless of internal names
        paths.add("supports_function_calling")
        return sorted(paths)
    except Exception:
        # Defensive fallback
        return [
            "name",
            "context_window.total",
            "context_window.input",
            "context_window.output",
            "pricing.input_cost_per_unit",
            "pricing.output_cost_per_unit",
            "pricing.unit",
            "supports_vision",
            "supports_function_calling",
            "supports_streaming",
            "provider",
        ]


_COLUMNS_HELP_DYNAMIC = "Comma-separated columns to display (dotted paths). Available: " + ", ".join(
    _collect_available_columns()
)


def extract_nested_value(obj: Dict[str, Any], path: str) -> Any:
    """Extract nested value using dotted path notation.

    Args:
        obj: Object to extract from
        path: Dotted path (e.g., 'pricing.input_cost_per_unit')

    Returns:
        Extracted value or None if path doesn't exist
    """
    try:
        current = obj
        for part in path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current
    except (KeyError, TypeError):
        return None


def filter_models(models: Dict[str, Any], filter_expr: str) -> Dict[str, Any]:
    """Apply filtering to models with support for structured queries.

    Args:
        models: Models data
        filter_expr: Filter expression - supports:
                    - Simple string matching: "gpt-4"
                    - Field comparison: "supports_vision:true", "pricing.input_cost_per_unit:>2.0"
                    - Multiple conditions with AND: "supports_vision:true AND context_window.total:>100000"

    Returns:
        Filtered models data
    """
    filtered = {}

    # Parse filter expression for structured queries
    conditions = []
    import re

    # Split on AND (case insensitive) using regex
    and_pattern = r"\s+AND\s+"
    if re.search(and_pattern, filter_expr, re.IGNORECASE):
        parts = [part.strip() for part in re.split(and_pattern, filter_expr, flags=re.IGNORECASE) if part.strip()]
        conditions = parts
    else:
        conditions = [filter_expr.strip()]

    for name, model_data in models.items():
        # Check if all conditions match
        matches_all = True

        for condition in conditions:
            if not _matches_condition(name, model_data, condition):
                matches_all = False
                break

        if matches_all:
            filtered[name] = model_data

    return filtered


def _matches_condition(model_name: str, model_data: Dict[str, Any], condition: str) -> bool:
    """Check if a single condition matches a model.

    Args:
        model_name: Name of the model
        model_data: Model data dictionary
        condition: Single condition to check

    Returns:
        True if condition matches, False otherwise
    """
    condition = condition.strip()

    # Check for field:value patterns
    if ":" in condition:
        field, value = condition.split(":", 1)
        field = field.strip()
        value = value.strip()

        # Handle comparison operators
        if value.startswith(">="):
            return _compare_numeric(model_name, model_data, field, float(value[2:]), ">=")
        elif value.startswith("<="):
            return _compare_numeric(model_name, model_data, field, float(value[2:]), "<=")
        elif value.startswith(">"):
            return _compare_numeric(model_name, model_data, field, float(value[1:]), ">")
        elif value.startswith("<"):
            return _compare_numeric(model_name, model_data, field, float(value[1:]), "<")
        elif value.startswith("="):
            value = value[1:]  # Remove = prefix

        # Handle special field "name"
        if field.lower() == "name":
            if value.lower() == "true" or value.lower() == "false":
                return False  # Name can't be boolean
            return value.lower() in model_name.lower()

        # Extract field value using dotted notation
        field_value = extract_nested_value(model_data, field)

        # Handle boolean comparisons
        if value.lower() in ["true", "false"]:
            expected_bool = value.lower() == "true"
            return bool(field_value) == expected_bool

        # Handle string comparisons
        if isinstance(field_value, str):
            return value.lower() in field_value.lower()

        # Handle exact matches for other types
        return str(field_value) == value

    else:
        # Simple string search in model name or any string values
        return _simple_string_match(model_name, model_data, condition)


def _compare_numeric(
    model_name: str, model_data: Dict[str, Any], field: str, target_value: float, operator: str
) -> bool:
    """Compare numeric field values.

    Args:
        model_name: Name of the model
        model_data: Model data dictionary
        field: Field path to compare
        target_value: Target numeric value
        operator: Comparison operator (>, <, >=, <=)

    Returns:
        True if comparison matches, False otherwise
    """
    try:
        if field.lower() == "name":
            return False  # Can't do numeric comparison on name

        field_value = extract_nested_value(model_data, field)
        if field_value is None:
            return False

        numeric_value = float(field_value)

        if operator == ">":
            return numeric_value > target_value
        elif operator == "<":
            return numeric_value < target_value
        elif operator == ">=":
            return numeric_value >= target_value
        elif operator == "<=":
            return numeric_value <= target_value

        return False
    except (ValueError, TypeError):
        return False


def _simple_string_match(model_name: str, model_data: Dict[str, Any], search_term: str) -> bool:
    """Perform simple string matching against model name and data.

    Args:
        model_name: Name of the model
        model_data: Model data dictionary
        search_term: Term to search for

    Returns:
        True if search term found, False otherwise
    """
    # Check model name first
    if search_term.lower() in model_name.lower():
        return True

    # Check string values in model data
    def check_values(obj: Any, term: str) -> bool:
        if isinstance(obj, str):
            return term.lower() in obj.lower()
        elif isinstance(obj, dict):
            return any(check_values(v, term) for v in obj.values())
        elif hasattr(obj, "__iter__") and not isinstance(obj, str):
            # Handle lists and other iterables (but not strings)
            try:
                return any(check_values(item, term) for item in obj)
            except TypeError:
                return False
        return False

    return check_values(model_data, search_term)


@click.group()
def models() -> None:
    """Inspect and list models."""
    pass


@models.command()
@click.option("--filter", type=str, help="Filter models using simple expression.")
@click.option("--columns", type=str, help=_COLUMNS_HELP_DYNAMIC)
@click.pass_context
def list(
    ctx: click.Context,
    filter: Optional[str] = None,
    columns: Optional[str] = None,
) -> None:
    """List all available models with their capabilities."""
    try:
        registry = ModelRegistry.get_default()

        # Get effective models data
        effective_data = registry.dump_effective()
        models_data = effective_data.get("models", {})

        # Apply filtering if specified
        if filter:
            models_data = filter_models(models_data, filter)

        format_type = ctx.obj["format"]

        if format_type == "json":
            formatted_data = format_models_list_json(models_data)
            format_json(formatted_data)
        elif format_type == "csv":
            # CSV output
            import csv
            import io

            output = io.StringIO()

            # Determine columns
            if columns:
                column_list = [col.strip() for col in columns.split(",")]
            else:
                column_list = [
                    "name",
                    "context_window.total",
                    "context_window.output",
                    "pricing.input_cost_per_unit",
                    "pricing.output_cost_per_unit",
                    "pricing.unit",
                    "supports_vision",
                    "supports_function_calling",
                ]

            writer = csv.writer(output)
            writer.writerow(column_list)

            for name, model_data in models_data.items():
                row = []
                for col in column_list:
                    if col == "name":
                        row.append(name)
                    else:
                        value = extract_nested_value(model_data, col)
                        row.append(str(value) if value is not None else "N/A")
                writer.writerow(row)

            click.echo(output.getvalue().strip())
        else:
            # Table format
            console = create_console(no_color=ctx.obj["no_color"])

            # Determine columns for table format
            if columns:
                column_list = [col.strip() for col in columns.split(",")]
            else:
                column_list = None  # Use default columns

            format_models_table(models_data, console, columns=column_list)

    except Exception as e:
        handle_error(e, ExitCode.GENERIC_ERROR)


@models.command()
@click.argument("model_name", type=str)
@click.option("--effective", is_flag=True, help="Show effective model data (with provider overrides) - default.")
@click.option("--raw", is_flag=True, help="Show raw model data (without provider overrides).")
@click.option("--parameters-only", is_flag=True, help="Show only the model's parameters block.")
@click.option("--output", "-o", type=click.Path(), help="Write output to file instead of stdout.")
@click.pass_context
def get(
    ctx: click.Context,
    model_name: str,
    effective: bool = False,
    raw: bool = False,
    parameters_only: bool = False,
    output: Optional[str] = None,
) -> None:
    """Get detailed information about a specific model."""
    try:
        registry = ModelRegistry.get_default()

        # Default to effective if neither specified
        if not raw and not effective:
            effective = True

        # Prepare output
        output_file: Optional[TextIO] = None
        if output:
            output_file = open(output, "w")

        try:
            if effective:
                # Get effective model capabilities
                try:
                    # Pre-check existence using effective data if available (skip when parameters-only)
                    if not parameters_only:
                        try:
                            effective_data = registry.dump_effective().get("models", {})
                            if model_name not in effective_data:
                                handle_error(
                                    Exception(f"Model '{model_name}' not found"),
                                    ExitCode.MODEL_NOT_FOUND,
                                )
                                return
                        except Exception:
                            pass

                    capabilities = registry.get_capabilities(model_name)
                    wb = getattr(capabilities, "web_search_billing", None)
                    if wb is not None and is_dataclass(wb):
                        billing_block = {"web_search": asdict(wb)}
                    elif isinstance(wb, dict):
                        billing_block = {"web_search": wb}
                    else:
                        billing_block = None
                    model_data = {
                        "name": model_name,
                        "context_window": {
                            "total": capabilities.context_window,
                            "input": getattr(capabilities, "input_context_window", None),
                            "output": capabilities.max_output_tokens,
                        },
                        "pricing": {
                            "scheme": getattr(capabilities.pricing, "scheme", "per_token"),
                            "unit": getattr(capabilities.pricing, "unit", "million_tokens"),
                            "input_cost_per_unit": getattr(capabilities.pricing, "input_cost_per_unit", 0.0),
                            "output_cost_per_unit": getattr(capabilities.pricing, "output_cost_per_unit", 0.0),
                            "tiers": getattr(capabilities.pricing, "tiers", None),
                        },
                        "supports_vision": capabilities.supports_vision,
                        "supports_function_calling": getattr(
                            capabilities,
                            "supports_function_calling",
                            getattr(capabilities, "supports_functions", False),
                        ),
                        "supports_streaming": capabilities.supports_streaming,
                        "billing": billing_block,
                        "provider": ctx.obj["provider"],
                        "parameters": getattr(capabilities, "inline_parameters", {}),
                        "metadata": {"source": "effective", "provider_applied": ctx.obj["provider"]},
                    }
                except Exception:
                    handle_error(Exception(f"Model '{model_name}' not found"), ExitCode.MODEL_NOT_FOUND)
                    return
            else:
                # Get raw model data without provider overrides
                model_data_opt: Dict[str, Any] | None = registry.get_raw_model_data(model_name)

                if model_data_opt is None:
                    handle_error(Exception(f"Model '{model_name}' not found"), ExitCode.MODEL_NOT_FOUND)
                    return
                model_data = model_data_opt

            # Output the data in requested format
            format_type = ctx.obj["format"]

            # Validate format support for models get
            try:
                format_type = validate_format_support(format_type, ["json", "yaml"], "models get", ctx.obj)
            except click.BadParameter as e:
                handle_error(e, ExitCode.INVALID_USAGE)

            # Reduce payload to only parameters if requested
            payload: Dict[str, Any]
            if parameters_only:
                if effective:
                    payload = getattr(capabilities, "inline_parameters", {}) or {}
                else:
                    payload = {}
                    if isinstance(model_data, dict):
                        payload = model_data.get("parameters", {}) or {}
            else:
                payload = model_data

            if format_type == "yaml":
                import yaml

                yaml_output = yaml.dump(payload, default_flow_style=False, sort_keys=True)
                if output_file:
                    output_file.write(yaml_output)
                else:
                    click.echo(yaml_output.rstrip())
            else:  # json format (default)
                format_json(payload, output_file or sys.stdout)

        finally:
            if output_file:
                output_file.close()

    except Exception as e:
        handle_error(e, ExitCode.GENERIC_ERROR)
