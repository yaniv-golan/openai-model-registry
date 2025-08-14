"""Update management commands for the OMR CLI."""

from typing import Optional

import click

from ...registry import ModelRegistry
from ..formatters import create_console, format_json
from ..utils import ExitCode, handle_error


@click.group()
def update() -> None:
    """Manage registry data updates.

    Keep your model registry data current with the latest OpenAI models,
    capabilities, and pricing information from GitHub releases.
    """
    pass


@update.command()
@click.option("--url", type=str, help="Override update URL.")
@click.pass_context
def check(ctx: click.Context, url: Optional[str] = None) -> None:
    """Check if newer model data is available without downloading.

    Shows current and latest versions. Useful for CI/CD pipelines
    to detect when updates are needed.

    Exit codes:
      0: Registry is up to date
     10: Update available (CI-friendly)
    """
    try:
        registry = ModelRegistry.get_default()

        # Check for updates
        refresh_result = registry.check_for_updates(url)
        update_info = registry.get_update_info()

        format_type = ctx.obj["format"]

        if format_type == "json":
            result_data = {
                "update_available": not refresh_result.success or refresh_result.status.value != "up_to_date",
                "current_version": update_info.current_version,
                "latest_version": update_info.latest_version,
                "message": refresh_result.message,
                "status": refresh_result.status.value
                if hasattr(refresh_result.status, "value")
                else str(refresh_result.status),
            }
            format_json(result_data)
        else:
            # Table/human readable format
            console = create_console(no_color=ctx.obj["no_color"])

            if (
                refresh_result.success
                and hasattr(refresh_result.status, "value")
                and refresh_result.status.value == "up_to_date"
            ):
                console.print("✅ [green]Registry is up to date[/green]")
                console.print(f"Current version: {update_info.current_version or 'bundled'}")
            else:
                console.print("🔄 [yellow]Update available[/yellow]")
                console.print(f"Current version: {update_info.current_version or 'bundled'}")
                console.print(f"Latest version: {update_info.latest_version}")
                if refresh_result.message:
                    console.print(f"Details: {refresh_result.message}")

        # Exit with appropriate code for CI
        if (
            refresh_result.success
            and hasattr(refresh_result.status, "value")
            and refresh_result.status.value == "up_to_date"
        ):
            exit(ExitCode.SUCCESS)
        else:
            exit(ExitCode.UPDATE_AVAILABLE)

    except Exception as e:
        handle_error(e, ExitCode.GENERIC_ERROR)


@update.command()
@click.option("--force", is_flag=True, help="Force update even if current version is newer.")
@click.option("--url", type=str, help="Override update URL.")
@click.pass_context
def apply(ctx: click.Context, force: bool = False, url: Optional[str] = None) -> None:
    """Download and install available updates.

    Only downloads if an update is actually available (unless --force is used).
    Use 'omr update check' first to see what updates are available.

    This command only applies updates - it doesn't check or validate first.
    For a complete check-and-update workflow, use 'omr update refresh' instead.
    """
    try:
        registry = ModelRegistry.get_default()

        # Get version info before update
        update_info = registry.get_update_info()
        current_version_before = update_info.current_version

        if url:
            # Use refresh_from_remote for URL override
            # This method automatically reloads the registry after successful update
            result = registry.refresh_from_remote(url=url, force=force)
            success = result.success
            message = result.message
        else:
            # Use update_data for standard updates
            # This method automatically reloads the registry after successful update
            success = registry.update_data(force=force)
            message = "Update completed successfully" if success else "Update failed"

        # Get version info after update
        update_info_after = registry.get_update_info()
        current_version_after = update_info_after.current_version

        format_type = ctx.obj["format"]

        if format_type == "json":
            result_data = {
                "success": success,
                "message": message,
                "version_before": current_version_before,
                "version_after": current_version_after,
            }
            format_json(result_data)
        else:
            console = create_console(no_color=ctx.obj["no_color"])
            if success:
                console.print("✅ [green]Update applied successfully[/green]")
                if current_version_before != current_version_after:
                    console.print(
                        f"Updated from: {current_version_before or 'bundled'} → {current_version_after or 'bundled'}"
                    )
                else:
                    console.print(f"Version: {current_version_after or 'bundled'} (already up to date)")
                # Show message without "Message:" prefix if it's not generic
                if message and message not in ["Update completed successfully", "Update failed"]:
                    console.print(message)
            else:
                console.print("❌ [red]Update failed[/red]")
                console.print(f"Version: {current_version_before or 'bundled'} (unchanged)")
                # Show error message without "Error:" prefix if it's meaningful
                if message and message != "Update failed":
                    console.print(message)

        exit(ExitCode.SUCCESS if success else ExitCode.GENERIC_ERROR)

    except Exception as e:
        handle_error(e, ExitCode.GENERIC_ERROR)


@update.command()
@click.option("--url", type=str, help="Override update URL.")
@click.option("--validate-only", is_flag=True, help="Only validate remote data without applying updates.")
@click.option("--force", is_flag=True, help="Force refresh even if current version is newer.")
@click.pass_context
def refresh(
    ctx: click.Context,
    url: Optional[str] = None,
    validate_only: bool = False,
    force: bool = False,
) -> None:
    """Complete update workflow: check, validate, and apply in one command.

    This is the recommended way to update your registry. It automatically:
    1. Checks for available updates
    2. Validates the remote data integrity
    3. Downloads and applies updates if available

    Use --validate-only to test remote data without downloading.
    This is the most convenient command for regular updates.
    """
    try:
        registry = ModelRegistry.get_default()

        # Get version info before update
        update_info = registry.get_update_info()
        current_version_before = update_info.current_version

        result = registry.refresh_from_remote(url=url, force=force, validate_only=validate_only)

        # Get version info after update (only if not validate_only)
        if not validate_only:
            update_info_after = registry.get_update_info()
            current_version_after = update_info_after.current_version
        else:
            current_version_after = current_version_before

        format_type = ctx.obj["format"]

        if format_type == "json":
            result_data = {
                "success": result.success,
                "status": result.status.value if hasattr(result.status, "value") else str(result.status),
                "message": result.message,
                "validate_only": validate_only,
                "version_before": current_version_before,
                "version_after": current_version_after,
            }
            format_json(result_data)
        else:
            console = create_console(no_color=ctx.obj["no_color"])

            action = "Validation" if validate_only else "Refresh"
            if result.success:
                console.print(f"✅ [green]{action} completed successfully[/green]")
            else:
                console.print(f"❌ [red]{action} failed[/red]")

            # Show version information with friendly status
            if not validate_only and current_version_before != current_version_after:
                console.print(
                    f"Updated from: {current_version_before or 'bundled'} → {current_version_after or 'bundled'}"
                )
            else:
                # Show friendly status instead of enum
                status_str = result.status.value if hasattr(result.status, "value") else str(result.status)
                if status_str == "already_current":
                    version_suffix = " (already up to date)"
                elif status_str == "updated":
                    version_suffix = " (updated)"
                else:
                    version_suffix = f" ({status_str.replace('_', ' ')})"

                console.print(f"Version: {current_version_before or 'bundled'}{version_suffix}")

            # Show message without "Message:" prefix
            if result.message:
                console.print(result.message)

        exit(ExitCode.SUCCESS if result.success else ExitCode.GENERIC_ERROR)

    except Exception as e:
        handle_error(e, ExitCode.GENERIC_ERROR)


@update.command("show-config")
@click.pass_context
def show_config(ctx: click.Context) -> None:
    """Show current update configuration and environment settings.

    Displays data sources, update policies, version pinning, and
    other settings that affect how updates work.
    """
    try:
        registry = ModelRegistry.get_default()
        data_info = registry.get_data_info()

        # Get environment variables related to updates
        import os

        update_config: dict[str, object] = {
            "data_directory": data_info.get("user_data_dir") if isinstance(data_info, dict) else "N/A",
            "environment_variables": {
                "OMR_DISABLE_DATA_UPDATES": os.getenv("OMR_DISABLE_DATA_UPDATES"),
                "OMR_DATA_VERSION_PIN": os.getenv("OMR_DATA_VERSION_PIN"),
                "OMR_DATA_DIR": os.getenv("OMR_DATA_DIR"),
                "OMR_MODEL_REGISTRY_PATH": os.getenv("OMR_MODEL_REGISTRY_PATH"),
            },
            "update_settings": {
                "updates_disabled": os.getenv("OMR_DISABLE_DATA_UPDATES") == "true",
                "version_pinned": os.getenv("OMR_DATA_VERSION_PIN") is not None,
                "custom_data_dir": os.getenv("OMR_DATA_DIR") is not None,
                "custom_registry_path": os.getenv("OMR_MODEL_REGISTRY_PATH") is not None,
            },
        }

        format_type = ctx.obj["format"]

        if format_type == "json":
            format_json(update_config)
        else:
            console = create_console(no_color=ctx.obj["no_color"])

            console.print("[bold]Update Configuration[/bold]")
            console.print(f"Data Directory: {update_config['data_directory']}")
            console.print()

            console.print("[bold]Environment Variables:[/bold]")
            env_vars = update_config.get("environment_variables")
            if isinstance(env_vars, dict):
                for key, value in env_vars.items():
                    status = value if value else "[dim]<not set>[/dim]"
                    console.print(f"  {key}: {status}")

            console.print()
            console.print("[bold]Settings:[/bold]")
            settings = update_config.get("update_settings")
            if isinstance(settings, dict):
                console.print(f"  Updates Disabled: {'✓' if settings.get('updates_disabled') else '✗'}")
                console.print(f"  Version Pinned: {'✓' if settings.get('version_pinned') else '✗'}")
                console.print(f"  Custom Data Dir: {'✓' if settings.get('custom_data_dir') else '✗'}")
                console.print(f"  Custom Registry Path: {'✓' if settings.get('custom_registry_path') else '✗'}")

    except Exception as e:
        handle_error(e, ExitCode.GENERIC_ERROR)
