#!/usr/bin/env python
"""Example of integrating OpenAI Model Registry into a CLI application."""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

import click
from click import Context

from openai_model_registry import ModelRegistry
from openai_model_registry.errors import (
    ModelNotSupportedError,
    ModelRegistryError,
    ModelVersionError,
    TokenParameterError,
)

# Constants for update checks
UPDATE_CHECK_INTERVAL_DAYS = 7  # How often to check for updates
LAST_CHECK_FILE = Path.home() / ".myapp" / "last_update_check"


class CLIError(Exception):
    """Custom error for CLI operation failures."""

    pass


def get_update_notification(quiet: bool = False) -> Optional[str]:
    """
    Check if registry updates are available and return notification message if needed.

    This implements a non-intrusive check for updates that runs only
    once every UPDATE_CHECK_INTERVAL_DAYS.
    """
    if quiet:
        return None

    # Check if it's time for an update check
    should_check = False

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(LAST_CHECK_FILE), exist_ok=True)

    # Check when we last ran an update check
    try:
        if not LAST_CHECK_FILE.exists():
            should_check = True
        else:
            last_check_time = datetime.fromtimestamp(
                LAST_CHECK_FILE.stat().st_mtime
            )
            check_interval = timedelta(days=UPDATE_CHECK_INTERVAL_DAYS)
            should_check = datetime.now() - last_check_time > check_interval
    except Exception:
        # If we can't check for updates, just continue without checking
        return None

    if not should_check:
        return None

    try:
        # Update the last check timestamp
        LAST_CHECK_FILE.touch()

        # Check if updates are available
        registry = ModelRegistry.get_instance()
        result = registry.check_for_updates()

        if result.status.name == "UPDATE_AVAILABLE":
            return (
                "Model registry updates are available. Run 'myapp update-registry' "
                "to get the latest model information."
            )
    except Exception:
        # If we can't check for updates, just continue without checking
        pass

    return None


def validate_model_parameters(model: str, params: Dict[str, Any]) -> None:
    """Validate that model parameters are supported by the model."""
    try:
        registry = ModelRegistry.get_instance()
        capabilities = registry.get_capabilities(model)

        # Validates parameters against model capabilities
        for param_name, value in params.items():
            capabilities.validate_parameter(param_name, value)

        # Enforce token limits
        max_tokens = params.get("max_tokens")
        max_output_tokens = params.get("max_output_tokens")

        if max_tokens and max_tokens > capabilities.context_window:
            raise CLIError(
                f"max_tokens ({max_tokens}) exceeds model context window "
                f"({capabilities.context_window})"
            )

        if (
            max_output_tokens
            and max_output_tokens > capabilities.max_output_tokens
        ):
            raise CLIError(
                f"max_output_tokens ({max_output_tokens}) exceeds model's maximum "
                f"({capabilities.max_output_tokens})"
            )

    except ModelNotSupportedError as e:
        raise CLIError(f"Unknown model: {model}") from e
    except ModelVersionError as e:
        raise CLIError(str(e)) from e
    except TokenParameterError as e:
        raise CLIError(f"Invalid parameter: {str(e)}") from e
    except ModelRegistryError as e:
        raise CLIError(f"Error validating model parameters: {str(e)}") from e
    except Exception as e:
        raise CLIError(f"Error validating model parameters: {str(e)}") from e


@click.group()
@click.version_option()
@click.option("--quiet", is_flag=True, help="Suppress non-essential output")
@click.pass_context
def cli(ctx: Context, quiet: bool) -> None:
    """A sample CLI application using OpenAI Model Registry."""
    ctx.ensure_object(dict)
    ctx.obj["quiet"] = quiet

    # Show update notification if available
    update_msg = get_update_notification(quiet=quiet)
    if update_msg:
        click.echo(update_msg, err=True)


@cli.command("update-registry")
@click.option(
    "--url",
    help="URL to fetch registry updates from",
    default=None,
)
@click.option(
    "--force",
    is_flag=True,
    help="Force update even if registry is current",
)
@click.option(
    "--auto-confirm",
    "-y",
    is_flag=True,
    help="Automatically confirm update without prompting",
)
@click.pass_context
def update_registry_command(
    ctx: Context, url: Optional[str], force: bool, auto_confirm: bool
) -> None:
    """Update the model registry with the latest model information."""
    quiet = ctx.obj.get("quiet", False)

    try:
        registry = ModelRegistry.get_instance()

        # Check if updates are available
        if not force:
            result = registry.check_for_updates(url=url)
            if result.status.name == "ALREADY_CURRENT":
                click.echo("Model registry is already up-to-date.")
                return

            if not auto_confirm:
                if not click.confirm(
                    "Updates are available. Do you want to update now?"
                ):
                    click.echo("Update cancelled.")
                    return

        # Perform the update
        result = registry.refresh_from_remote(url=url, force=force)

        if not quiet:
            if result.success:
                click.echo("Model registry updated successfully.")
            else:
                click.echo(f"Update failed: {result.message}")
    except Exception as e:
        raise CLIError(f"Failed to update model registry: {str(e)}") from e


@cli.command("completion")
@click.option("--model", required=True, help="OpenAI model to use")
@click.option("--prompt", required=True, help="Text prompt")
@click.option(
    "--temperature", type=float, default=0.7, help="Sampling temperature"
)
@click.option("--max-tokens", type=int, help="Maximum tokens to generate")
@click.pass_context
def completion_command(
    ctx: Context,
    model: str,
    prompt: str,
    temperature: float,
    max_tokens: Optional[int],
) -> None:
    """Generate text completions using the specified model."""
    # Build parameters
    params = {
        "temperature": temperature,
    }

    if max_tokens is not None:
        params["max_tokens"] = max_tokens

    # Validate model and parameters
    try:
        validate_model_parameters(model, params)
    except CLIError as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

    # In a real application, you would now call the OpenAI API
    # with the validated model and parameters
    click.echo(f"Using model: {model}")
    click.echo(f"Parameters: {params}")
    click.echo(f"Prompt: {prompt}")
    click.echo("(This example doesn't actually call the OpenAI API)")


def main() -> None:
    """Run the CLI application."""
    try:
        cli()
    except CLIError as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
