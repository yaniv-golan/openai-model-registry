"""Parameter constraints for the model registry.

This module defines the constraint types used to validate parameters for model calls.
"""

import math
from dataclasses import dataclass
from typing import (
    Any,
    List,
    Optional,
)

from .errors import ModelRegistryError


@dataclass
class ParameterReference:
    """Reference to a parameter constraint with optional metadata."""

    ref: str
    description: str = ""
    max_value: Optional[float] = None


class NumericConstraint:
    """Constraint for numeric parameters."""

    def __init__(
        self,
        min_value: float = 0.0,
        max_value: Optional[float] = None,
        allow_float: bool = True,
        allow_int: bool = True,
        description: str = "",
    ):
        """Initialize numeric constraint.

        Args:
            min_value: Minimum allowed value
            max_value: Maximum allowed value, or None for no upper limit
            allow_float: Whether floating point values are allowed
            allow_int: Whether integer values are allowed
            description: Description of the parameter
        """
        self.min_value = min_value
        self.max_value = max_value
        self.allow_float = allow_float
        self.allow_int = allow_int
        self.description = description

    def validate(self, name: str, value: Any) -> None:
        """Validate a value against this constraint.

        Args:
            name: Parameter name for error messages
            value: Value to validate

        Raises:
            ModelRegistryError: If validation fails
        """
        # Validate numeric type
        if not isinstance(value, (int, float)):
            raise ModelRegistryError(
                f"Parameter '{name}' must be a number, got {type(value).__name__}.\n"
                "Allowed types: "
                + (
                    "float and integer"
                    if self.allow_float and self.allow_int
                    else ("float only" if self.allow_float else "integer only")
                )
            )

        # Validate integer/float requirements
        if isinstance(value, float) and not self.allow_float:
            raise ModelRegistryError(
                f"Parameter '{name}' must be an integer, got float {value}.\n"
                f"Description: {self.description}"
            )
        if isinstance(value, int) and not self.allow_int:
            raise ModelRegistryError(
                f"Parameter '{name}' must be a float, got integer {value}.\n"
                f"Description: {self.description}"
            )

        # Handle special float values (NaN and infinity)
        if isinstance(value, float):
            if math.isnan(value):
                raise ModelRegistryError(
                    f"Parameter '{name}' cannot be NaN (not a number).\n"
                    f"Description: {self.description}"
                )
            if math.isinf(value):
                raise ModelRegistryError(
                    f"Parameter '{name}' cannot be infinity.\n"
                    f"Description: {self.description}"
                )

        # Validate range
        min_val = self.min_value
        max_val = self.max_value

        if value < min_val or (max_val is not None and value > max_val):
            max_desc = str(max_val) if max_val is not None else "unlimited"
            raise ModelRegistryError(
                f"Parameter '{name}' must be between {min_val} and {max_desc}.\n"
                f"Description: {self.description}\n"
                f"Current value: {value}"
            )


class EnumConstraint:
    """Constraint for enumerated parameters."""

    def __init__(
        self,
        allowed_values: List[str],
        description: str = "",
    ):
        """Initialize enum constraint.

        Args:
            allowed_values: List of allowed string values
            description: Description of the parameter
        """
        self.allowed_values = allowed_values
        self.description = description

    def validate(self, name: str, value: Any) -> None:
        """Validate a value against this constraint.

        Args:
            name: Parameter name for error messages
            value: Value to validate

        Raises:
            ModelRegistryError: If validation fails
        """
        # Validate type
        if not isinstance(value, str):
            raise ModelRegistryError(
                f"Parameter '{name}' must be a string, got {type(value).__name__}.\n"
                f"Description: {self.description}"
            )

        # Validate allowed values
        if value not in self.allowed_values:
            raise ModelRegistryError(
                f"Invalid value '{value}' for parameter '{name}'.\n"
                f"Description: {self.description}\n"
                f"Allowed values: {', '.join(map(str, sorted(self.allowed_values)))}"
            )
