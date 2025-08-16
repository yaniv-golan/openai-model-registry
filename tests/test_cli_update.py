"""Tests for CLI update commands."""

import json
import os
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from openai_model_registry.cli.app import app


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


class TestUpdateCheck:
    """Test update check command."""

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_check_up_to_date(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update check when up to date."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock check result - up to date
        mock_result = Mock()
        mock_result.status.value = "already_current"
        mock_result.message = "Registry is up to date"
        mock_registry.check_for_updates.return_value = mock_result

        # Mock update info
        mock_update_info = Mock()
        mock_update_info.current_version = "1.0.0"
        mock_update_info.latest_version = "1.0.0"
        mock_registry.get_update_info.return_value = mock_update_info

        result = cli_runner.invoke(app, ["update", "check"])

        assert result.exit_code == 0
        assert "up to date" in result.output.lower()
        mock_registry.check_for_updates.assert_called_once_with(None)

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_check_available(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update check when update is available."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock check result - update available
        mock_result = Mock()
        mock_result.status.value = "update_available"
        mock_result.message = "Update available"
        mock_registry.check_for_updates.return_value = mock_result

        # Mock update info
        mock_update_info = Mock()
        mock_update_info.current_version = "1.0.0"
        mock_update_info.latest_version = "1.1.0"
        mock_registry.get_update_info.return_value = mock_update_info

        result = cli_runner.invoke(app, ["update", "check"])

        assert result.exit_code == 10  # CI-friendly exit code for update available
        assert "1.0.0" in result.output
        assert "1.1.0" in result.output

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_check_with_url(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update check with custom URL."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock check result
        mock_result = Mock()
        mock_result.status.value = "already_current"
        mock_result.message = "Registry is up to date"
        mock_registry.check_for_updates.return_value = mock_result

        # Mock update info
        mock_update_info = Mock()
        mock_update_info.current_version = "1.0.0"
        mock_update_info.latest_version = "1.0.0"
        mock_registry.get_update_info.return_value = mock_update_info

        custom_url = "https://example.com/data"
        result = cli_runner.invoke(app, ["update", "check", "--url", custom_url])

        assert result.exit_code == 0
        mock_registry.check_for_updates.assert_called_once_with(custom_url)

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_check_json_format(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update check with JSON format."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock check result
        mock_result = Mock()
        mock_result.status.value = "update_available"
        mock_result.message = "Update available"
        mock_registry.check_for_updates.return_value = mock_result

        # Mock update info
        mock_update_info = Mock()
        mock_update_info.current_version = "1.0.0"
        mock_update_info.latest_version = "1.1.0"
        mock_registry.get_update_info.return_value = mock_update_info

        result = cli_runner.invoke(app, ["--format", "json", "update", "check"])

        assert result.exit_code == 10
        output_data = json.loads(result.output)
        assert output_data["update_available"] is True
        assert output_data["current_version"] == "1.0.0"
        assert output_data["latest_version"] == "1.1.0"
        assert output_data["status"] == "update_available"

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_check_error_handling(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update check error handling."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Simulate error
        mock_registry.check_for_updates.side_effect = Exception("Network error")

        result = cli_runner.invoke(app, ["update", "check"])

        assert result.exit_code != 0
        assert "Error" in result.output


class TestUpdateApply:
    """Test update apply command."""

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_apply_success(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test successful update apply."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock update success
        mock_registry.update_data.return_value = True

        # Mock update info before and after
        mock_update_info_before = Mock()
        mock_update_info_before.current_version = "1.0.0"
        mock_update_info_after = Mock()
        mock_update_info_after.current_version = "1.1.0"
        mock_registry.get_update_info.side_effect = [mock_update_info_before, mock_update_info_after]

        result = cli_runner.invoke(app, ["update", "apply"])

        assert result.exit_code == 0
        assert "successfully" in result.output.lower()
        mock_registry.update_data.assert_called_once_with(force=False)

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_apply_with_force(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update apply with force flag."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock update success
        mock_registry.update_data.return_value = True

        # Mock update info
        mock_update_info = Mock()
        mock_update_info.current_version = "1.0.0"
        mock_registry.get_update_info.return_value = mock_update_info

        result = cli_runner.invoke(app, ["update", "apply", "--force"])

        assert result.exit_code == 0
        mock_registry.update_data.assert_called_once_with(force=True)

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_apply_with_url(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update apply with custom URL."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock refresh result
        mock_result = Mock()
        mock_result.success = True
        mock_result.message = "Update completed"
        mock_registry.refresh_from_remote.return_value = mock_result

        # Mock update info
        mock_update_info = Mock()
        mock_update_info.current_version = "1.0.0"
        mock_registry.get_update_info.return_value = mock_update_info

        custom_url = "https://example.com/data"
        result = cli_runner.invoke(app, ["update", "apply", "--url", custom_url])

        assert result.exit_code == 0
        mock_registry.refresh_from_remote.assert_called_once_with(url=custom_url, force=False)

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_apply_failure(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update apply failure."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock update failure
        mock_registry.update_data.return_value = False

        # Mock update info
        mock_update_info = Mock()
        mock_update_info.current_version = "1.0.0"
        mock_registry.get_update_info.return_value = mock_update_info

        result = cli_runner.invoke(app, ["update", "apply"])

        assert result.exit_code != 0
        assert "failed" in result.output.lower()

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_apply_json_format(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update apply with JSON format."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock update success
        mock_registry.update_data.return_value = True

        # Mock update info
        mock_update_info_before = Mock()
        mock_update_info_before.current_version = "1.0.0"
        mock_update_info_after = Mock()
        mock_update_info_after.current_version = "1.1.0"
        mock_registry.get_update_info.side_effect = [mock_update_info_before, mock_update_info_after]

        result = cli_runner.invoke(app, ["--format", "json", "update", "apply"])

        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert output_data["success"] is True
        assert output_data["version_before"] == "1.0.0"
        assert output_data["version_after"] == "1.1.0"

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_apply_error_handling(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update apply error handling."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Simulate error
        mock_registry.update_data.side_effect = Exception("Update error")

        result = cli_runner.invoke(app, ["update", "apply"])

        assert result.exit_code != 0
        assert "Error" in result.output


class TestUpdateRefresh:
    """Test update refresh command."""

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_refresh_success(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test successful update refresh."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock refresh result
        mock_result = Mock()
        mock_result.success = True
        mock_result.status.value = "updated"
        mock_result.message = "Refresh completed"
        mock_registry.refresh_from_remote.return_value = mock_result

        # Mock update info
        mock_update_info_before = Mock()
        mock_update_info_before.current_version = "1.0.0"
        mock_update_info_after = Mock()
        mock_update_info_after.current_version = "1.1.0"
        mock_registry.get_update_info.side_effect = [mock_update_info_before, mock_update_info_after]

        result = cli_runner.invoke(app, ["update", "refresh"])

        assert result.exit_code == 0
        assert "completed" in result.output.lower() or "success" in result.output.lower()
        mock_registry.refresh_from_remote.assert_called_once_with(url=None, force=False, validate_only=False)

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_refresh_validate_only(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update refresh with validate-only flag."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock refresh result
        mock_result = Mock()
        mock_result.success = True
        mock_result.status.value = "validated"
        mock_result.message = "Validation successful"
        mock_registry.refresh_from_remote.return_value = mock_result

        # Mock update info
        mock_update_info = Mock()
        mock_update_info.current_version = "1.0.0"
        mock_registry.get_update_info.return_value = mock_update_info

        result = cli_runner.invoke(app, ["update", "refresh", "--validate-only"])

        assert result.exit_code == 0
        mock_registry.refresh_from_remote.assert_called_once_with(url=None, force=False, validate_only=True)

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_refresh_with_url_and_force(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update refresh with URL and force flags."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock refresh result
        mock_result = Mock()
        mock_result.success = True
        mock_result.status.value = "updated"
        mock_result.message = "Forced refresh completed"
        mock_registry.refresh_from_remote.return_value = mock_result

        # Mock update info
        mock_update_info = Mock()
        mock_update_info.current_version = "1.0.0"
        mock_registry.get_update_info.return_value = mock_update_info

        custom_url = "https://example.com/data"
        result = cli_runner.invoke(app, ["update", "refresh", "--url", custom_url, "--force"])

        assert result.exit_code == 0
        mock_registry.refresh_from_remote.assert_called_once_with(url=custom_url, force=True, validate_only=False)

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_refresh_json_format(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update refresh with JSON format."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock refresh result
        mock_result = Mock()
        mock_result.success = True
        mock_result.status.value = "updated"
        mock_result.message = "Refresh completed"
        mock_registry.refresh_from_remote.return_value = mock_result

        # Mock update info
        mock_update_info_before = Mock()
        mock_update_info_before.current_version = "1.0.0"
        mock_update_info_after = Mock()
        mock_update_info_after.current_version = "1.1.0"
        mock_registry.get_update_info.side_effect = [mock_update_info_before, mock_update_info_after]

        result = cli_runner.invoke(app, ["--format", "json", "update", "refresh"])

        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert output_data["success"] is True
        assert output_data["status"] == "updated"
        assert output_data["validate_only"] is False
        assert output_data["version_before"] == "1.0.0"
        assert output_data["version_after"] == "1.1.0"

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_refresh_failure(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update refresh failure."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock refresh failure
        mock_result = Mock()
        mock_result.success = False
        mock_result.status.value = "failed"
        mock_result.message = "Refresh failed"
        mock_registry.refresh_from_remote.return_value = mock_result

        # Mock update info
        mock_update_info = Mock()
        mock_update_info.current_version = "1.0.0"
        mock_registry.get_update_info.return_value = mock_update_info

        result = cli_runner.invoke(app, ["update", "refresh"])

        assert result.exit_code != 0

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_refresh_error_handling(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update refresh error handling."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Simulate error
        mock_registry.refresh_from_remote.side_effect = Exception("Refresh error")

        result = cli_runner.invoke(app, ["update", "refresh"])

        assert result.exit_code != 0
        assert "Error" in result.output


class TestUpdateShowConfig:
    """Test update show-config command."""

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_show_config_basic(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update show-config command."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock data info
        mock_registry.get_data_info.return_value = {
            "user_data_dir": "/fake/user/data",
            "current_version": "1.0.0",
        }

        result = cli_runner.invoke(app, ["update", "show-config"])

        assert result.exit_code == 0
        # The output is JSON by default, so check for JSON structure
        output_data = json.loads(result.output)
        assert "data_directory" in output_data
        assert output_data["data_directory"] == "/fake/user/data"
        mock_registry.get_data_info.assert_called_once()

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_show_config_with_env_vars(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update show-config with environment variables set."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock data info
        mock_registry.get_data_info.return_value = {
            "user_data_dir": "/fake/user/data",
        }

        # Set test environment variables
        test_env = {
            "OMR_DISABLE_DATA_UPDATES": "true",
            "OMR_DATA_VERSION_PIN": "1.0.0",
            "OMR_DATA_DIR": "/custom/data",
            "OMR_MODEL_REGISTRY_PATH": "/custom/models.yaml",
        }

        with patch.dict(os.environ, test_env, clear=False):
            result = cli_runner.invoke(app, ["update", "show-config"])

            assert result.exit_code == 0
            assert "OMR_DISABLE_DATA_UPDATES" in result.output
            assert "true" in result.output
            assert "OMR_DATA_VERSION_PIN" in result.output
            assert "1.0.0" in result.output

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_show_config_json_format(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update show-config with JSON format."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock data info
        mock_registry.get_data_info.return_value = {
            "user_data_dir": "/fake/user/data",
        }

        test_env = {
            "OMR_DISABLE_DATA_UPDATES": "true",
            "OMR_DATA_VERSION_PIN": "1.0.0",
        }

        with patch.dict(os.environ, test_env, clear=False):
            result = cli_runner.invoke(app, ["--format", "json", "update", "show-config"])

            assert result.exit_code == 0
            output_data = json.loads(result.output)
            assert "data_directory" in output_data
            assert "environment_variables" in output_data
            assert "update_settings" in output_data
            assert output_data["environment_variables"]["OMR_DISABLE_DATA_UPDATES"] == "true"
            assert output_data["update_settings"]["updates_disabled"] is True
            assert output_data["update_settings"]["version_pinned"] is True

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_show_config_no_env_vars(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update show-config with no environment variables set."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Mock data info
        mock_registry.get_data_info.return_value = {
            "user_data_dir": "/fake/user/data",
        }

        # Clear OMR environment variables
        omr_vars = [key for key in os.environ.keys() if key.startswith("OMR_")]

        # Save original values and remove them temporarily
        original_values = {var: os.environ.get(var) for var in omr_vars}
        for var in omr_vars:
            if var in os.environ:
                del os.environ[var]

        try:
            result = cli_runner.invoke(app, ["--format", "json", "update", "show-config"])

            assert result.exit_code == 0
            output_data = json.loads(result.output)
            assert output_data["update_settings"]["updates_disabled"] is False
            assert output_data["update_settings"]["version_pinned"] is False
            assert output_data["update_settings"]["custom_data_dir"] is False
            assert output_data["update_settings"]["custom_registry_path"] is False
        finally:
            # Restore original environment variables
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value

    @patch("openai_model_registry.cli.commands.update.ModelRegistry")
    def test_update_show_config_error_handling(self, mock_registry_class: MagicMock, cli_runner: CliRunner) -> None:
        """Test update show-config error handling."""
        mock_registry = Mock()
        mock_registry_class.get_default.return_value = mock_registry

        # Simulate error
        mock_registry.get_data_info.side_effect = Exception("Data info error")

        result = cli_runner.invoke(app, ["update", "show-config"])

        assert result.exit_code != 0
        assert "Error" in result.output
