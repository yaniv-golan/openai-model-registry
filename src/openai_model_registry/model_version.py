"""Model version handling for OpenAI models.

This module provides utilities for parsing and comparing model versions
in the format YYYY-MM-DD.
"""

import re
from datetime import date
from typing import Tuple

from .errors import InvalidDateError, ModelFormatError


class ModelVersion:
    """Represents a model version in YYYY-MM-DD format.

    This class handles parsing, validation, and comparison of model version dates.

    Attributes:
        year: The year component of the version
        month: The month component of the version
        day: The day component of the version
    """

    def __init__(self, year: int, month: int, day: int) -> None:
        """Initialize a model version.

        Args:
            year: The year component (e.g., 2024)
            month: The month component (1-12)
            day: The day component (1-31)
        """
        self.year = year
        self.month = month
        self.day = day

    def __eq__(self, other: object) -> bool:
        """Check if two versions are equal.

        Args:
            other: The other version to compare with

        Returns:
            bool: True if versions are equal, False otherwise
        """
        if not isinstance(other, ModelVersion):
            return NotImplemented
        return (
            self.year == other.year
            and self.month == other.month
            and self.day == other.day
        )

    def __lt__(self, other: "ModelVersion") -> bool:
        """Check if this version is earlier than another.

        Args:
            other: The other version to compare with

        Returns:
            bool: True if this version is earlier, False otherwise
        """
        if self.year != other.year:
            return self.year < other.year
        if self.month != other.month:
            return self.month < other.month
        return self.day < other.day

    def __le__(self, other: "ModelVersion") -> bool:
        """Check if this version is earlier than or equal to another.

        Args:
            other: The other version to compare with

        Returns:
            bool: True if this version is earlier or equal, False otherwise
        """
        return self < other or self == other

    def __gt__(self, other: "ModelVersion") -> bool:
        """Check if this version is later than another.

        Args:
            other: The other version to compare with

        Returns:
            bool: True if this version is later, False otherwise
        """
        return not (self <= other)

    def __ge__(self, other: "ModelVersion") -> bool:
        """Check if this version is later than or equal to another.

        Args:
            other: The other version to compare with

        Returns:
            bool: True if this version is later or equal, False otherwise
        """
        return not (self < other)

    def __repr__(self) -> str:
        """Get string representation of the version.

        Returns:
            str: Version in YYYY-MM-DD format
        """
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"

    @classmethod
    def from_string(cls, version_str: str) -> "ModelVersion":
        """Create a version from a string in YYYY-MM-DD format.

        Args:
            version_str: The version string to parse

        Returns:
            A new ModelVersion instance

        Raises:
            InvalidDateError: If the string is not a valid version
        """
        parts = version_str.split("-")
        if len(parts) != 3:
            raise InvalidDateError(
                f"Invalid version format: {version_str}. "
                f"Expected YYYY-MM-DD."
            )

        try:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
        except ValueError:
            raise InvalidDateError(
                f"Invalid version components in {version_str}. "
                f"Year, month, and day must be integers."
            )

        # Basic validation
        if not (1000 <= year <= 9999):
            raise InvalidDateError(f"Invalid year: {year}. Must be 1000-9999.")
        if not (1 <= month <= 12):
            raise InvalidDateError(f"Invalid month: {month}. Must be 1-12.")
        if not (1 <= day <= 31):
            raise InvalidDateError(f"Invalid day: {day}. Must be 1-31.")

        # Calendar validation
        try:
            date(year, month, day)
        except ValueError as e:
            raise InvalidDateError(f"Invalid date: {version_str}. {str(e)}")

        return cls(year, month, day)

    @staticmethod
    def parse_from_model(model: str) -> Tuple[str, "ModelVersion"]:
        """Parse a model name into base name and version.

        Args:
            model: Full model name with version (e.g., "gpt-4o-2024-08-06")

        Returns:
            Tuple of (base_name, version)
            Example: ("gpt-4o", ModelVersion(2024, 8, 6))

        Raises:
            ModelFormatError: If the model name does not follow the expected format
            InvalidDateError: If the date part of the model name is invalid
        """
        # Format: "{base_model}-{YYYY}-{MM}-{DD}"
        pattern = re.compile(r"^([\w-]+?)-(\d{4}-\d{2}-\d{2})$")
        match = pattern.match(model)

        if not match:
            raise ModelFormatError(
                f"Invalid model format: {model}. Expected format: "
                f"base-name-YYYY-MM-DD (e.g., gpt-4o-2024-08-06)",
                model=model,
            )

        base_model = match.group(1)
        version_str = match.group(2)

        try:
            version = ModelVersion.from_string(version_str)
            return base_model, version
        except InvalidDateError as e:
            raise ModelFormatError(
                f"Invalid version in model name {model}: {e}",
                model=model,
            ) from e

    @staticmethod
    def is_dated_model(model_name: str) -> bool:
        """Check if a model name follows the dated model format.

        Args:
            model_name: The model name to check

        Returns:
            True if the model name follows the dated format (with YYYY-MM-DD suffix)
        """
        return bool(re.match(r"^.*-\d{4}-\d{2}-\d{2}$", model_name))
