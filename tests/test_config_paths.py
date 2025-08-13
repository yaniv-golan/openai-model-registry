"""Tests for the config_paths module."""

import os
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest

from openai_model_registry import config_paths
from openai_model_registry.config_paths import (
    APP_NAME,
    PARAM_CONSTRAINTS_FILENAME,
    copy_default_to_user_config,
    ensure_user_config_dir_exists,
    get_parameter_constraints_path,
    get_user_config_dir,
)


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


def test_user_config_dir_contains_app_name() -> None:
    """Test that the user config directory contains the app name."""
    config_dir = get_user_config_dir()
    assert APP_NAME in str(config_dir)


def test_user_config_dir_is_created() -> None:
    """Test that the user config directory is created if it doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("openai_model_registry.config_paths.platformdirs.user_config_dir") as mock_user_config_dir:
            temp_config_dir = Path(temp_dir) / APP_NAME
            mock_user_config_dir.return_value = str(temp_config_dir)

            # Directory should not exist yet
            assert not temp_config_dir.exists()

            # This should create the directory
            ensure_user_config_dir_exists()

            # Directory should now exist
            assert temp_config_dir.exists()
            assert temp_config_dir.is_dir()


# Model registry path functionality has been moved to DataManager


def test_get_parameter_constraints_path() -> None:
    """Test that the parameter constraints path is correct."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_package_config_dir = Path(temp_dir) / APP_NAME
        temp_package_config_dir.mkdir(parents=True)

        # Create a test file
        test_file = temp_package_config_dir / PARAM_CONSTRAINTS_FILENAME
        test_file.write_text("test content")

        # Set up path for user config dir that should be ignored
        user_config_dir = Path(temp_dir) / "user" / APP_NAME

        # Create the side effect function that properly handles the self parameter
        def is_file_side_effect(self: Path) -> bool:
            """Return True only for the package config file."""
            return str(self) == str(test_file)

        # Mock both directories and the is_file method
        with (
            patch(
                "openai_model_registry.config_paths.get_package_config_dir",
                return_value=temp_package_config_dir,
            ),
            patch(
                "openai_model_registry.config_paths.get_user_config_dir",
                return_value=user_config_dir,
            ),
            patch(
                "pathlib.Path.is_file",
                autospec=True,
                side_effect=is_file_side_effect,
            ),
        ):
            expected_path = str(test_file)
            assert get_parameter_constraints_path() == expected_path


def test_copy_default_to_user_config() -> None:
    """Test copying default config to user directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up package and user config dirs
        package_dir = Path(temp_dir) / "package"
        user_dir = Path(temp_dir) / "user"

        # Create package config file
        package_dir.mkdir(parents=True)
        test_file = "test.yml"
        package_file = package_dir / test_file
        package_file.write_text("test content")

        # Mock the config dir functions
        with (
            patch(
                "openai_model_registry.config_paths.get_package_config_dir",
                return_value=package_dir,
            ),
            patch(
                "openai_model_registry.config_paths.get_user_config_dir",
                return_value=user_dir,
            ),
        ):
            # Copy the file
            result = copy_default_to_user_config(test_file)

            # Verify the file was copied
            assert result is True
            assert (user_dir / test_file).exists()
            assert (user_dir / test_file).read_text() == "test content"


def test_copy_default_to_user_config_existing_file() -> None:
    """Test that copy_default_to_user_config doesn't overwrite existing files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up package and user config dirs
        package_dir = Path(temp_dir) / "package"
        user_dir = Path(temp_dir) / "user"

        # Create package and user config files
        package_dir.mkdir(parents=True)
        user_dir.mkdir(parents=True)

        test_file = "test.yml"
        package_file = package_dir / test_file
        user_file = user_dir / test_file

        package_file.write_text("package content")
        user_file.write_text("user content")

        # Mock the config dir functions
        with (
            patch(
                "openai_model_registry.config_paths.get_package_config_dir",
                return_value=package_dir,
            ),
            patch(
                "openai_model_registry.config_paths.get_user_config_dir",
                return_value=user_dir,
            ),
        ):
            # Try to copy the file
            result = copy_default_to_user_config(test_file)

            # Verify the file was not copied
            assert result is False
            assert user_file.read_text() == "user content"


# Model registry path environment variable handling moved to DataManager


def test_get_parameter_constraints_path_env_var() -> None:
    """Test that environment variable takes precedence for parameter constraints path."""
    custom_path = "/custom/path/parameter_constraints.yml"

    with (
        patch.dict(os.environ, {"OMR_PARAMETER_CONSTRAINTS_PATH": custom_path}),
        patch("pathlib.Path.is_file", return_value=True),
    ):
        assert get_parameter_constraints_path() == custom_path


def test_copy_default_to_user_config_error_handling(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test error handling in copy_default_to_user_config function."""

    # Mock the write_bytes method to raise an OSError
    def mock_write_bytes(self: Path, data: bytes) -> None:
        raise OSError("Simulated write error")

    # Setup paths
    package_dir = tmp_path / "package"
    user_dir = tmp_path / "user"
    package_dir.mkdir()
    user_dir.mkdir()

    test_file = package_dir / "test.yml"
    test_file.write_text("test content")

    # Apply monkeypatches
    monkeypatch.setattr(Path, "write_bytes", mock_write_bytes)
    monkeypatch.setattr(config_paths, "get_package_config_dir", lambda: package_dir)
    monkeypatch.setattr(config_paths, "get_user_config_dir", lambda: user_dir)

    # Attempt to copy should raise OSError
    with pytest.raises(OSError) as excinfo:
        copy_default_to_user_config("test.yml")

    assert "Simulated write error" in str(excinfo.value)
