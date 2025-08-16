"""Cache management commands for the OMR CLI."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import click

from ...registry import ModelRegistry
from ..formatters import (
    create_console,
    format_cache_info_json,
    format_cache_info_table,
    format_json,
)
from ..utils import ExitCode, format_file_size, handle_error


def _get_file_etag_info(file_path: Path) -> Optional[str]:
    """Get ETag information for a cache file if available.

    Args:
        file_path: Path to the cache file

    Returns:
        ETag string if available, None otherwise
    """
    try:
        # Look for .etag file or similar metadata
        etag_path = file_path.with_suffix(file_path.suffix + ".etag")
        if etag_path.exists():
            with open(etag_path, "r") as f:
                return f.read().strip()

        # Check for HTTP cache headers in a .meta file
        meta_path = file_path.with_suffix(file_path.suffix + ".meta")
        if meta_path.exists():
            try:
                import json

                with open(meta_path, "r") as f:
                    meta_data = json.load(f)
                    etag_val = meta_data.get("etag")
                    return str(etag_val) if etag_val is not None else None
            except (json.JSONDecodeError, KeyError):
                pass

        return None

    except (OSError, IOError):
        return None


def get_cache_info() -> Dict[str, Any]:
    """Get information about cache files and directory.

    Returns:
        Dictionary containing cache information
    """
    try:
        registry = ModelRegistry.get_default()
        data_info = registry.get_data_info()

        if isinstance(data_info, dict) and "user_data_dir" in data_info:
            cache_dir = Path(data_info["user_data_dir"])
        else:
            # Fallback to getting user data dir directly
            from ...config_paths import get_user_data_dir

            cache_dir = get_user_data_dir()

        cache_info: Dict[str, Any] = {"directory": str(cache_dir), "exists": cache_dir.exists(), "files": []}

        if cache_dir.exists():
            # Look for common cache files
            cache_files = ["models.yaml", "overrides.yaml"]

            for filename in cache_files:
                file_path = cache_dir / filename
                if file_path.exists():
                    stat = file_path.stat()

                    # Try to get ETag information if available
                    etag = _get_file_etag_info(file_path)

                    cache_info["files"].append(
                        {
                            "name": filename,
                            "path": str(file_path),
                            "size": stat.st_size,
                            "size_formatted": format_file_size(stat.st_size),
                            "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                            "etag": etag,
                        }
                    )

        # Calculate total size
        total_size = int(sum(int(f.get("size", 0)) for f in cache_info["files"]))
        cache_info["total_size"] = total_size
        cache_info["total_size_formatted"] = format_file_size(total_size)

        return cache_info

    except Exception as e:
        return {"directory": "Unknown", "exists": False, "files": [], "total_size": 0, "error": str(e)}


@click.group()
def cache() -> None:
    """Manage registry cache."""
    pass


@cache.command()
@click.pass_context
def info(ctx: click.Context) -> None:
    """Show cache directory and file information."""
    try:
        cache_info = get_cache_info()

        format_type = ctx.obj["format"]

        if format_type == "json":
            formatted_data = format_cache_info_json(cache_info)
            format_json(formatted_data)
        else:
            # Table format
            console = create_console(no_color=ctx.obj["no_color"])
            format_cache_info_table(cache_info, console)

    except Exception as e:
        handle_error(e, ExitCode.GENERIC_ERROR)


@cache.command()
@click.option("--yes", is_flag=True, help="Confirm deletion without prompting (required for non-interactive use).")
@click.pass_context
def clear(ctx: click.Context, yes: bool = False) -> None:
    """Clear cached registry data files.

    This will remove cached models.yaml and overrides.yaml files
    from the user data directory. The registry will fall back to bundled data
    until the next update.
    """
    try:
        if not yes:
            # Interactive confirmation
            cache_info = get_cache_info()
            file_count = len(cache_info["files"])

            if file_count == 0:
                click.echo("No cache files found to clear.")
                return

            console = create_console(no_color=ctx.obj["no_color"])
            console.print(f"[yellow]Warning:[/yellow] This will delete {file_count} cache files:")

            for file_info in cache_info["files"]:
                console.print(f"  - {file_info['name']} ({file_info['size_formatted']})")

            console.print(f"\nCache directory: {cache_info['directory']}")

            if not click.confirm("\nAre you sure you want to clear the cache?"):
                console.print("Cache clear cancelled.")
                return

        # Perform the cache clear
        registry = ModelRegistry.get_default()

        # Get files before clearing
        cache_info_before = get_cache_info()
        files_before = [f["name"] for f in cache_info_before["files"]]

        # Clear the cache
        registry.clear_cache()

        # Get files after clearing to see what was actually removed
        cache_info_after = get_cache_info()
        files_after = [f["name"] for f in cache_info_after["files"]]

        removed_files = [f for f in files_before if f not in files_after]

        format_type = ctx.obj["format"]

        if format_type == "json":
            result_data = {
                "success": True,
                "files_removed": removed_files,
                "files_removed_count": len(removed_files),
                "cache_directory": cache_info_before["directory"],
            }
            format_json(result_data)
        else:
            console = create_console(no_color=ctx.obj["no_color"])

            if removed_files:
                console.print(f"✅ [green]Successfully cleared {len(removed_files)} cache files:[/green]")
                for filename in removed_files:
                    console.print(f"  - {filename}")
            else:
                console.print("ℹ️  No cache files were found to clear.")

            console.print(f"\nCache directory: {cache_info_before['directory']}")

    except Exception as e:
        handle_error(e, ExitCode.GENERIC_ERROR)
