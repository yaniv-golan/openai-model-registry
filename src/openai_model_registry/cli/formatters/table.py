"""Rich table formatter for CLI output."""

import sys
from typing import Any, Dict, List, Optional, TextIO

from rich.console import Console
from rich.table import Table
from rich.text import Text


def create_console(output: Optional[TextIO] = None, no_color: bool = False) -> Console:
    """Create a Rich console instance.

    Args:
        output: Output stream (defaults to stdout)
        no_color: Disable color output

    Returns:
        Console instance
    """
    if output is None:
        output = sys.stdout

    # Let Rich use the actual terminal width to avoid truncating headers
    return Console(file=output, no_color=no_color)


def _extract_nested_value(obj: Dict[str, Any], path: str) -> Any:
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


def _format_column_value(value: Any, column_name: str) -> str:
    """Format a column value for display in table.

    Args:
        value: The value to format
        column_name: Name of the column (for special formatting)

    Returns:
        Formatted string value
    """
    if value is None:
        return "N/A"

    # Special formatting for certain column types
    if "pricing.input_cost_per_unit" == column_name and isinstance(value, (int, float)):
        return f"${value}"
    if "pricing.output_cost_per_unit" == column_name and isinstance(value, (int, float)):
        return f"${value}"
    # Human-friendly formatting for context window sizes in table only
    if column_name in ("context_window.total", "context_window.output", "context_window.input") and isinstance(
        value, (int, float)
    ):
        tokens = int(value)
        # Represent in thousands (K) and millions (M) of tokens for readability
        if tokens >= 1_000_000:
            return f"{tokens/1_000_000:.1f}M"
        if tokens >= 1_000:
            return f"{tokens/1_000:.0f}K"
        return str(tokens)
    elif isinstance(value, bool):
        return "✓" if value else "✗"
    else:
        return str(value)


def _get_column_display_name(column_path: str) -> str:
    """Convert column path to display name.

    Args:
        column_path: Dotted path like 'pricing.input_cost_per_million_tokens'

    Returns:
        Human-readable column name
    """
    # Map common paths to readable names
    name_map = {
        "name": "Model",
        "context_window.total": "Context\nWindow",
        "context_window.output": "Max\nOutput",
        "context_window.input": "Input\nWindow",
        "pricing.input_cost_per_unit": "Input\nCost",
        "pricing.output_cost_per_unit": "Output\nCost",
        "pricing.unit": "Unit",
        "supports_vision": "Vision",
        "supports_function_calling": "Function\nCalling",
        "supports_streaming": "Streaming",
        "supports_structured_output": "Structured\nOutput",
        "supports_json_mode": "JSON\nMode",
        "supports_web_search": "Web\nSearch",
        "supports_audio": "Audio",
        "modalities": "Modalities",
        "provider": "Provider",
    }

    if column_path in name_map:
        return name_map[column_path]

    # Convert path to title case
    parts = column_path.split(".")
    return " ".join(part.replace("_", " ").title() for part in parts)


def format_models_table(
    models: Dict[str, Any], console: Optional[Console] = None, columns: Optional[List[str]] = None
) -> None:
    """Format models as a Rich table.

    Args:
        models: Models data
        console: Rich console (will create if None)
        columns: Custom columns to display (dotted paths)
    """
    if console is None:
        console = create_console()

    table = Table(title="OpenAI Models", show_header=True, header_style="bold magenta")

    # Define default columns if none specified
    if columns is None:
        columns = [
            "name",
            "context_window.total",
            "context_window.output",
            "context_window.input",
            "pricing.input_cost_per_unit",
            "pricing.output_cost_per_unit",
            "pricing.unit",
            "supports_vision",
            "supports_function_calling",
            "supports_streaming",
            "supports_structured_output",
            "supports_json_mode",
            "supports_web_search",
            "supports_audio",
        ]

    # Helper to compute minimal width from a multi-line header
    def _min_width_from_header(header: str) -> int:
        lines = header.split("\n")
        return max(len(line) for line in lines) if lines else len(header)

    # Add columns to table
    for column_path in columns:
        display_name = _get_column_display_name(column_path)

        # Set column styling based on content type
        if column_path == "name":
            table.add_column(display_name, style="cyan", no_wrap=True)
        elif "cost" in column_path.lower() or "window" in column_path.lower() or "output" in column_path.lower():
            table.add_column(
                display_name,
                justify="right",
                no_wrap=True,
                min_width=_min_width_from_header(display_name),
            )
        elif "supports_" in column_path or column_path in ["vision", "function_calling", "streaming"]:
            table.add_column(
                display_name,
                justify="center",
                no_wrap=True,
                min_width=_min_width_from_header(display_name),
            )
        else:
            table.add_column(
                display_name,
                no_wrap=True,
                min_width=_min_width_from_header(display_name),
            )

    # Add data rows
    for name, model_data in models.items():
        row = []
        for column_path in columns:
            if column_path == "name":
                value = name
            else:
                value = _extract_nested_value(model_data, column_path)

            formatted_value = _format_column_value(value, column_path)
            row.append(formatted_value)

        table.add_row(*row)

    console.print(table)


def format_providers_table(providers: List[str], current: str, console: Optional[Console] = None) -> None:
    """Format providers as a Rich table.

    Args:
        providers: List of available providers
        current: Current active provider
        console: Rich console (will create if None)
    """
    if console is None:
        console = create_console()

    table = Table(title="Available Providers", show_header=True, header_style="bold magenta")

    table.add_column("Provider", style="cyan")
    table.add_column("Status", justify="center")

    for provider in providers:
        status = "✓ Active" if provider == current else ""
        style = "bold green" if provider == current else ""
        table.add_row(provider, status, style=style)

    console.print(table)


def format_data_paths_table(paths: Dict[str, Any], console: Optional[Console] = None) -> None:
    """Format data paths as a Rich table.

    Args:
        paths: Path information
        console: Rich console (will create if None)
    """
    if console is None:
        console = create_console()

    table = Table(title="Data Source Paths", show_header=True, header_style="bold magenta")

    table.add_column("File", style="cyan")
    table.add_column("Source", style="yellow")
    table.add_column("Path", style="dim")
    table.add_column("Status", justify="center")
    table.add_column("Checksum", justify="center")
    table.add_column("Modified", style="dim")

    for file_type, path_info in paths.items():
        if isinstance(path_info, dict):
            path = path_info.get("path", "N/A")
            source = path_info.get("source", "Unknown")
            exists = path_info.get("exists", False)
            checksum_verified = path_info.get("checksum_verified")
            last_modified = path_info.get("last_modified", "N/A")
        else:
            path = str(path_info) if path_info else "Bundled"
            source = "User Data" if path_info else "Bundled"
            exists = path_info is not None
            checksum_verified = None
            last_modified = "N/A"

        # Status column
        status = "✓" if exists else "✗"
        status_style = "green" if exists else "red"

        # Checksum column
        if checksum_verified is True:
            checksum = "✓"
            checksum_style = "green"
        elif checksum_verified is False:
            checksum = "✗"
            checksum_style = "red"
        else:
            checksum = "N/A"
            checksum_style = "dim"

        table.add_row(
            file_type,
            source,
            path,
            Text(status, style=status_style),
            Text(checksum, style=checksum_style),
            last_modified,
        )

    console.print(table)


def format_cache_info_table(cache_info: Dict[str, Any], console: Optional[Console] = None) -> None:
    """Format cache information as a Rich table.

    Args:
        cache_info: Cache information
        console: Rich console (will create if None)
    """
    if console is None:
        console = create_console()

    # Summary info
    console.print(f"[bold]Cache Directory:[/bold] {cache_info.get('directory', 'N/A')}")
    console.print(f"[bold]Total Files:[/bold] {len(cache_info.get('files', []))}")
    console.print()

    # Files table
    files = cache_info.get("files", [])
    if files:
        table = Table(title="Cache Files", show_header=True, header_style="bold magenta")

        table.add_column("File", style="cyan")
        table.add_column("Size", justify="right")
        table.add_column("Modified", style="dim")
        table.add_column("ETag", style="dim")

        for file_info in files:
            etag = file_info.get("etag")
            etag_display = etag[:12] + "..." if etag and len(etag) > 15 else (etag or "N/A")

            table.add_row(
                file_info.get("name", "Unknown"),
                file_info.get("size_formatted", "N/A"),
                file_info.get("modified", "N/A"),
                etag_display,
            )

        console.print(table)
    else:
        console.print("[dim]No cache files found[/dim]")


def format_env_vars_table(env_vars: Dict[str, Optional[str]], console: Optional[Console] = None) -> None:
    """Format environment variables as a Rich table.

    Args:
        env_vars: Environment variables
        console: Rich console (will create if None)
    """
    if console is None:
        console = create_console()

    table = Table(title="OMR Environment Variables", show_header=True, header_style="bold magenta")

    table.add_column("Variable", style="cyan")
    table.add_column("Value", style="yellow")
    table.add_column("Set", justify="center")

    for key, value in sorted(env_vars.items()):
        is_set = value is not None
        display_value = value if is_set else "[dim]<not set>[/dim]"
        status = "✓" if is_set else "✗"
        status_style = "green" if is_set else "red"

        table.add_row(key, display_value, Text(status, style=status_style))

    console.print(table)
