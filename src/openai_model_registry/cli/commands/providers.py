"""Provider management commands for the OMR CLI."""

import sys

import click

from ...registry import ModelRegistry
from ..formatters import (
    create_console,
    format_json,
    format_providers_json,
    format_providers_table,
)
from ..utils import ExitCode, handle_error


@click.group()
def providers() -> None:
    """Manage and inspect providers."""
    pass


@providers.command()
@click.pass_context
def list(ctx: click.Context) -> None:
    """List all available providers."""
    try:
        registry = ModelRegistry.get_default()
        available_providers = registry.list_providers()
        current_provider = ctx.obj["provider"]

        # If the user explicitly provided --format, honor it.
        # Otherwise: force table when sys.stdout.isatty() is True (tests patch this);
        # fall back to JSON when not TTY.
        if ctx.obj.get("format_explicit"):
            format_type = ctx.obj["format"].lower()
        else:
            try:
                is_tty = bool(sys.stdout.isatty())
            except Exception:
                is_tty = False
            if is_tty:
                format_type = "table"
            else:
                format_type = "json"

        if format_type == "json":
            formatted_data = format_providers_json(available_providers, current_provider)
            format_json(formatted_data)
        elif format_type == "table":
            # Table format
            console = create_console(no_color=ctx.obj["no_color"])
            format_providers_table(available_providers, current_provider, console)
        else:
            # Only json and table are supported here; anything else is invalid usage
            handle_error(
                click.BadParameter(
                    f"Format '{format_type}' is not supported for providers list. Use 'table' or 'json'."
                ),
                ExitCode.INVALID_USAGE,
            )

    except Exception as e:
        handle_error(e, ExitCode.GENERIC_ERROR)


@providers.command()
@click.pass_context
def current(ctx: click.Context) -> None:
    """Show the currently active provider and its source."""
    try:
        current_provider = ctx.obj["provider"]

        # Get the tracked provider source information from context
        source = ctx.obj.get("provider_source", "Unknown")
        source_value = ctx.obj.get("provider_source_value", current_provider)

        format_type = ctx.obj["format"]

        if format_type == "json":
            provider_info = {
                "current_provider": current_provider,
                "source": source,
                "source_value": source_value,
                "precedence_order": [
                    "CLI flag (--provider)",
                    "Environment variable (OMR_PROVIDER)",
                    "Default (openai)",
                ],
            }
            format_json(provider_info)
        else:
            # Table/human readable format
            console = create_console(no_color=ctx.obj["no_color"])

            console.print(f"[bold]Current Provider:[/bold] {current_provider}")
            console.print(f"[bold]Source:[/bold] {source}")
            console.print(f"[bold]Value:[/bold] {source_value}")

            console.print("\n[bold]Provider Resolution Precedence:[/bold]")
            console.print("  1. CLI flag (--provider)")
            console.print("  2. Environment variable (OMR_PROVIDER)")
            console.print("  3. Default (openai)")

    except Exception as e:
        handle_error(e, ExitCode.GENERIC_ERROR)
