"""Tests for the update_registry script."""

from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest

from openai_model_registry.errors import (
    ModelNotSupportedError,
    ModelVersionError,
)
from openai_model_registry.registry import RefreshResult, RefreshStatus
from openai_model_registry.scripts.update_registry import refresh_registry


@pytest.fixture
def mock_registry() -> Generator[MagicMock, None, None]:
    """Mock the ModelRegistry for testing."""
    with patch(
        "openai_model_registry.scripts.update_registry.ModelRegistry"
    ) as mock:
        registry_instance = MagicMock()
        mock.get_instance.return_value = registry_instance
        yield registry_instance


class TestRefreshRegistry:
    """Tests for the refresh_registry function."""

    def test_validate_success(
        self, mock_registry: MagicMock, capsys: Any
    ) -> None:
        """Test validation mode when successful."""
        result = refresh_registry(validate=True)

        # Check that the function loaded capabilities
        mock_registry._load_capabilities.assert_called_once()

        # Check output
        captured = capsys.readouterr()
        assert "✅ Config validation successful" in captured.out
        assert result == 0

    def test_validate_verbose(
        self, mock_registry: MagicMock, capsys: Any
    ) -> None:
        """Test validation mode with verbose output."""
        mock_registry.config.registry_path = "/path/to/registry"

        result = refresh_registry(validate=True, verbose=True)

        # Check output
        captured = capsys.readouterr()
        assert "✅ Config validation successful" in captured.out
        assert "Local registry file: /path/to/registry" in captured.out
        assert result == 0

    def test_check_only_update_available(
        self, mock_registry: MagicMock, capsys: Any
    ) -> None:
        """Test check_only mode when update is available."""
        mock_registry.check_for_updates.return_value = RefreshResult(
            success=True,
            status=RefreshStatus.UPDATE_AVAILABLE,
            message="Update available",
        )

        result = refresh_registry(check_only=True)

        # Check that the function checked for updates
        mock_registry.check_for_updates.assert_called_once_with(None)

        # Check output
        captured = capsys.readouterr()
        assert "✅ Registry update is available" in captured.out
        assert result == 0

    def test_check_only_already_current(
        self, mock_registry: MagicMock, capsys: Any
    ) -> None:
        """Test check_only mode when already current."""
        mock_registry.check_for_updates.return_value = RefreshResult(
            success=True,
            status=RefreshStatus.ALREADY_CURRENT,
            message="Already current",
        )

        result = refresh_registry(check_only=True)

        # Check output
        captured = capsys.readouterr()
        assert "✓ Registry is already up to date" in captured.out
        assert result == 0

    def test_check_only_verbose(
        self, mock_registry: MagicMock, capsys: Any
    ) -> None:
        """Test check_only mode with verbose output."""
        mock_registry.check_for_updates.return_value = RefreshResult(
            success=True,
            status=RefreshStatus.UPDATE_AVAILABLE,
            message="Update available",
        )

        result = refresh_registry(check_only=True, verbose=True)

        # Check output
        captured = capsys.readouterr()
        assert "✅ Registry update is available" in captured.out
        # Fix the assertion to match the actual output (status is lowercase)
        assert "Status: update_available" in captured.out
        assert "Message: Update available" in captured.out
        assert result == 0

    def test_check_only_error(
        self, mock_registry: MagicMock, capsys: Any
    ) -> None:
        """Test check_only mode when error occurs."""
        mock_registry.check_for_updates.return_value = RefreshResult(
            success=False, status=RefreshStatus.ERROR, message="Error occurred"
        )

        result = refresh_registry(check_only=True)

        # Check output
        captured = capsys.readouterr()
        assert "❌ Error checking for updates: Error occurred" in captured.out
        assert result == 1

    def test_update_already_current_no_force(
        self, mock_registry: MagicMock, capsys: Any
    ) -> None:
        """Test update when already current and no force flag."""
        mock_registry.check_for_updates.return_value = RefreshResult(
            success=True,
            status=RefreshStatus.ALREADY_CURRENT,
            message="Already current",
        )

        result = refresh_registry()

        # Check that refresh_from_remote was not called
        mock_registry.refresh_from_remote.assert_not_called()

        # Check output
        captured = capsys.readouterr()
        assert "✓ Registry is already up to date" in captured.out
        assert result == 0

    def test_update_success(
        self, mock_registry: MagicMock, capsys: Any
    ) -> None:
        """Test successful update."""
        mock_registry.check_for_updates.return_value = RefreshResult(
            success=True,
            status=RefreshStatus.UPDATE_AVAILABLE,
            message="Update available",
        )
        mock_registry.refresh_from_remote.return_value = RefreshResult(
            success=True,
            status=RefreshStatus.UPDATED,
            message="Updated successfully",
        )

        result = refresh_registry()

        # Check that refresh_from_remote was called
        mock_registry.refresh_from_remote.assert_called_once_with(
            url=None, force=False, validate_only=False
        )

        # Check output
        captured = capsys.readouterr()
        assert "✅ Registry updated successfully" in captured.out
        assert result == 0

    def test_update_failure(
        self, mock_registry: MagicMock, capsys: Any
    ) -> None:
        """Test failed update."""
        mock_registry.check_for_updates.return_value = RefreshResult(
            success=True,
            status=RefreshStatus.UPDATE_AVAILABLE,
            message="Update available",
        )
        mock_registry.refresh_from_remote.return_value = RefreshResult(
            success=False, status=RefreshStatus.ERROR, message="Update failed"
        )

        result = refresh_registry()

        # Check output
        captured = capsys.readouterr()
        assert "❌ Error updating registry: Update failed" in captured.out
        assert result == 1

    def test_model_not_supported_error(
        self, mock_registry: MagicMock, capsys: Any
    ) -> None:
        """Test handling of ModelNotSupportedError."""
        mock_registry.check_for_updates.side_effect = ModelNotSupportedError(
            "Model not supported", model="invalid-model"
        )

        result = refresh_registry()

        # Check output
        captured = capsys.readouterr()
        assert "❌ Invalid model:" in captured.out
        assert result == 1

    def test_model_version_error(
        self, mock_registry: MagicMock, capsys: Any
    ) -> None:
        """Test handling of ModelVersionError."""
        mock_registry.check_for_updates.side_effect = ModelVersionError(
            "Invalid version"
        )

        result = refresh_registry()

        # Check output
        captured = capsys.readouterr()
        assert "❌ Config error:" in captured.out
        assert result == 1

    def test_generic_exception(
        self, mock_registry: MagicMock, capsys: Any
    ) -> None:
        """Test handling of generic exception."""
        mock_registry.check_for_updates.side_effect = Exception(
            "Unexpected error"
        )

        result = refresh_registry()

        # Check output
        captured = capsys.readouterr()
        assert (
            "❌ Error refreshing model registry: Unexpected error"
            in captured.out
        )
        assert result == 1


# Use pytest-click or a more appropriate approach
# to test Click commands instead of direct invocation
def test_main_integration() -> None:
    """Verify that main correctly handles command line arguments."""
    with patch(
        "openai_model_registry.scripts.update_registry.refresh_registry"
    ) as mock_refresh:
        from click.testing import CliRunner

        from openai_model_registry.scripts.update_registry import main

        runner = CliRunner()
        mock_refresh.return_value = 0

        # Test basic invocation
        result = runner.invoke(main, ["--verbose", "--force"])
        assert result.exit_code == 0

        # Verify refresh_registry was called with correct args
        mock_refresh.assert_called_once_with(
            verbose=True,
            force=True,
            url=None,
            validate=False,
            check_only=False,
        )
