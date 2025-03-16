"""Configuration path handling for model registry.

This module implements path resolution for config files following the XDG Base Directory
Specification for user-specific configuration files.
"""

import os
from pathlib import Path

import platformdirs

# Application name used for directory paths
APP_NAME = "openai-model-registry"

# Environment variable names
ENV_MODEL_REGISTRY = "MODEL_REGISTRY_PATH"
ENV_PARAM_CONSTRAINTS = "PARAMETER_CONSTRAINTS_PATH"

# Default filenames
MODEL_REGISTRY_FILENAME = "models.yml"
PARAM_CONSTRAINTS_FILENAME = "parameter_constraints.yml"


def get_package_config_dir() -> Path:
    """Get the path to the package's config directory."""
    return Path(__file__).parent / "config"


def get_user_config_dir() -> Path:
    """Get the path to the user's config directory for this application."""
    return Path(platformdirs.user_config_dir(APP_NAME))


def ensure_user_config_dir_exists() -> None:
    """Ensure that the user config directory exists."""
    user_dir = get_user_config_dir()
    os.makedirs(user_dir, exist_ok=True)


def copy_default_to_user_config(filename: str) -> bool:
    """Copy a default config file to the user config directory if it doesn't exist.

    Args:
        filename: Name of the config file to copy

    Returns:
        True if file was copied, False if no action was taken
    """
    package_file = get_package_config_dir() / filename
    user_file = get_user_config_dir() / filename

    # Don't copy if user file already exists
    if user_file.exists():
        return False

    # Ensure directory exists
    ensure_user_config_dir_exists()

    # Only copy if package file exists
    if package_file.exists():
        user_file.write_bytes(package_file.read_bytes())
        return True

    return False


def get_model_registry_path() -> str:
    """Get the path to the model registry file, respecting XDG specification.

    Returns:
        Path to the model registry file
    """
    # 1. Check environment variable
    env_path = os.environ.get(ENV_MODEL_REGISTRY)
    if env_path and Path(env_path).is_file():
        return env_path

    # 2. Check user config directory
    user_path = get_user_config_dir() / MODEL_REGISTRY_FILENAME
    if user_path.is_file():
        return str(user_path)

    # 3. Fall back to package directory
    return str(get_package_config_dir() / MODEL_REGISTRY_FILENAME)


def get_parameter_constraints_path() -> str:
    """Get the path to the parameter constraints file, respecting XDG specification.

    Returns:
        Path to the parameter constraints file
    """
    # 1. Check environment variable
    env_path = os.environ.get(ENV_PARAM_CONSTRAINTS)
    if env_path and Path(env_path).is_file():
        return env_path

    # 2. Check user config directory
    user_path = get_user_config_dir() / PARAM_CONSTRAINTS_FILENAME
    if user_path.is_file():
        return str(user_path)

    # 3. Fall back to package directory
    return str(get_package_config_dir() / PARAM_CONSTRAINTS_FILENAME)
