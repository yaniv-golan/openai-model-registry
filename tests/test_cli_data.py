"""Tests for CLI data commands."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from openai_model_registry.cli.app import app


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


class TestDataDump:
    """Test data dump command."""

    @patch("openai_model_registry.cli.commands.data.ModelRegistry")
    def test_data_dump_effective_default(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test data dump with default effective mode."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock effective data
        mock_registry.dump_effective.return_value = {
            "models": {
                "gpt-4": {
                    "provider": "openai",
                    "capabilities": ["text_generation"],
                }
            },
            "overrides": {},
        }

        result = cli_runner.invoke(app, ["data", "dump"])

        assert result.exit_code == 0
        # Should contain JSON output
        output_data = json.loads(result.output)
        assert "models" in output_data
        assert "gpt-4" in output_data["models"]
        mock_registry.dump_effective.assert_called_once()

    @patch("openai_model_registry.cli.commands.data.ModelRegistry")
    def test_data_dump_effective_explicit(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test data dump with explicit --effective flag."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        mock_registry.dump_effective.return_value = {
            "models": {"gpt-3.5-turbo": {"provider": "openai"}},
            "overrides": {},
        }

        result = cli_runner.invoke(app, ["data", "dump", "--effective"])

        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert "models" in output_data
        assert "gpt-3.5-turbo" in output_data["models"]
        mock_registry.dump_effective.assert_called_once()

    @patch("openai_model_registry.cli.commands.data.ModelRegistry")
    @patch("openai_model_registry.cli.commands.data.Path")
    @patch("builtins.open")
    @patch("openai_model_registry.cli.commands.data.yaml")
    def test_data_dump_raw(
        self,
        mock_yaml: MagicMock,
        mock_open: MagicMock,
        mock_path: MagicMock,
        mock_registry_class: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test data dump with --raw flag."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock raw data paths
        mock_registry.get_raw_data_paths.return_value = {
            "models": "/fake/path/models.yaml",
            "overrides": "/fake/path/overrides.yaml",
        }

        # Mock file existence
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        # Mock file reading and YAML parsing
        mock_yaml.safe_load.side_effect = [
            {"claude-3": {"provider": "anthropic"}},  # models.yaml
            {},  # overrides.yaml
        ]

        result = cli_runner.invoke(app, ["data", "dump", "--raw"])

        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert "models" in output_data
        assert "claude-3" in output_data["models"]
        mock_registry.get_raw_data_paths.assert_called_once()

    @patch("openai_model_registry.cli.commands.data.ModelRegistry")
    def test_data_dump_to_file(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test data dump with output to file."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        mock_registry.dump_effective.return_value = {
            "models": {"test-model": {"provider": "test"}},
            "overrides": {},
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as temp_file:
            temp_path = temp_file.name

        try:
            result = cli_runner.invoke(app, ["data", "dump", "--output", temp_path])

            assert result.exit_code == 0
            # The command doesn't output a success message, it just writes to file

            # Verify file contents
            with open(temp_path, "r") as f:
                output_data = json.load(f)
            assert "models" in output_data
            assert "test-model" in output_data["models"]
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @patch("openai_model_registry.cli.commands.data.ModelRegistry")
    def test_data_dump_error_handling(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test data dump error handling."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Simulate error
        mock_registry.dump_effective.side_effect = Exception("Registry error")

        result = cli_runner.invoke(app, ["data", "dump"])

        assert result.exit_code != 0
        assert "Error" in result.output

    @patch("openai_model_registry.cli.commands.data.ModelRegistry")
    def test_data_dump_file_write_error(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test data dump file write error handling."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        mock_registry.dump_effective.return_value = {"models": {}, "overrides": {}}

        # Try to write to invalid path
        result = cli_runner.invoke(app, ["data", "dump", "--output", "/invalid/path/file.json"])

        assert result.exit_code != 0
        assert "Error" in result.output


class TestDataPaths:
    """Test data paths command."""

    @patch("openai_model_registry.cli.commands.data.ModelRegistry")
    def test_data_paths_table_format(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test data paths with table format."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock the methods that the paths command actually calls
        mock_registry.get_raw_data_paths.return_value = {
            "models": "/fake/user/data/models.yaml",
            "overrides": "/fake/user/data/overrides.yaml",
        }

        mock_registry.get_data_info.return_value = {
            "data_directory": "/fake/user/data",
            "current_version": "1.0.0",
            "data_files": {
                "models.yaml": {
                    "exists": True,
                    "path": "/fake/user/data/models.yaml",
                    "using_bundled": False,
                },
                "overrides.yaml": {
                    "exists": True,
                    "path": "/fake/user/data/overrides.yaml",
                    "using_bundled": False,
                },
            },
        }

        result = cli_runner.invoke(app, ["data", "paths"])

        assert result.exit_code == 0
        assert "models.yaml" in result.output
        assert "overrides.yaml" in result.output

    @patch("openai_model_registry.cli.commands.data.ModelRegistry")
    def test_data_paths_json_format(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test data paths with JSON format."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock the methods that the paths command actually calls
        mock_registry.get_raw_data_paths.return_value = {
            "models": "/fake/user/data/models.yaml",
            "overrides": "/fake/user/data/overrides.yaml",
        }

        mock_registry.get_data_info.return_value = {
            "data_directory": "/fake/user/data",
            "current_version": "1.0.0",
            "data_files": {
                "models.yaml": {
                    "exists": True,
                    "path": "/fake/user/data/models.yaml",
                    "using_bundled": False,
                },
                "overrides.yaml": {
                    "exists": True,
                    "path": "/fake/user/data/overrides.yaml",
                    "using_bundled": False,
                },
            },
        }

        result = cli_runner.invoke(app, ["data", "paths"])

        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert "data_sources" in output_data
        assert "models.yaml" in output_data["data_sources"]
        assert "overrides.yaml" in output_data["data_sources"]

    @patch("openai_model_registry.cli.commands.data.ModelRegistry")
    def test_data_paths_error_handling(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test data paths error handling."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Simulate error accessing registry methods
        mock_registry.get_raw_data_paths.side_effect = Exception("Registry error")

        result = cli_runner.invoke(app, ["data", "paths"])

        assert result.exit_code != 0
        assert "Error" in result.output


class TestDataEnv:
    """Test data env command."""

    def test_data_env_table_format(self, cli_runner: CliRunner) -> None:
        """Test data env with table format."""
        # Set some test environment variables
        test_env = {
            "OMR_PROVIDER": "openai",
            "OMR_DEBUG": "1",
            "PATH": "/usr/bin:/bin",  # Non-OMR variable should be filtered out
        }

        with patch.dict(os.environ, test_env, clear=False):
            result = cli_runner.invoke(app, ["data", "env"])

            assert result.exit_code == 0
            # The output is in JSON format by default, check for OMR variables
            assert "OMR_PROVIDER" in result.output
            assert "openai" in result.output
            # PATH should not appear as a standalone environment variable name
            # but OMR_MODEL_REGISTRY_PATH might appear, so we check more specifically
            assert '"PATH"' not in result.output  # Should be filtered out

    def test_data_env_json_format(self, cli_runner: CliRunner) -> None:
        """Test data env with JSON format (default output is JSON)."""
        test_env = {
            "OMR_PROVIDER": "azure",
            "OMR_VERBOSE": "2",
        }

        with patch.dict(os.environ, test_env, clear=False):
            result = cli_runner.invoke(app, ["data", "env"])

            assert result.exit_code == 0
            output_data = json.loads(result.output)
            # Check the actual structure - environment variables are nested
            assert "environment_variables" in output_data
            env_vars = output_data["environment_variables"]
            assert "OMR_PROVIDER" in env_vars
            assert env_vars["OMR_PROVIDER"]["value"] == "azure"
            assert env_vars["OMR_PROVIDER"]["set"] is True

    def test_data_env_no_omr_vars(self, cli_runner: CliRunner) -> None:
        """Test data env when no OMR variables are set."""
        # Clear all OMR environment variables
        omr_vars = [key for key in os.environ.keys() if key.startswith("OMR_")]

        # Save original values and remove them temporarily
        original_values = {var: os.environ.get(var) for var in omr_vars}
        for var in omr_vars:
            if var in os.environ:
                del os.environ[var]

        try:
            result = cli_runner.invoke(app, ["data", "env"])

            assert result.exit_code == 0
            # Check the JSON structure shows no variables are set
            output_data = json.loads(result.output)
            assert "set_count" in output_data
            assert output_data["set_count"] == 0
        finally:
            # Restore original environment variables
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
