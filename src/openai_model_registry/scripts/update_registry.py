#!/usr/bin/env python3
"""Command line utility for refreshing the model registry from remote source."""

import sys
from typing import Optional, Union

import click

from ..errors import ModelNotSupportedError, ModelVersionError
from ..registry import ModelRegistry, RefreshStatus


def refresh_registry(
    verbose: bool = False,
    force: bool = False,
    url: Union[str, None] = None,
    validate: bool = False,
    check_only: bool = False,
) -> int:
    """Refresh the model registry from remote source.

    Args:
        verbose: Whether to print verbose output
        force: Skip confirmation prompt
        url: Custom config URL
        validate: Validate without updating
        check_only: Only check for updates without downloading

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    try:
        registry = ModelRegistry.get_instance()

        if validate:
            registry._load_capabilities()  # Force revalidation
            print("✅ Config validation successful")
            if verbose:
                print(
                    f"\nLocal registry file: {registry.config.registry_path}"
                )
            return 0

        if check_only:
            result = registry.check_for_updates(url)
            if result.success:
                if result.status == RefreshStatus.UPDATE_AVAILABLE:
                    print("✅ Registry update is available")
                    if verbose:
                        print(f"\nStatus: {result.status.value}")
                        print(f"Message: {result.message}")
                elif result.status == RefreshStatus.ALREADY_CURRENT:
                    print("✓ Registry is already up to date")
                    if verbose:
                        print(f"\nStatus: {result.status.value}")
                        print(f"Message: {result.message}")
                return 0
            else:
                print(f"❌ Error checking for updates: {result.message}")
                return 1

        # For actual update (when not in validate or check_only mode)
        result = registry.check_for_updates(url)
        if not force and result.status == RefreshStatus.ALREADY_CURRENT:
            print("✓ Registry is already up to date")
            if verbose:
                print(f"\nStatus: {result.status.value}")
                print(f"Message: {result.message}")
            return 0

        # Perform the update
        result = registry.refresh_from_remote(
            url=url, force=force, validate_only=validate
        )
        if result.success:
            print("✅ Registry updated successfully")
            if verbose:
                print(f"\nStatus: {result.status.value}")
                print(f"Message: {result.message}")
            return 0
        else:
            print(f"❌ Error updating registry: {result.message}")
            return 1

    except ModelNotSupportedError as e:
        print(f"❌ Invalid model: {e}")
        return 1
    except ModelVersionError as e:
        print(f"❌ Config error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error refreshing model registry: {e}")
        return 1


@click.command()
@click.option("-v", "--verbose", is_flag=True, help="Show verbose output")
@click.option("-f", "--force", is_flag=True, help="Skip confirmation prompt")
@click.option("--url", help="Custom config URL")
@click.option("--validate", is_flag=True, help="Validate without updating")
@click.option(
    "--check", is_flag=True, help="Check for updates without downloading"
)
def main(
    verbose: bool = False,
    force: bool = False,
    url: Optional[str] = None,
    validate: bool = False,
    check: bool = False,
) -> int:
    """Update model registry from remote source.

    This command updates the local model registry configuration from a remote
    source. By default, it fetches the configuration from the official repository.

    The command will:
    1. Download the latest model configuration
    2. Validate the configuration format and values
    3. Update the local configuration file

    Examples:
        # Basic update with confirmation
        $ openai-model-registry-update

        # Update with verbose output
        $ openai-model-registry-update -v

        # Update from custom URL without confirmation
        $ openai-model-registry-update -f --url https://example.com/models.yml

        # Validate current configuration without updating
        $ openai-model-registry-update --validate

        # Check for updates without downloading
        $ openai-model-registry-update --check
    """
    return refresh_registry(
        verbose=verbose,
        force=force,
        url=url,
        validate=validate,
        check_only=check,
    )


if __name__ == "__main__":
    sys.exit(main())
