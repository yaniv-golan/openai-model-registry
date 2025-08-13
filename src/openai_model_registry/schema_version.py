"""Schema version validation and compatibility checking using semver."""

from typing import Any, Dict, Optional

try:
    import semver

    SEMVER_AVAILABLE = True
except ImportError:
    semver = None  # type: ignore
    SEMVER_AVAILABLE = False

from .logging import LogEvent, log_error, log_warning


class SchemaVersionValidator:
    """Handles schema version validation and compatibility checking using semver."""

    # Define supported schema version ranges
    SUPPORTED_SCHEMA_VERSIONS = {
        "1.x": ">=1.0.0,<2.0.0",
        # Future versions can be added here without legacy naming
    }

    DEFAULT_SCHEMA_VERSION = "1.0.0"

    @classmethod
    def _check_version_range(cls, version: str, range_spec: str) -> bool:
        """Check if a version satisfies a range specification.

        Args:
            version: Version string to check
            range_spec: Range specification like ">=1.0.0,<2.0.0"

        Returns:
            True if version satisfies the range
        """
        if not SEMVER_AVAILABLE or not semver:
            return False

        try:
            # Parse the version to get components
            parsed_version = semver.VersionInfo.parse(version)

            # Split range by comma and check each condition
            conditions = [cond.strip() for cond in range_spec.split(",")]

            for condition in conditions:
                # Special handling for pre-release versions with >= conditions
                if condition.startswith(">=") and parsed_version.prerelease:
                    # For pre-release versions, check if the base version (without prerelease)
                    # would satisfy the condition
                    base_version = f"{parsed_version.major}.{parsed_version.minor}.{parsed_version.patch}"
                    base_version_info = semver.VersionInfo.parse(base_version)
                    if not base_version_info.match(condition):
                        return False
                else:
                    if not parsed_version.match(condition):
                        return False
            return True
        except ValueError:
            return False

    @classmethod
    def get_schema_version(cls, config_data: Dict[str, Any]) -> str:
        """Extract and validate schema version from config data.

        Args:
            config_data: Configuration data dictionary

        Returns:
            Valid schema version string

        Raises:
            ValueError: If version is invalid
        """
        version = config_data.get("version")

        if not version:
            log_warning(
                LogEvent.MODEL_REGISTRY,
                "Missing schema version, using default",
                default_version=cls.DEFAULT_SCHEMA_VERSION,
            )
            return cls.DEFAULT_SCHEMA_VERSION

        # Ensure version is a string
        version_str = str(version)

        # Validate version format using semver
        if not SEMVER_AVAILABLE or not semver:
            log_warning(LogEvent.MODEL_REGISTRY, "semver library not available, skipping version validation")
            return version_str

        try:
            # Try to parse as-is first
            semver.VersionInfo.parse(version_str)
        except ValueError:
            # If that fails, try to normalize common formats
            try:
                # Handle formats like "1.0" -> "1.0.0"
                parts = version_str.split(".")
                if len(parts) == 2:
                    version_str = f"{parts[0]}.{parts[1]}.0"
                    semver.VersionInfo.parse(version_str)
                elif len(parts) == 1:
                    version_str = f"{parts[0]}.0.0"
                    semver.VersionInfo.parse(version_str)
                else:
                    raise ValueError(f"Cannot normalize version: {version_str}")
            except ValueError as e:
                log_error(LogEvent.MODEL_REGISTRY, "Invalid schema version format", version=version_str, error=str(e))
                raise ValueError(f"Invalid schema version format: {version_str}") from e

        return version_str

    @classmethod
    def is_compatible_schema(cls, version: str) -> bool:
        """Check if schema version is compatible with this registry.

        Args:
            version: Schema version string

        Returns:
            True if version is supported, False otherwise
        """
        if not SEMVER_AVAILABLE or not semver:
            return True  # Assume compatible if semver not available

        try:
            # Check against all supported version ranges
            for range_spec in cls.SUPPORTED_SCHEMA_VERSIONS.values():
                if cls._check_version_range(version, range_spec):
                    return True
            return False
        except ValueError:
            return False

    @classmethod
    def get_compatible_range(cls, version: str) -> Optional[str]:
        """Get the compatible version range for a given version.

        Args:
            version: Schema version string

        Returns:
            Version range string if compatible, None otherwise
        """
        if not SEMVER_AVAILABLE or not semver:
            return "1.x"  # Default range if semver not available

        try:
            for range_name, range_spec in cls.SUPPORTED_SCHEMA_VERSIONS.items():
                if cls._check_version_range(version, range_spec):
                    return range_name
            return None
        except ValueError:
            return None

    @classmethod
    def validate_schema_structure(cls, config_data: Dict[str, Any], version: str) -> bool:
        """Validate that data structure matches the declared schema version.

        Args:
            config_data: Configuration data dictionary
            version: Schema version string

        Returns:
            True if structure is valid for the version
        """
        if not SEMVER_AVAILABLE or not semver:
            # Basic validation without semver
            return "models" in config_data

        try:
            # For 1.x versions, require 'models' key
            if cls._check_version_range(version, ">=1.0.0,<2.0.0"):
                required_keys = ["version", "models"]
                missing_keys = [key for key in required_keys if key not in config_data]
                if missing_keys:
                    log_error(
                        LogEvent.MODEL_REGISTRY,
                        "Missing required keys for schema version",
                        version=version,
                        missing_keys=missing_keys,
                    )
                    return False
                return True

            # Future versions can extend here with appropriate loader methods
            return False

        except ValueError:
            return False

    @classmethod
    def get_loader_method_name(cls, version: str) -> Optional[str]:
        """Get the appropriate loader method name for a schema version.

        Args:
            version: Schema version string

        Returns:
            Method name string if version is supported, None otherwise
        """
        if not SEMVER_AVAILABLE or not semver:
            return "_load_capabilities_modern"  # Default method

        try:
            if cls._check_version_range(version, ">=1.0.0,<2.0.0"):
                return "_load_capabilities_modern"
            # Future versions can extend here with appropriate loader methods
            return None
        except ValueError:
            return None
