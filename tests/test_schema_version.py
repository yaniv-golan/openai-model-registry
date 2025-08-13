"""Tests for schema version validation and compatibility checking."""

from typing import Any, Dict
from unittest.mock import patch

import pytest

from openai_model_registry.schema_version import SchemaVersionValidator


class TestSchemaVersionValidator:
    """Test suite for SchemaVersionValidator class."""

    def test_get_schema_version_valid(self) -> None:
        """Test getting valid schema version from config data."""
        config_data: Dict[str, Any] = {"version": "1.0.0", "models": {}}
        version = SchemaVersionValidator.get_schema_version(config_data)
        assert version == "1.0.0"

    def test_get_schema_version_missing_uses_default(self) -> None:
        """Test that missing version uses default with warning."""
        config_data: Dict[str, Any] = {"models": {}}
        with patch("openai_model_registry.schema_version.log_warning") as mock_log:
            version = SchemaVersionValidator.get_schema_version(config_data)
            assert version == "1.0.0"
            mock_log.assert_called_once()

    def test_get_schema_version_empty_uses_default(self) -> None:
        """Test that empty version uses default with warning."""
        config_data: Dict[str, Any] = {"version": "", "models": {}}
        with patch("openai_model_registry.schema_version.log_warning") as mock_log:
            version = SchemaVersionValidator.get_schema_version(config_data)
            assert version == "1.0.0"
            mock_log.assert_called_once()

    def test_get_schema_version_invalid_format(self) -> None:
        """Test that invalid version format raises ValueError."""
        config_data: Dict[str, Any] = {"version": "invalid.version", "models": {}}
        with pytest.raises(ValueError, match="Invalid schema version format"):
            SchemaVersionValidator.get_schema_version(config_data)

    def test_get_schema_version_non_string_converted(self) -> None:
        """Test that non-string version is converted to string and normalized."""
        config_data: Dict[str, Any] = {"version": 1.0, "models": {}}
        version = SchemaVersionValidator.get_schema_version(config_data)
        assert version == "1.0.0"  # Normalized to proper semver format

    def test_is_compatible_schema_valid_1x(self) -> None:
        """Test compatibility check for valid 1.x versions."""
        assert SchemaVersionValidator.is_compatible_schema("1.0.0") is True
        assert SchemaVersionValidator.is_compatible_schema("1.0.1") is True
        assert SchemaVersionValidator.is_compatible_schema("1.1.0") is True
        assert SchemaVersionValidator.is_compatible_schema("1.9.9") is True

    def test_is_compatible_schema_invalid_versions(self) -> None:
        """Test compatibility check for invalid versions."""
        assert SchemaVersionValidator.is_compatible_schema("0.9.9") is False
        assert SchemaVersionValidator.is_compatible_schema("2.0.0") is False
        assert SchemaVersionValidator.is_compatible_schema("3.0.0") is False

    def test_is_compatible_schema_malformed(self) -> None:
        """Test compatibility check for malformed versions."""
        assert SchemaVersionValidator.is_compatible_schema("invalid") is False
        assert SchemaVersionValidator.is_compatible_schema("1.x.y") is False
        assert SchemaVersionValidator.is_compatible_schema("") is False

    def test_get_compatible_range_valid(self) -> None:
        """Test getting compatible range for valid versions."""
        assert SchemaVersionValidator.get_compatible_range("1.0.0") == "1.x"
        assert SchemaVersionValidator.get_compatible_range("1.5.2") == "1.x"

    def test_get_compatible_range_invalid(self) -> None:
        """Test getting compatible range for invalid versions."""
        assert SchemaVersionValidator.get_compatible_range("2.0.0") is None
        assert SchemaVersionValidator.get_compatible_range("0.9.9") is None
        assert SchemaVersionValidator.get_compatible_range("invalid") is None

    def test_validate_schema_structure_valid_1x(self) -> None:
        """Test structure validation for valid 1.x schema."""
        config_data: Dict[str, Any] = {"version": "1.0.0", "models": {}}
        assert SchemaVersionValidator.validate_schema_structure(config_data, "1.0.0") is True

    def test_validate_schema_structure_missing_version(self) -> None:
        """Test structure validation fails when version is missing."""
        config_data: Dict[str, Any] = {"models": {}}
        with patch("openai_model_registry.schema_version.log_error") as mock_log:
            result = SchemaVersionValidator.validate_schema_structure(config_data, "1.0.0")
            assert result is False
            mock_log.assert_called_once()

    def test_validate_schema_structure_missing_models(self) -> None:
        """Test structure validation fails when models is missing."""
        config_data: Dict[str, Any] = {"version": "1.0.0"}
        with patch("openai_model_registry.schema_version.log_error") as mock_log:
            result = SchemaVersionValidator.validate_schema_structure(config_data, "1.0.0")
            assert result is False
            mock_log.assert_called_once()

    def test_validate_schema_structure_unsupported_version(self) -> None:
        """Test structure validation fails for unsupported versions."""
        config_data: Dict[str, Any] = {"version": "2.0.0", "models": {}}
        assert SchemaVersionValidator.validate_schema_structure(config_data, "2.0.0") is False

    def test_validate_schema_structure_malformed_version(self) -> None:
        """Test structure validation fails for malformed versions."""
        config_data: Dict[str, Any] = {"version": "1.0.0", "models": {}}
        assert SchemaVersionValidator.validate_schema_structure(config_data, "invalid") is False

    def test_get_loader_method_name_valid_1x(self) -> None:
        """Test getting loader method name for valid 1.x versions."""
        assert SchemaVersionValidator.get_loader_method_name("1.0.0") == "_load_capabilities_modern"
        assert SchemaVersionValidator.get_loader_method_name("1.5.2") == "_load_capabilities_modern"

    def test_get_loader_method_name_unsupported(self) -> None:
        """Test getting loader method name for unsupported versions."""
        assert SchemaVersionValidator.get_loader_method_name("2.0.0") is None
        assert SchemaVersionValidator.get_loader_method_name("0.9.9") is None

    def test_get_loader_method_name_malformed(self) -> None:
        """Test getting loader method name for malformed versions."""
        assert SchemaVersionValidator.get_loader_method_name("invalid") is None

    def test_supported_schema_versions_constant(self) -> None:
        """Test that supported schema versions constant is properly defined."""
        versions: Dict[str, str] = SchemaVersionValidator.SUPPORTED_SCHEMA_VERSIONS
        assert isinstance(versions, dict)
        assert "1.x" in versions
        assert versions["1.x"] == ">=1.0.0,<2.0.0"

    def test_default_schema_version_constant(self) -> None:
        """Test that default schema version constant is properly defined."""
        assert SchemaVersionValidator.DEFAULT_SCHEMA_VERSION == "1.0.0"


class TestSchemaVersionEdgeCases:
    """Test edge cases and error conditions for schema version validation."""

    def test_semver_import_error_handling(self) -> None:
        """Test graceful handling when semver is not available."""
        with patch("openai_model_registry.schema_version.semver", None):
            # This should still work for basic cases if semver is mocked properly
            # The actual behavior depends on implementation details
            pass

    def test_prerelease_versions(self) -> None:
        """Test handling of pre-release versions."""
        # Pre-release versions should be handled according to semver rules
        assert SchemaVersionValidator.is_compatible_schema("1.0.0-alpha") is True
        assert SchemaVersionValidator.is_compatible_schema("1.0.0-beta.1") is True
        assert SchemaVersionValidator.is_compatible_schema("1.0.0-rc.1") is True

    def test_build_metadata_versions(self) -> None:
        """Test handling of versions with build metadata."""
        # Build metadata should be ignored according to semver rules
        assert SchemaVersionValidator.is_compatible_schema("1.0.0+build.1") is True
        assert SchemaVersionValidator.is_compatible_schema("1.0.0+20130313144700") is True

    def test_version_with_leading_v(self) -> None:
        """Test handling of versions with leading 'v'."""
        # Leading 'v' should be handled gracefully
        config_data: Dict[str, Any] = {"version": "v1.0.0", "models": {}}
        with pytest.raises(ValueError):
            # This should fail because 'v1.0.0' is not valid semver
            SchemaVersionValidator.get_schema_version(config_data)

    def test_extremely_long_version(self) -> None:
        """Test handling of extremely long version strings."""
        long_version: str = "1.0.0-" + "a" * 1000
        config_data: Dict[str, Any] = {"version": long_version, "models": {}}
        # Should handle gracefully without crashing
        try:
            SchemaVersionValidator.get_schema_version(config_data)
        except ValueError:
            # This is acceptable - invalid format
            pass

    def test_unicode_version(self) -> None:
        """Test handling of unicode characters in version."""
        config_data: Dict[str, Any] = {"version": "1.0.0-αβγ", "models": {}}
        with pytest.raises(ValueError):
            SchemaVersionValidator.get_schema_version(config_data)

    def test_numeric_version_object(self) -> None:
        """Test handling of numeric version objects."""
        config_data: Dict[str, Any] = {"version": {"major": 1, "minor": 0, "patch": 0}, "models": {}}
        # Should convert to string and likely fail validation
        with pytest.raises(ValueError):
            SchemaVersionValidator.get_schema_version(config_data)
