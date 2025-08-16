"""Tests for CLI cache commands."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from openai_model_registry.cli.commands.cache import get_cache_info


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_registry() -> Mock:
    """Create a mock ModelRegistry for testing."""
    mock = Mock()
    mock.config = Mock()
    mock.config.user_data_dir = Path("/fake/user/data")
    mock._data_manager = Mock()
    mock._data_manager.get_cache_info.return_value = {
        "cache_dir": "/fake/cache",
        "total_size": 1024 * 1024,  # 1MB
        "file_count": 5,
        "files": [
            {
                "path": "/fake/cache/models.yaml",
                "size": 512 * 1024,
                "modified": "2025-01-31T10:00:00Z",
                "etag": "abc123",
            },
            {
                "path": "/fake/cache/overrides.yaml",
                "size": 256 * 1024,
                "modified": "2025-01-31T09:00:00Z",
                "etag": None,
            },
        ],
    }
    return mock


class TestCacheInfo:
    """Test cache info command."""

    @patch("openai_model_registry.cli.commands.cache.get_cache_info")
    def test_cache_info_table_format(self, mock_get_cache_info: MagicMock, cli_runner: CliRunner) -> None:
        """Test cache info with table format."""
        # Mock the actual cache info structure
        mock_get_cache_info.return_value = {
            "directory": "/fake/cache",
            "exists": True,
            "total_size": 1024 * 1024,
            "total_size_formatted": "1.0 MB",
            "files": [
                {
                    "name": "models.yaml",
                    "path": "/fake/cache/models.yaml",
                    "size": 512 * 1024,
                    "size_formatted": "512.0 KB",
                    "modified": "2025-01-31 10:00:00",
                    "etag": "abc123",
                }
            ],
        }

        # Use the main CLI app to get proper context
        from openai_model_registry.cli.app import app

        result = cli_runner.invoke(app, ["cache", "info"])

        assert result.exit_code == 0
        assert "models.yaml" in result.output
        assert "512.0 KB" in result.output  # File size

    @patch("openai_model_registry.cli.commands.cache.get_cache_info")
    def test_cache_info_empty_cache(self, mock_get_cache_info: MagicMock, cli_runner: CliRunner) -> None:
        """Test cache info with empty cache."""
        mock_get_cache_info.return_value = {
            "directory": "/fake/cache",
            "exists": True,
            "total_size": 0,
            "total_size_formatted": "0 B",
            "files": [],
        }

        from openai_model_registry.cli.app import app

        result = cli_runner.invoke(app, ["cache", "info"])

        assert result.exit_code == 0
        # Check JSON output structure
        assert '"total_size_bytes": 0' in result.output
        assert '"file_count": 0' in result.output

    @patch("openai_model_registry.cli.commands.cache.get_cache_info")
    def test_cache_info_nonexistent_cache(self, mock_get_cache_info: MagicMock, cli_runner: CliRunner) -> None:
        """Test cache info when cache directory doesn't exist."""
        mock_get_cache_info.return_value = {
            "directory": "/fake/cache",
            "exists": False,
            "total_size": 0,
            "total_size_formatted": "0 B",
            "files": [],
        }

        from openai_model_registry.cli.app import app

        result = cli_runner.invoke(app, ["cache", "info"])

        assert result.exit_code == 0
        # Check JSON output structure for non-existent cache
        assert '"cache_directory": "/fake/cache"' in result.output
        assert '"file_count": 0' in result.output

    @patch("openai_model_registry.cli.commands.cache.get_cache_info")
    def test_cache_info_error_handling(self, mock_get_cache_info: MagicMock, cli_runner: CliRunner) -> None:
        """Test cache info error handling."""
        # Simulate error
        mock_get_cache_info.side_effect = Exception("Cache access failed")

        from openai_model_registry.cli.app import app

        result = cli_runner.invoke(app, ["cache", "info"])

        assert result.exit_code != 0
        assert "Error" in result.output


class TestCacheClear:
    """Test cache clear command."""

    @patch("openai_model_registry.cli.commands.cache.ModelRegistry")
    @patch("openai_model_registry.cli.commands.cache.get_cache_info")
    def test_cache_clear_with_confirmation(
        self, mock_get_cache_info: MagicMock, mock_registry_class: MagicMock, cli_runner: CliRunner
    ) -> None:
        """Test cache clear with user confirmation."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock cache info before and after clearing
        cache_info_before = {
            "directory": "/fake/cache",
            "exists": True,
            "files": [
                {"name": "models.yaml", "size_formatted": "50.0 KB"},
                {"name": "overrides.yaml", "size_formatted": "1.0 KB"},
            ],
        }
        cache_info_after = {
            "directory": "/fake/cache",
            "exists": True,
            "files": [],
        }

        mock_get_cache_info.side_effect = [cache_info_before, cache_info_before, cache_info_after]

        # Simulate user confirming with 'y'
        from openai_model_registry.cli.app import app

        result = cli_runner.invoke(app, ["cache", "clear"], input="y\n")

        assert result.exit_code == 0
        assert "models.yaml" in result.output
        assert "overrides.yaml" in result.output
        mock_registry.clear_cache.assert_called_once()

    @patch("openai_model_registry.cli.commands.cache.ModelRegistry")
    @patch("openai_model_registry.cli.commands.cache.get_cache_info")
    def test_cache_clear_with_yes_flag(
        self, mock_get_cache_info: MagicMock, mock_registry_class: MagicMock, cli_runner: CliRunner
    ) -> None:
        """Test cache clear with --yes flag (no confirmation)."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock cache info before and after clearing
        cache_info_before = {
            "directory": "/fake/cache",
            "exists": True,
            "files": [
                {"name": "models.yaml", "size_formatted": "50.0 KB"},
            ],
        }
        cache_info_after = {
            "directory": "/fake/cache",
            "exists": True,
            "files": [],
        }

        mock_get_cache_info.side_effect = [cache_info_before, cache_info_after]

        from openai_model_registry.cli.app import app

        result = cli_runner.invoke(app, ["cache", "clear", "--yes"])

        assert result.exit_code == 0
        mock_registry.clear_cache.assert_called_once()

    @patch("openai_model_registry.cli.commands.cache.get_cache_info")
    def test_cache_clear_user_cancels(self, mock_get_cache_info: MagicMock, cli_runner: CliRunner) -> None:
        """Test cache clear when user cancels."""
        mock_get_cache_info.return_value = {
            "directory": "/fake/cache",
            "exists": True,
            "files": [{"name": "models.yaml", "size_formatted": "50.0 KB"}],
        }

        # Simulate user canceling with 'n'
        from openai_model_registry.cli.app import app

        result = cli_runner.invoke(app, ["cache", "clear"], input="n\n")

        assert result.exit_code == 0
        assert "cancelled" in result.output

    @patch("openai_model_registry.cli.commands.cache.get_cache_info")
    def test_cache_clear_empty_cache(self, mock_get_cache_info: MagicMock, cli_runner: CliRunner) -> None:
        """Test cache clear with empty cache."""
        mock_get_cache_info.return_value = {
            "directory": "/fake/cache",
            "exists": True,
            "files": [],
        }

        from openai_model_registry.cli.app import app

        result = cli_runner.invoke(app, ["cache", "clear"])

        assert result.exit_code == 0
        assert "No cache files found" in result.output

    @patch("openai_model_registry.cli.commands.cache.ModelRegistry")
    @patch("openai_model_registry.cli.commands.cache.get_cache_info")
    def test_cache_clear_error_handling(
        self, mock_get_cache_info: MagicMock, mock_registry_class: MagicMock, cli_runner: CliRunner
    ) -> None:
        """Test cache clear error handling."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Simulate error during clear
        mock_registry.clear_cache.side_effect = PermissionError("Access denied")

        mock_get_cache_info.return_value = {
            "directory": "/fake/cache",
            "exists": True,
            "files": [{"name": "models.yaml", "size_formatted": "50.0 KB"}],
        }

        from openai_model_registry.cli.app import app

        result = cli_runner.invoke(app, ["cache", "clear", "--yes"])

        assert result.exit_code != 0
        assert "Error" in result.output


class TestGetCacheInfo:
    """Test get_cache_info utility function."""

    def test_get_cache_info_integration(self) -> None:
        """Test get_cache_info integration with real registry."""
        # This is an integration test that uses the real function
        result = get_cache_info()

        # Check expected structure
        assert "directory" in result
        assert "exists" in result
        assert "total_size" in result
        assert "total_size_formatted" in result
        assert "files" in result
        assert isinstance(result["files"], list)

        # Check file structure if files exist
        if result["files"]:
            file_info = result["files"][0]
            assert "name" in file_info
            assert "path" in file_info
            assert "size" in file_info
            assert "size_formatted" in file_info
            assert "modified" in file_info


class TestFileEtagInfo:
    """Test _get_file_etag_info utility function."""

    def test_etag_from_etag_file(self) -> None:
        """Test reading ETag from .etag file."""
        from openai_model_registry.cli.commands.cache import _get_file_etag_info

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file and .etag file
            test_file = Path(temp_dir) / "test.yaml"
            etag_file = Path(temp_dir) / "test.yaml.etag"

            test_file.write_text("test content")
            etag_file.write_text("abc123def")

            result = _get_file_etag_info(test_file)
            assert result == "abc123def"

    def test_etag_from_meta_file(self) -> None:
        """Test reading ETag from .meta file."""
        from openai_model_registry.cli.commands.cache import _get_file_etag_info

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file and .meta file
            test_file = Path(temp_dir) / "test.yaml"
            meta_file = Path(temp_dir) / "test.yaml.meta"

            test_file.write_text("test content")
            meta_file.write_text(json.dumps({"etag": "meta123", "other": "data"}))

            result = _get_file_etag_info(test_file)
            assert result == "meta123"

    def test_no_etag_available(self) -> None:
        """Test when no ETag information is available."""
        from openai_model_registry.cli.commands.cache import _get_file_etag_info

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file without etag/meta files
            test_file = Path(temp_dir) / "test.yaml"
            test_file.write_text("test content")

            result = _get_file_etag_info(test_file)
            assert result is None

    def test_invalid_meta_file(self) -> None:
        """Test handling of invalid .meta file."""
        from openai_model_registry.cli.commands.cache import _get_file_etag_info

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file and invalid .meta file
            test_file = Path(temp_dir) / "test.yaml"
            meta_file = Path(temp_dir) / "test.yaml.meta"

            test_file.write_text("test content")
            meta_file.write_text("invalid json")

            result = _get_file_etag_info(test_file)
            assert result is None

    def test_file_not_found(self) -> None:
        """Test handling of non-existent file."""
        from openai_model_registry.cli.commands.cache import _get_file_etag_info

        non_existent_file = Path("/fake/path/does/not/exist.yaml")
        result = _get_file_etag_info(non_existent_file)
        assert result is None
