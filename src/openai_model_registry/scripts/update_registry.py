#!/usr/bin/env python3
"""Command line utility for refreshing the model registry from remote source."""

import sys
from typing import Optional, Union

import click

from ..errors import ModelNotSupportedError, ModelVersionError
from ..registry import ModelRegistry, RegistryUpdateStatus


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
                print(f"\nLocal registry file: {registry._config_path}")
            return 0

        if check_only:
            result = registry.check_for_updates(url)
            if result.success:
                if result.status == RegistryUpdateStatus.UPDATE_AVAILABLE:
                    print("✅ Registry update is available")
                    if verbose:
                        print(f"\nStatus: {result.status.value}")
                        print(f"Message: {result.message}")
                        if result.url:
                            print(f"URL: {result.url}")
                        print(f"Local registry file: {registry._config_path}")
                elif result.status == RegistryUpdateStatus.ALREADY_CURRENT:
                    print("✅ Registry is already up to date")
                    if verbose:
                        print(f"\nStatus: {result.status.value}")
                        print(f"Message: {result.message}")
                        if result.url:
                            print(f"URL: {result.url}")
                        print(f"Local registry file: {registry._config_path}")
                return 0
            else:
                print(f"❌ Failed to check for updates: {result.message}")
                if verbose:
                    if result.error:
                        print(f"Error details: {str(result.error)}")
                    print(f"Local registry file: {registry._config_path}")
                return 1

        if not force:
            if not click.confirm(
                "Update model configurations from remote?", default=True
            ):
                return 0

        # Update from remote
        result = registry.refresh_from_remote(url, force=force)

        if result.success:
            if result.status == RegistryUpdateStatus.UPDATED:
                print("✅ Registry updated successfully")
                if verbose:
                    # Show available models
                    aliases = sorted(
                        [
                            name
                            for name, caps in registry.models.items()
                            if not name.count("-") >= 3
                        ]
                    )
                    dated_models = sorted(
                        [
                            name
                            for name, caps in registry.models.items()
                            if name.count("-") >= 3
                        ]
                    )

                    print("\nAvailable models:")
                    print("  Aliases:")
                    for alias in aliases:
                        print(f"    - {alias}")
                    print("\n  Dated models:")
                    for model in dated_models:
                        print(f"    - {model}")

                    print(f"\nLocal registry file: {registry._config_path}")
            elif result.status == RegistryUpdateStatus.ALREADY_CURRENT:
                print("✅ Registry is already up to date")
                if verbose:
                    print(f"\nLocal registry file: {registry._config_path}")
            return 0
        else:
            print(f"❌ Failed to update registry: {result.message}")
            if verbose and result.error:
                print(f"Error details: {str(result.error)}")
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
