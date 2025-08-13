"""Helper functions for CLI operations."""

import os
import sys
from typing import Any, Dict, List, Optional

import click


class ExitCode:
    """Standard exit codes for the CLI."""

    SUCCESS = 0
    GENERIC_ERROR = 1
    INVALID_USAGE = 2
    MODEL_NOT_FOUND = 3
    DATA_SOURCE_ERROR = 4
    UPDATE_AVAILABLE = 10  # CI-friendly code for update check


def resolve_provider(cli_provider: Optional[str] = None) -> str:
    """Resolve provider using precedence: CLI flag > OMR_PROVIDER env > default 'openai'.

    Args:
        cli_provider: Provider specified via CLI flag

    Returns:
        Resolved provider name
    """
    if cli_provider:
        return cli_provider.lower()

    env_provider = os.getenv("OMR_PROVIDER")
    if env_provider:
        return env_provider.lower()

    return "openai"


def resolve_format(cli_format: Optional[str] = None, default_tty: str = "table", default_non_tty: str = "json") -> str:
    """Resolve output format with TTY detection.

    Args:
        cli_format: Format specified via CLI flag
        default_tty: Default format for TTY output
        default_non_tty: Default format for non-TTY output

    Returns:
        Resolved format name
    """
    if cli_format:
        return cli_format.lower()

    # Auto-detect based on TTY
    if sys.stdout.isatty():
        return default_tty
    else:
        return default_non_tty


def handle_error(error: Exception, exit_code: int = ExitCode.GENERIC_ERROR) -> None:
    """Handle CLI errors with consistent formatting.

    Args:
        error: Exception to handle
        exit_code: Exit code to use
    """
    click.echo(f"Error: {str(error)}", err=True)
    sys.exit(exit_code)


def get_omr_env_vars() -> Dict[str, Optional[str]]:
    """Get all OMR_* environment variables.

    Returns:
        Dictionary of OMR environment variables and their values
    """
    omr_vars: Dict[str, Optional[str]] = {}
    for key, value in os.environ.items():
        if key.startswith("OMR_"):
            omr_vars[key] = value

    # Include commonly used variables even if not set
    common_vars: List[str] = [
        "OMR_PROVIDER",
        "OMR_DATA_DIR",
        "OMR_DISABLE_DATA_UPDATES",
        "OMR_DATA_VERSION_PIN",
        "OMR_MODEL_REGISTRY_PATH",
        "OMR_PARAMETER_CONSTRAINTS_PATH",
    ]

    for var in common_vars:
        if var not in omr_vars:
            omr_vars[var] = None

    return omr_vars


def validate_provider(provider: str) -> str:
    """Validate and normalize provider name.

    Args:
        provider: Provider name to validate

    Returns:
        Normalized provider name

    Raises:
        click.BadParameter: If provider is invalid
    """
    provider_lower = provider.lower()

    # Try to get valid providers dynamically from registry
    try:
        from ...registry import ModelRegistry

        registry = ModelRegistry.get_default()
        valid_providers = registry.list_providers()

        if valid_providers and provider_lower in [p.lower() for p in valid_providers]:
            return provider_lower
    except Exception:
        # Fallback to static validation if registry is not available
        pass

    # Fallback to basic known providers + extensible validation
    basic_providers = ["openai", "azure"]
    if provider_lower in basic_providers:
        return provider_lower

    # If none of the above matched, it's invalid
    raise click.BadParameter(f"Invalid provider '{provider}'. Must be one of: {', '.join(basic_providers)}")


def validate_format_support(
    format_type: str,
    supported_formats: List[str],
    command_name: str,
    ctx_obj: Dict[str, Any],
) -> str:
    """Validate format support for a command with consistent fallback behavior.

    Args:
        format_type: The requested format
        supported_formats: List of supported formats for this command
        command_name: Name of the command for error messages
        ctx_obj: Click context object containing verbosity settings

    Returns:
        The validated format (may be changed from input for fallback)

    Raises:
        click.BadParameter: For unsupported formats that can't fall back
    """
    if format_type in supported_formats:
        return format_type

    # Common fallback behavior for table/csv
    if format_type in ["table", "csv"]:
        fallback_format = "json" if "json" in supported_formats else supported_formats[0]
        # Only show message in verbose mode to avoid cluttering output
        if ctx_obj.get("verbose", 0) > 0:
            click.echo(
                f"Note: {command_name} doesn't support '{format_type}' format, using {fallback_format} instead.",
                err=True,
            )
        return fallback_format
    else:
        # For other unsupported formats, show clear error
        supported_list = "', '".join(supported_formats)
        raise click.BadParameter(f"Format '{format_type}' is not supported for {command_name}. Use '{supported_list}'.")


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB"]
    i: int = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes = int(size_bytes / 1024.0) if i < len(size_names) - 1 else size_bytes
        i += 1

    return f"{float(size_bytes):.1f} {size_names[i]}"
