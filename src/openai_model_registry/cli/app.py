"""Main CLI application for OpenAI Model Registry."""

import os
from typing import Optional

import click
import rich_click as rich_click

# Make ModelRegistry available at module scope so tests can patch it
try:  # pragma: no cover - import for test patching convenience
    from ..registry import ModelRegistry as ModelRegistry  # noqa: F401
except Exception:  # pragma: no cover
    ModelRegistry = None  # type: ignore

# Expose ModelRegistry at module scope for tests monkeypatching
from .utils import (
    ExitCode,
    handle_error,
    resolve_format,
    resolve_provider,
    validate_provider,
)

# Configure rich-click
rich_click.rich_click.USE_RICH_MARKUP = True
rich_click.rich_click.USE_MARKDOWN = True
rich_click.rich_click.SHOW_ARGUMENTS = True
rich_click.rich_click.GROUP_ARGUMENTS_OPTIONS = True


def _show_json_help(ctx: click.Context) -> None:
    """Show comprehensive JSON help and exit."""
    # Get dynamic provider choices
    try:
        from ..registry import ModelRegistry

        registry = ModelRegistry.get_default()
        provider_choices = sorted(registry.list_providers())
    except Exception:
        # Fallback to basic providers if registry unavailable
        provider_choices = ["openai", "azure"]

    # Get dynamic CLI version
    try:
        from .. import __version__

        cli_version = __version__
    except ImportError:
        cli_version = "1.0.0"  # Fallback

    help_data = {
        "command": "omr",
        "description": "OpenAI Model Registry CLI - inspect and debug model registry data",
        "usage": "omr [OPTIONS] COMMAND [ARGS]...",
        "version": cli_version,
        "global_options": [
            {
                "name": "--provider",
                "type": "choice",
                "choices": provider_choices,
                "help": "Override active provider (openai, azure, etc.). Takes precedence over OMR_PROVIDER environment variable.",
                "required": False,
            },
            {
                "name": "--format",
                "type": "choice",
                "choices": ["table", "json", "csv", "yaml"],
                "help": "Output format. Defaults to 'table' for TTY, 'json' for non-TTY.",
                "required": False,
            },
            {
                "name": "--verbose",
                "short": "-v",
                "type": "count",
                "help": "Increase verbosity (can be used multiple times).",
                "required": False,
            },
            {
                "name": "--quiet",
                "short": "-q",
                "type": "count",
                "help": "Decrease verbosity (can be used multiple times).",
                "required": False,
            },
            {"name": "--debug", "type": "flag", "help": "Enable debug-level logging.", "required": False},
            {"name": "--no-color", "type": "flag", "help": "Disable color output.", "required": False},
            {
                "name": "--version",
                "type": "flag",
                "help": "Print CLI and library version information.",
                "required": False,
            },
            {
                "name": "--help-json",
                "type": "flag",
                "help": "Show help in JSON format for programmatic use.",
                "required": False,
            },
        ],
        "commands": {
            "data": {
                "description": "Data source inspection and dumping",
                "subcommands": {
                    "paths": {"description": "Show resolved data source paths and precedence", "options": []},
                    "env": {"description": "Show effective OMR environment variables", "options": []},
                    "dump": {
                        "description": "Dump registry data in various formats",
                        "options": [
                            {
                                "name": "--raw",
                                "type": "flag",
                                "help": "Dump original on-disk/bundled YAML (no provider merge)",
                            },
                            {
                                "name": "--effective",
                                "type": "flag",
                                "help": "Dump fully merged, provider-adjusted dataset",
                            },
                            {
                                "name": "--output",
                                "short": "-o",
                                "type": "path",
                                "help": "Write output to file instead of stdout",
                            },
                        ],
                    },
                },
            },
            "update": {
                "description": "Update registry data from remote sources",
                "subcommands": {
                    "check": {
                        "description": "Check for available updates",
                        "options": [{"name": "--url", "type": "string", "help": "Override update URL"}],
                    },
                    "apply": {
                        "description": "Apply available updates",
                        "options": [
                            {
                                "name": "--force",
                                "type": "flag",
                                "help": "Force update even if current version is newer",
                            },
                            {"name": "--url", "type": "string", "help": "Override update URL"},
                        ],
                    },
                    "refresh": {
                        "description": "Refresh data from remote with validation",
                        "options": [
                            {"name": "--url", "type": "string", "help": "Override update URL"},
                            {
                                "name": "--validate-only",
                                "type": "flag",
                                "help": "Only validate remote data without applying updates",
                            },
                            {
                                "name": "--force",
                                "type": "flag",
                                "help": "Force refresh even if current version is newer",
                            },
                        ],
                    },
                    "show-config": {"description": "Show effective update-related configuration", "options": []},
                },
            },
            "models": {
                "description": "Model listing and inspection",
                "subcommands": {
                    "list": {
                        "description": "List all available models",
                        "options": [
                            {"name": "--filter", "type": "string", "help": "Filter models using simple expression"},
                            {"name": "--columns", "type": "string", "help": "Comma-separated columns to display"},
                        ],
                    },
                    "get": {
                        "description": "Get detailed information about a specific model",
                        "arguments": [
                            {
                                "name": "model_name",
                                "type": "string",
                                "help": "Name of the model to inspect",
                                "required": True,
                            }
                        ],
                        "options": [
                            {
                                "name": "--effective",
                                "type": "flag",
                                "help": "Show effective model data (with provider overrides) - default",
                            },
                            {
                                "name": "--raw",
                                "type": "flag",
                                "help": "Show raw model data (without provider overrides)",
                            },
                            {
                                "name": "--parameters-only",
                                "type": "flag",
                                "help": "Show only the model's parameters block",
                            },
                            {
                                "name": "--output",
                                "short": "-o",
                                "type": "path",
                                "help": "Write output to file instead of stdout",
                            },
                        ],
                    },
                },
            },
            "providers": {
                "description": "Provider management and inspection",
                "subcommands": {
                    "list": {"description": "List available providers", "options": []},
                    "current": {"description": "Show current active provider and its source", "options": []},
                },
            },
            "cache": {
                "description": "Cache management operations",
                "subcommands": {
                    "info": {"description": "Show cache information and file details", "options": []},
                    "clear": {
                        "description": "Clear cached registry data files",
                        "options": [
                            {
                                "name": "--yes",
                                "type": "flag",
                                "help": "Confirm deletion without prompting (required for non-interactive use)",
                            }
                        ],
                    },
                },
            },
        },
        "exit_codes": {
            "0": "Success",
            "1": "Generic error",
            "2": "Invalid usage",
            "3": "Model not found",
            "4": "Data source missing/corrupt",
            "10": "Update available (for 'update check')",
        },
        "environment_variables": [
            "OMR_PROVIDER",
            "OMR_DATA_DIR",
            "OMR_DISABLE_DATA_UPDATES",
            "OMR_DATA_VERSION_PIN",
            "OMR_MODEL_REGISTRY_PATH",
            "OMR_PARAMETER_CONSTRAINTS_PATH",
        ],
    }

    import json

    click.echo(json.dumps(help_data, indent=2, sort_keys=True))
    ctx.exit()


@click.group()
@click.option(
    "--provider",
    type=str,
    help="Override active provider (openai, azure, etc.). Takes precedence over OMR_PROVIDER environment variable.",
)
@click.option(
    "--format",
    type=click.Choice(["table", "json", "csv", "yaml"], case_sensitive=False),
    help="Output format. Defaults to 'table' for TTY, 'json' for non-TTY.",
)
@click.option("--verbose", "-v", count=True, help="Increase verbosity (can be used multiple times).")
@click.option("--quiet", "-q", count=True, help="Decrease verbosity (can be used multiple times).")
@click.option("--debug", is_flag=True, help="Enable debug-level logging.")
@click.option("--no-color", is_flag=True, help="Disable color output.")
@click.option("--version", is_flag=True, is_eager=True, help="Print CLI and library version information.")
@click.option(
    "--help-json",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=lambda ctx, param, value: _show_json_help(ctx) if value else None,
    help="Show help in JSON format for programmatic use.",
)
@click.pass_context
def app(
    ctx: click.Context,
    provider: Optional[str] = None,
    format: Optional[str] = None,
    verbose: int = 0,
    quiet: int = 0,
    debug: bool = False,
    no_color: bool = False,
    version: bool = False,
) -> None:
    """OpenAI Model Registry CLI - inspect and debug model registry data.

    The OMR CLI provides tools to inspect data sources, list models, manage cache,
    and debug provider configurations. It uses only public APIs and respects
    environment variable configuration.

    Examples:
      # List all models for OpenAI provider
      omr models list --provider openai

      # Show data source paths
      omr data paths

      # Check for updates
      omr update check

      # Clear cache
      omr cache clear --yes
    """
    if version:
        try:
            from .. import __version__

            library_version = __version__
        except ImportError:
            library_version = "unknown"

        # Get dynamic CLI version (same as library version)
        cli_version = library_version if library_version != "unknown" else "1.0.0"

        click.echo(f"OMR CLI version: {cli_version}")
        click.echo(f"Library version: {library_version}")
        return

    # Store global options in context for subcommands
    ctx.ensure_object(dict)

    # Resolve provider with precedence: CLI > env > default and track source
    provider_source = "default"
    provider_source_value = "openai"

    if provider:
        try:
            provider = validate_provider(provider)
            provider_source = "CLI flag (--provider)"
            provider_source_value = provider
        except click.BadParameter as e:
            handle_error(e, ExitCode.INVALID_USAGE)
    else:
        # Check if environment variable is set
        env_provider = os.getenv("OMR_PROVIDER")
        if env_provider:
            provider_source = "Environment variable (OMR_PROVIDER)"
            provider_source_value = env_provider

    resolved_provider = resolve_provider(provider)
    resolved_format = resolve_format(format)

    # Configure logging level based on verbosity
    log_level = "WARNING"
    if debug:
        log_level = "DEBUG"
    elif verbose > quiet:
        if verbose >= 2:
            log_level = "DEBUG"
        elif verbose >= 1:
            log_level = "INFO"
    elif quiet > verbose:
        if quiet >= 2:
            log_level = "ERROR"
        elif quiet >= 1:
            log_level = "WARNING"

    # Set environment variable for provider if specified
    if provider:
        os.environ["OMR_PROVIDER"] = resolved_provider
    else:
        # Validate provider from CLI if provided, otherwise ensure env/default is valid
        try:
            _ = validate_provider(resolved_provider)
        except click.BadParameter as e:
            handle_error(e, ExitCode.INVALID_USAGE)

    ctx.obj.update(
        {
            "provider": resolved_provider,
            "provider_source": provider_source,
            "provider_source_value": provider_source_value,
            "format": resolved_format,
            "format_explicit": format is not None,
            "verbose": verbose,
            "quiet": quiet,
            "debug": debug,
            "no_color": no_color,
            "log_level": log_level,
        }
    )


# Import and register subcommands (at module top is preferred, but we place
# here after context is built to avoid circular import issues in runtime.)
from .commands import cache, data, models, providers, update  # noqa: E402

app.add_command(data.data)
app.add_command(update.update)
app.add_command(models.models)
app.add_command(providers.providers)
app.add_command(cache.cache)

# Expose ModelRegistry on the Click group for tests that patch
# openai_model_registry.cli.app.ModelRegistry
app.ModelRegistry = ModelRegistry  # type: ignore[attr-defined]


if __name__ == "__main__":
    app()
