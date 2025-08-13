"""Data inspection commands for the OMR CLI."""

import hashlib
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, TextIO

import click
import yaml

from ...registry import ModelRegistry
from ..formatters import (
    create_console,
    format_data_paths_json,
    format_data_paths_table,
    format_env_vars_json,
    format_env_vars_table,
    format_json,
)
from ..utils import ExitCode, get_omr_env_vars, handle_error


def _verify_file_checksum(file_path: Path, file_type: str) -> Optional[bool]:
    """Verify file checksum against checksums.txt if available.

    Args:
        file_path: Path to the file to verify
        file_type: Type of file (models, overrides)

    Returns:
        True if verified, False if mismatch, None if no checksum available
    """
    try:
        # Look for checksums.txt in the same directory
        checksums_path = file_path.parent / "checksums.txt"
        if not checksums_path.exists():
            return None

        # Parse checksums.txt
        checksums = {}
        with open(checksums_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and " " in line:
                    parts = line.split(" ", 1)
                    if len(parts) == 2:
                        checksums[parts[1]] = parts[0]

        # Check if we have a checksum for this file
        expected_filename = f"{file_type}.yaml"
        if expected_filename not in checksums:
            return None

        # Calculate actual checksum
        with open(file_path, "rb") as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()

        expected_hash = checksums[expected_filename]
        return actual_hash == expected_hash

    except (OSError, IOError):
        return None


def _get_file_etag(file_path: Path) -> Optional[str]:
    """Get etag information for a file if available.

    Args:
        file_path: Path to the file

    Returns:
        Etag string if available, None otherwise
    """
    try:
        # Look for .etag file or similar metadata
        etag_path = file_path.with_suffix(file_path.suffix + ".etag")
        if etag_path.exists():
            with open(etag_path, "r") as f:
                return f.read().strip()

        # Could also check for HTTP cache headers in a .meta file
        meta_path = file_path.with_suffix(file_path.suffix + ".meta")
        if meta_path.exists():
            try:
                with open(meta_path, "r") as f:
                    import json

                    meta_data = json.load(f)
                    etag_val = meta_data.get("etag")
                    return str(etag_val) if etag_val is not None else None
            except (json.JSONDecodeError, KeyError):
                pass

        return None

    except (OSError, IOError):
        return None


@click.group()
def data() -> None:
    """Inspect data sources and configuration."""
    pass


@data.command()
@click.pass_context
def paths(ctx: click.Context) -> None:
    """Show resolved data source paths and precedence."""
    try:
        registry = ModelRegistry.get_default()
        raw_paths = registry.get_raw_data_paths()
        data_info = registry.get_data_info()

        # Enhance paths with additional info including checksum verification and etag/mtime
        enhanced_paths: dict[str, dict[str, object]] = {}
        for file_type, path in raw_paths.items():
            # Determine the actual source of the path by comparing actual paths
            source = "Bundled Package"
            if path:
                import os
                from pathlib import Path

                resolved_path = str(Path(path).resolve())

                # Check if path matches OMR_MODEL_REGISTRY_PATH (only for models.yaml)
                if file_type == "models" and "OMR_MODEL_REGISTRY_PATH" in os.environ:
                    registry_path = os.getenv("OMR_MODEL_REGISTRY_PATH")
                    if registry_path and str(Path(registry_path).resolve()) == resolved_path:
                        source = "OMR_MODEL_REGISTRY_PATH"
                    else:
                        # Check if path is from OMR_DATA_DIR
                        omr_data_dir = os.getenv("OMR_DATA_DIR")
                        if omr_data_dir and resolved_path.startswith(str(Path(omr_data_dir).resolve())):
                            source = "OMR_DATA_DIR"
                        else:
                            source = "User Data"
                else:
                    # Check if path is from OMR_DATA_DIR
                    omr_data_dir = os.getenv("OMR_DATA_DIR")
                    if omr_data_dir and resolved_path.startswith(str(Path(omr_data_dir).resolve())):
                        source = "OMR_DATA_DIR"
                    else:
                        source = "User Data"

            file_info = {
                "path": path or "Bundled",
                "source": source,
                "exists": Path(path).exists() if path else True,
                "checksum_verified": None,
                "etag": None,
                "last_modified": None,
                "file_size": None,
            }

            # Add file-specific information if the file exists
            if path and Path(path).exists():
                try:
                    file_path = Path(path)
                    stat = file_path.stat()
                    file_info["file_size"] = stat.st_size
                    file_info["last_modified"] = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

                    # Try to get checksum verification status
                    file_info["checksum_verified"] = _verify_file_checksum(file_path, file_type)

                    # Try to get etag from accompanying metadata if available
                    etag_info = _get_file_etag(file_path)
                    if etag_info:
                        file_info["etag"] = etag_info

                except (OSError, IOError):
                    # If we can't read file info, leave the fields as None
                    pass
            elif not path:  # Bundled file
                file_info["checksum_verified"] = True  # Assume bundled files are verified

            enhanced_paths[f"{file_type}.yaml"] = file_info

        # Add data info if available
        if isinstance(data_info, dict):
            enhanced_paths.update(
                {
                    "data_directory": {
                        "path": data_info.get("user_data_dir", "N/A"),
                        "source": "System",
                        "exists": True,
                    }
                }
            )

        # Force strict validation: only json/yaml supported; table/csv should error
        format_type = ctx.obj["format"]
        output_file = None

        if format_type == "json":
            formatted_data = format_data_paths_json(enhanced_paths)
            format_json(formatted_data, output_file)
        else:  # table format
            console = create_console(output_file, ctx.obj["no_color"])
            format_data_paths_table(enhanced_paths, console)

    except Exception as e:
        handle_error(e, ExitCode.DATA_SOURCE_ERROR)


@data.command()
@click.pass_context
def env(ctx: click.Context) -> None:
    """Show effective OMR environment variables."""
    try:
        env_vars = get_omr_env_vars()

        format_type = ctx.obj["format"]
        output_file = None

        if format_type == "json":
            formatted_data = format_env_vars_json(env_vars)
            format_json(formatted_data, output_file)
        else:  # table format
            console = create_console(output_file, ctx.obj["no_color"])
            format_env_vars_table(env_vars, console)

    except Exception as e:
        handle_error(e, ExitCode.GENERIC_ERROR)


@data.command()
@click.option("--raw", is_flag=True, help="Dump original on-disk/bundled YAML (no provider merge).")
@click.option("--effective", is_flag=True, help="Dump fully merged, provider-adjusted dataset.")
@click.option("--output", "-o", type=click.Path(), help="Write output to file instead of stdout.")
@click.pass_context
def dump(
    ctx: click.Context,
    raw: bool = False,
    effective: bool = False,
    output: Optional[str] = None,
) -> None:
    """Dump registry data in various formats.

    If neither --raw nor --effective is specified, defaults to --effective.
    """
    try:
        # Default to effective if neither specified
        if not raw and not effective:
            effective = True

        registry = ModelRegistry.get_default()
        format_type = ctx.obj["format"]

        # Validate format support for data dump (no fallback: table/csv should error)
        if format_type not in ["json", "yaml"]:
            handle_error(
                click.BadParameter(
                    "Format '" + format_type + "' is not supported for data dump. Use 'json' or 'yaml'."
                ),
                ExitCode.INVALID_USAGE,
            )
            return

        # Prepare output
        output_file: Optional[TextIO] = None
        if output:
            output_file = open(output, "w")

        try:
            if raw:
                # Get raw data paths and read files directly
                raw_paths = registry.get_raw_data_paths()
                raw_data = {}

                for file_type, path in raw_paths.items():
                    if path and Path(path).exists():
                        with open(path, "r") as f:
                            raw_data[file_type] = yaml.safe_load(f)
                    else:
                        # Try to get bundled content using public API
                        content = registry.get_bundled_data_content(f"{file_type}.yaml")
                        if content:
                            raw_data[file_type] = yaml.safe_load(content)

                data_to_output = raw_data
            else:
                # Get effective merged data
                data_to_output = registry.dump_effective()

            # Output in requested format
            if format_type == "yaml":
                yaml_output = yaml.dump(data_to_output, default_flow_style=False, sort_keys=True)
                if output_file:
                    output_file.write(yaml_output)
                else:
                    click.echo(yaml_output)
            else:  # json format (default for dump)
                format_json(data_to_output, output_file or sys.stdout)

        finally:
            if output_file:
                output_file.close()

    except Exception as e:
        handle_error(e, ExitCode.DATA_SOURCE_ERROR)
