"""Comprehensive CLI unit tests for the OMR CLI."""

import json
import os
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from openai_model_registry.cli import app
from openai_model_registry.cli.utils.helpers import ExitCode


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_registry() -> Mock:
    """Create a mock ModelRegistry for testing."""
    mock = Mock()
    mock.models = ["gpt-4o", "gpt-3.5-turbo"]
    mock.get_capabilities.return_value = Mock(
        context_window=128000,
        max_output_tokens=4096,
        pricing=Mock(scheme="per_token", unit="million_tokens", input_cost_per_unit=2.50, output_cost_per_unit=10.00),
        supports_vision=True,
        supports_function_calling=True,
        supports_streaming=True,
    )
    mock.get_data_info.return_value = {"user_data_dir": "/fake/user/data", "schema_version": "1.0.0"}
    mock.get_raw_data_paths.return_value = {
        "models": None,  # Bundled
        "overrides": None,  # Bundled
    }
    mock.list_providers.return_value = ["openai", "azure"]
    mock.dump_effective.return_value = {
        "provider": "openai",
        "models": {
            "gpt-4o": {
                "context_window": {"total": 128000, "output": 4096},
                "pricing": {
                    "scheme": "per_token",
                    "unit": "million_tokens",
                    "input_cost_per_unit": 2.50,
                    "output_cost_per_unit": 10.00,
                },
                "supports_vision": True,
                "supports_function_calling": True,
                "supports_streaming": True,
            }
        },
    }
    mock.clear_cache.return_value = None
    return mock


class TestHelpJson:
    """Test --help-json functionality."""

    def test_root_help_json(self, cli_runner: CliRunner) -> None:
        """Test --help-json at root level returns valid JSON."""
        result = cli_runner.invoke(app, ["--help-json"])

        assert result.exit_code == 0
        help_data = json.loads(result.output)

        # Verify structure
        assert "command" in help_data
        assert "description" in help_data
        assert "global_options" in help_data
        assert "commands" in help_data
        assert "exit_codes" in help_data

        # Verify key commands are present
        assert "data" in help_data["commands"]
        assert "models" in help_data["commands"]
        assert "providers" in help_data["commands"]
        assert "update" in help_data["commands"]
        assert "cache" in help_data["commands"]


class TestProviderResolution:
    """Test provider resolution precedence."""

    @patch("openai_model_registry.cli.app.app.ModelRegistry")
    def test_cli_flag_precedence(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test CLI flag takes precedence over environment."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry
        mock_registry.list_providers.return_value = ["openai", "azure"]

        with patch.dict(os.environ, {"OMR_PROVIDER": "openai"}):
            result = cli_runner.invoke(app, ["--provider", "azure", "providers", "current"])

        assert result.exit_code == 0
        assert "azure" in result.output
        assert "CLI flag" in result.output

    @patch("openai_model_registry.cli.app.app.ModelRegistry")
    def test_env_var_precedence(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test environment variable precedence over default."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry
        mock_registry.list_providers.return_value = ["openai", "azure"]

        with patch.dict(os.environ, {"OMR_PROVIDER": "azure"}):
            result = cli_runner.invoke(app, ["providers", "current"])

        assert result.exit_code == 0
        assert "azure" in result.output
        assert "Environment variable" in result.output

    @patch("openai_model_registry.cli.app.app.ModelRegistry")
    def test_default_precedence(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test default provider when no CLI flag or env var."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry
        mock_registry.list_providers.return_value = ["openai", "azure"]

        with patch.dict(os.environ, {}, clear=True):
            result = cli_runner.invoke(app, ["providers", "current"])

        assert result.exit_code == 0
        assert "openai" in result.output
        assert "default" in result.output.lower()


class TestDataPaths:
    """Test data paths command scenarios."""

    @patch("openai_model_registry.cli.commands.data.ModelRegistry")
    def test_bundled_only_scenario(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test data paths when using bundled data only."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry
        mock_registry.get_raw_data_paths.return_value = {"models": None, "overrides": None}
        mock_registry.get_data_info.return_value = {"user_data_dir": "/fake/user/data"}

        result = cli_runner.invoke(app, ["--format", "json", "data", "paths"])

        assert result.exit_code == 0
        data = json.loads(result.output)

        assert "data_sources" in data
        assert data["data_sources"]["models.yaml"]["source"] == "Bundled Package"
        assert data["data_sources"]["overrides.yaml"]["source"] == "Bundled Package"

    @patch("openai_model_registry.cli.commands.data.ModelRegistry")
    def test_user_data_scenario(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test data paths when using user data directory."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry
        mock_registry.get_raw_data_paths.return_value = {
            "models": "/fake/user/data/models.yaml",
            "overrides": "/fake/user/data/overrides.yaml",
        }
        mock_registry.get_data_info.return_value = {"user_data_dir": "/fake/user/data"}

        with patch("pathlib.Path.exists", return_value=True):
            result = cli_runner.invoke(app, ["--format", "json", "data", "paths"])

        assert result.exit_code == 0
        data = json.loads(result.output)

        assert data["data_sources"]["models.yaml"]["source"] == "User Data"
        assert data["data_sources"]["overrides.yaml"]["source"] == "User Data"


class TestExitCodes:
    """Test CLI exit codes."""

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_check_up_to_date_exit_code(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update check returns 0 when up to date."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        mock_result = Mock()
        mock_result.success = True
        mock_result.status = Mock()
        mock_result.status.value = "already_current"
        mock_result.message = "Already up to date"

        mock_registry.check_for_updates.return_value = mock_result
        mock_registry.get_update_info.return_value = Mock(current_version="1.0.0", latest_version="1.0.0")

        result = cli_runner.invoke(app, ["update", "check"])

        assert result.exit_code == ExitCode.SUCCESS

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_check_available_exit_code(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update check returns 10 when update available."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        mock_result = Mock()
        mock_result.success = False
        mock_result.status = Mock()
        mock_result.status.value = "update_available"
        mock_result.message = "Update available"

        mock_registry.check_for_updates.return_value = mock_result
        mock_registry.get_update_info.return_value = Mock(current_version="1.0.0", latest_version="1.1.0")

        result = cli_runner.invoke(app, ["update", "check"])

        assert result.exit_code == ExitCode.UPDATE_AVAILABLE

    @patch("openai_model_registry.cli.commands.models.ModelRegistry")
    def test_model_not_found_exit_code(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test model not found returns appropriate exit code."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry
        mock_registry.dump_effective.return_value = {"models": {}}

        result = cli_runner.invoke(app, ["models", "get", "nonexistent-model"])

        assert result.exit_code == ExitCode.MODEL_NOT_FOUND


class TestUpdateFlows:
    """Test update command flows."""

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_apply_success(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test successful update apply."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry
        mock_registry.update_data.return_value = True

        result = cli_runner.invoke(app, ["--format", "json", "update", "apply"])

        assert result.exit_code == ExitCode.SUCCESS
        data = json.loads(result.output)
        assert data["success"] is True

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_apply_with_url(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update apply with URL override."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        mock_result = Mock()
        mock_result.success = True
        mock_result.message = "Updated from custom URL"

        mock_registry.refresh_from_remote.return_value = mock_result

        result = cli_runner.invoke(app, ["--format", "json", "update", "apply", "--url", "https://example.com/data"])

        assert result.exit_code == ExitCode.SUCCESS
        data = json.loads(result.output)
        assert data["success"] is True

        # Verify URL was passed to refresh_from_remote
        mock_registry.refresh_from_remote.assert_called_once()
        call_args = mock_registry.refresh_from_remote.call_args
        assert call_args[1]["url"] == "https://example.com/data"

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_refresh_validate_only(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update refresh with validate-only flag."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        mock_result = Mock()
        mock_result.success = True
        mock_result.status = Mock()
        mock_result.status.value = "validated"
        mock_result.message = "Validation successful"

        mock_registry.refresh_from_remote.return_value = mock_result

        result = cli_runner.invoke(app, ["update", "refresh", "--validate-only"])

        assert result.exit_code == ExitCode.SUCCESS

        # Verify validate_only was passed
        mock_registry.refresh_from_remote.assert_called_once()
        call_args = mock_registry.refresh_from_remote.call_args
        assert call_args[1]["validate_only"] is True


class TestModelsCommands:
    """Test models command functionality."""

    @patch("openai_model_registry.cli.commands.models.ModelRegistry")
    def test_models_list_with_filter(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test models list with filtering."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry
        mock_registry.dump_effective.return_value = {
            "models": {
                "gpt-4o": {"supports_vision": True, "pricing": {"input_cost_per_unit": 2.50}},
                "gpt-3.5-turbo": {"supports_vision": False, "pricing": {"input_cost_per_unit": 0.50}},
            }
        }

        result = cli_runner.invoke(app, ["--format", "json", "models", "list", "--filter", "supports_vision:true"])

        assert result.exit_code == ExitCode.SUCCESS
        data = json.loads(result.output)

        # Should only return gpt-4o
        assert len(data["models"]) == 1
        assert data["models"][0]["name"] == "gpt-4o"

    @patch("openai_model_registry.cli.commands.models.ModelRegistry")
    def test_models_list_with_columns(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test models list with custom columns."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry
        mock_registry.dump_effective.return_value = {
            "models": {"gpt-4o": {"supports_vision": True, "pricing": {"input_cost_per_unit": 2.50}}}
        }

        result = cli_runner.invoke(app, ["--format", "csv", "models", "list", "--columns", "name,supports_vision"])

        assert result.exit_code == ExitCode.SUCCESS
        lines = result.output.strip().split("\n")

        # Check CSV header
        assert "name,supports_vision" in lines[0]
        # Check data row
        assert "gpt-4o" in lines[1]

    @patch("openai_model_registry.cli.commands.models.ModelRegistry")
    def test_models_get_parameters_only(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test models get --parameters-only outputs only parameters."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry
        # Effective capabilities inline parameters
        mock_registry.dump_effective.return_value = {"models": {"gpt-4o": {}}}
        mock_cap = Mock()
        mock_cap.context_window = 128000
        mock_cap.max_output_tokens = 4096
        mock_cap.supports_vision = True
        mock_cap.supports_streaming = True
        mock_cap.pricing = Mock(
            scheme="per_token", unit="million_tokens", input_cost_per_unit=2.5, output_cost_per_unit=10.0
        )
        mock_cap.inline_parameters = {
            "temperature": {"type": "number", "min": 0.0, "max": 2.0},
            "top_p": {"type": "number", "min": 0.0, "max": 1.0},
        }
        mock_registry.get_capabilities.return_value = mock_cap

        result = cli_runner.invoke(app, ["--format", "json", "models", "get", "gpt-4o", "--parameters-only"])

        assert result.exit_code == ExitCode.SUCCESS
        data = json.loads(result.output)
        assert "temperature" in data and "top_p" in data
        # Ensure other top-level fields are not present
        assert "context_window" not in data
        assert "pricing" not in data


class TestCacheCommands:
    """Test cache command functionality."""

    @patch("openai_model_registry.cli.commands.cache.ModelRegistry")
    def test_cache_clear_requires_yes(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test cache clear requires --yes flag."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        with patch("openai_model_registry.cli.commands.cache.get_cache_info") as mock_cache_info:
            mock_cache_info.return_value = {
                "directory": "/fake/cache",
                "files": [{"name": "models.yaml", "size": 1000}],
            }

            # Test without --yes flag (should prompt and fail in non-interactive)
            cli_runner.invoke(app, ["cache", "clear"], input="n\n")

            # Should not call clear_cache
            mock_registry.clear_cache.assert_not_called()

    @patch("openai_model_registry.cli.commands.cache.ModelRegistry")
    def test_cache_clear_with_yes(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test cache clear with --yes flag."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        with patch("openai_model_registry.cli.commands.cache.get_cache_info") as mock_cache_info:
            mock_cache_info.side_effect = [
                # Before clearing
                {"directory": "/fake/cache", "files": [{"name": "models.yaml", "size": 1000}]},
                # After clearing
                {"directory": "/fake/cache", "files": []},
            ]

            result = cli_runner.invoke(app, ["--format", "json", "cache", "clear", "--yes"])

            assert result.exit_code == ExitCode.SUCCESS
            mock_registry.clear_cache.assert_called_once()

            data = json.loads(result.output)
            assert data["success"] is True
            assert "models.yaml" in data["files_removed"]


class TestOutputFormats:
    """Test output format handling."""

    @patch("openai_model_registry.cli.commands.providers.ModelRegistry")
    def test_non_tty_defaults_to_json(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test non-TTY output defaults to JSON format."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry
        mock_registry.list_providers.return_value = ["openai", "azure"]

        # Simulate non-TTY
        with patch("sys.stdout.isatty", return_value=False):
            result = cli_runner.invoke(app, ["providers", "list"])

        assert result.exit_code == ExitCode.SUCCESS
        # Should be valid JSON
        data = json.loads(result.output)
        assert "providers" in data
        assert "current" in data


class TestFormatEdgeCases:
    """Test format handling edge cases."""

    @patch("openai_model_registry.cli.commands.models.ModelRegistry")
    def test_models_get_yaml_format(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test models get with YAML format."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry
        mock_registry.get_raw_model_data.return_value = {
            "name": "gpt-4o",
            "context_window": {"total": 128000, "output": 4096},
            "pricing": {
                "scheme": "per_token",
                "unit": "million_tokens",
                "input_cost_per_unit": 2.50,
                "output_cost_per_unit": 10.00,
            },
            "supports_vision": True,
            "metadata": {"source": "raw", "provider_applied": None},
        }

        result = cli_runner.invoke(app, ["--format", "yaml", "models", "get", "gpt-4o", "--raw"])

        assert result.exit_code == ExitCode.SUCCESS
        # Should contain YAML formatting
        assert "name: gpt-4o" in result.output
        assert "context_window:" in result.output
        assert "pricing:" in result.output

    @patch("openai_model_registry.cli.commands.data.ModelRegistry")
    def test_data_dump_unsupported_format_error(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test data dump with unsupported format shows error."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        result = cli_runner.invoke(app, ["--format", "csv", "data", "dump"])

        assert result.exit_code == ExitCode.INVALID_USAGE
        assert "not supported" in result.output.lower()
        assert "csv" in result.output.lower()
        assert "json" in result.output.lower() or "yaml" in result.output.lower()

    @patch("openai_model_registry.cli.commands.data.ModelRegistry")
    def test_data_dump_table_format_error(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test data dump with table format shows error."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        result = cli_runner.invoke(app, ["--format", "table", "data", "dump"])

        assert result.exit_code == ExitCode.INVALID_USAGE
        assert "not supported" in result.output.lower()
        assert "table" in result.output.lower()


class TestErrorHandling:
    """Test error handling and error messages."""

    def test_invalid_provider_error(self, cli_runner: CliRunner) -> None:
        """Test invalid provider shows helpful error."""
        result = cli_runner.invoke(app, ["--provider", "invalid", "providers", "current"])

        assert result.exit_code == ExitCode.INVALID_USAGE
        assert "invalid" in result.output.lower()
        assert "openai" in result.output or "azure" in result.output

    @patch("openai_model_registry.cli.commands.data.ModelRegistry")
    def test_data_source_error_handling(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test data source errors are handled gracefully."""
        mock_registry_class.get_default.side_effect = Exception("Data source unavailable")

        result = cli_runner.invoke(app, ["data", "paths"])

        assert result.exit_code == ExitCode.DATA_SOURCE_ERROR
        assert "error" in result.output.lower()


if __name__ == "__main__":
    pytest.main([__file__])
