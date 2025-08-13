#!/usr/bin/env python3
"""CLI script for managing OpenAI Model Registry data files.

This script provides commands for updating, checking, and managing
model registry data files with various options for customization.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, cast

from ..data_manager import ENV_DATA_DIR, DataManager
from ..logging import get_logger

logger = get_logger(__name__)


def setup_data_dir_env(data_dir: Optional[str]) -> None:
    """Set up the data directory environment variable if provided."""
    if data_dir:
        os.environ[ENV_DATA_DIR] = str(Path(data_dir).expanduser().resolve())


def cmd_check(args: argparse.Namespace) -> int:
    """Check current data status and available updates."""
    setup_data_dir_env(args.data_dir)

    try:
        data_manager = DataManager()

        # Check current version
        current_version = data_manager._get_current_version()
        if current_version:
            print(f"Current data version: {current_version}")
        else:
            print("No local data version found (using bundled data)")

        # Check for updates
        print("Checking for updates...")
        latest_release = data_manager._fetch_latest_data_release()

        if not latest_release:
            print("No data releases found on GitHub")
            return 1

        latest_version = latest_release.get("tag_name", "")
        print(f"Latest available version: {latest_version}")

        if current_version and data_manager._compare_versions(latest_version, current_version) <= 0:
            print("✓ Data is up to date")
            return 0
        else:
            print("⚠ Update available")
            return 0

    except Exception as e:
        logger.error(f"Failed to check data status: {e}")
        return 1


def cmd_update(args: argparse.Namespace) -> int:
    """Update data files."""
    setup_data_dir_env(args.data_dir)

    try:
        data_manager = DataManager()

        if args.force:
            print("Force updating data files...")
            success = data_manager.force_update()
        else:
            print("Checking for data updates...")
            success = data_manager.check_for_updates()

        if success:
            print("✓ Data files updated successfully")
            return 0
        else:
            print("⚠ No updates available or update failed")
            return 1

    except Exception as e:
        logger.error(f"Failed to update data: {e}")
        return 1


def cmd_info(args: argparse.Namespace) -> int:
    """Show information about data configuration."""
    setup_data_dir_env(args.data_dir)

    try:
        data_manager = DataManager()

        print("Data Configuration:")
        print(f"  Data directory: {data_manager._data_dir}")
        print(f"  Update disabled: {not data_manager.should_update_data()}")

        # Environment variables
        print("\nEnvironment Variables:")
        print(f"  OMR_DISABLE_DATA_UPDATES: {os.getenv('OMR_DISABLE_DATA_UPDATES', 'not set')}")
        print(f"  OMR_DATA_VERSION_PIN: {os.getenv('OMR_DATA_VERSION_PIN', 'not set')}")
        print(f"  OMR_DATA_DIR: {os.getenv('OMR_DATA_DIR', 'not set')}")

        # File status
        print("\nData Files:")
        for filename in ["models.yaml", "overrides.yaml"]:
            file_path = data_manager.get_data_file_path(filename)
            if file_path:
                print(f"  {filename}: {file_path} (exists)")
            else:
                print(f"  {filename}: not found (will use bundled)")

        # Version info
        current_version = data_manager._get_current_version()
        if current_version:
            print(f"\nCurrent version: {current_version}")
        else:
            print("\nNo version info (using bundled data)")

        return 0

    except Exception as e:
        logger.error(f"Failed to get data info: {e}")
        return 1


def cmd_clean(args: argparse.Namespace) -> int:
    """Clean local data files (forces re-download on next use)."""
    setup_data_dir_env(args.data_dir)

    try:
        data_manager = DataManager()

        if not args.yes:
            response = input(f"Remove all data files from {data_manager._data_dir}? [y/N]: ")
            if response.lower() not in ("y", "yes"):
                print("Cancelled")
                return 0

        # Remove data files
        files_removed = 0
        for filename in ["models.yaml", "overrides.yaml", "version_info.json"]:
            file_path = data_manager._data_dir / filename
            if file_path.exists():
                file_path.unlink()
                files_removed += 1
                print(f"Removed: {filename}")

        if files_removed > 0:
            print(f"✓ Removed {files_removed} files")
        else:
            print("No files to remove")

        return 0

    except Exception as e:
        logger.error(f"Failed to clean data: {e}")
        return 1


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Manage OpenAI Model Registry data files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s check                    # Check current status
  %(prog)s update                   # Update if newer version available
  %(prog)s update --force           # Force update to latest version
  %(prog)s info                     # Show configuration and file status
  %(prog)s clean                    # Remove local data files

Environment Variables:
  OMR_DISABLE_DATA_UPDATES=1        # Disable automatic updates
  OMR_DATA_VERSION_PIN=v1.2.3       # Pin to specific version
  OMR_DATA_DIR=/custom/path         # Use custom data directory
        """,
    )

    parser.add_argument("--data-dir", type=str, help="Custom data directory (overrides OMR_DATA_DIR)")

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Check command
    check_parser = subparsers.add_parser("check", help="Check data status and available updates")
    check_parser.set_defaults(func=cmd_check)

    # Update command
    update_parser = subparsers.add_parser("update", help="Update data files")
    update_parser.add_argument("--force", action="store_true", help="Force update to latest version")
    update_parser.set_defaults(func=cmd_update)

    # Info command
    info_parser = subparsers.add_parser("info", help="Show data configuration and status")
    info_parser.set_defaults(func=cmd_info)

    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Remove local data files")
    clean_parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    clean_parser.set_defaults(func=cmd_clean)

    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Set up logging
    if args.verbose:
        import logging

        logging.basicConfig(level=logging.DEBUG)

    # Run the command
    try:
        return cast(int, args.func(args))
    except KeyboardInterrupt:
        print("\nInterrupted")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
