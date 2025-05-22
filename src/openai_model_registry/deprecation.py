"""Deprecation support for model registry.

This module provides deprecation metadata and validation for models.
"""

import warnings
from dataclasses import dataclass
from datetime import date
from typing import Dict, Literal, Optional


@dataclass(frozen=True)
class DeprecationInfo:
    """Deprecation metadata for a model.

    All fields are mandatory in schema v2.
    """

    status: Literal["active", "deprecated", "sunset"]
    deprecates_on: Optional[date]
    sunsets_on: Optional[date]
    replacement: Optional[str]
    migration_guide: Optional[str]
    reason: str

    def __post_init__(self) -> None:
        """Validate deprecation dates are properly ordered."""
        if (
            self.deprecates_on is not None
            and self.sunsets_on is not None
            and self.deprecates_on > self.sunsets_on
        ):
            raise ValueError(
                f"deprecates_on ({self.deprecates_on}) must be <= sunsets_on ({self.sunsets_on})"
            )


class ModelSunsetError(Exception):
    """Raised when attempting to access a sunset model."""

    def __init__(self, model: str, sunset_date: date):
        self.model = model
        self.sunset_date = sunset_date
        super().__init__(
            f"Model '{model}' has been sunset as of {sunset_date}. "
            f"It is no longer available for use."
        )


class InvalidSchemaVersionError(Exception):
    """Raised when the schema version is not supported."""

    def __init__(
        self, found_version: Optional[str], expected_version: str = "2"
    ):
        self.found_version = found_version
        self.expected_version = expected_version
        super().__init__(
            f"Invalid schema version: found {found_version}, expected {expected_version}"
        )


def assert_model_active(model: str, deprecation_info: DeprecationInfo) -> None:
    """Assert that a model is active and warn if deprecated.

    Args:
        model: Model name
        deprecation_info: Deprecation metadata

    Raises:
        ModelSunsetError: If the model is sunset

    Warns:
        DeprecationWarning: If the model is deprecated
    """
    if deprecation_info.status == "sunset":
        if deprecation_info.sunsets_on is None:
            raise ValueError(f"Sunset model '{model}' missing sunset date")
        raise ModelSunsetError(model, deprecation_info.sunsets_on)

    if deprecation_info.status == "deprecated":
        sunset_date = (
            deprecation_info.sunsets_on.isoformat()
            if deprecation_info.sunsets_on is not None
            else "unknown date"
        )
        warnings.warn(
            f"{model} is deprecated; will sunset {sunset_date}",
            DeprecationWarning,
            stacklevel=2,
        )


def sunset_headers(deprecation_info: DeprecationInfo) -> Dict[str, str]:
    """Generate RFC-compliant HTTP headers for deprecation status.

    Args:
        deprecation_info: Deprecation metadata

    Returns:
        Dictionary of HTTP headers
    """
    if deprecation_info.status == "active":
        return {}

    headers: Dict[str, str] = {}

    if deprecation_info.deprecates_on is not None:
        headers[
            "Deprecation"
        ] = deprecation_info.deprecates_on.isoformat()  # RFC 9745 §3

    if deprecation_info.sunsets_on is not None:
        headers[
            "Sunset"
        ] = deprecation_info.sunsets_on.isoformat()  # RFC 8594 §2

    if deprecation_info.migration_guide:
        headers[
            "Link"
        ] = f'<{deprecation_info.migration_guide}>; rel="deprecation"'

    return headers
