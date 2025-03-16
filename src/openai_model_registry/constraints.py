"""Parameter constraints for the model registry.

This module defines the constraint types used to validate parameters for model calls.
"""

from typing import (
    List,
    Optional,
)

from pydantic import BaseModel


class NumericConstraint(BaseModel):
    """Constraint for numeric parameters.

    This defines the valid range and types for numeric parameters.

    Attributes:
        type: The constraint type, always "numeric"
        min_value: The minimum allowed value
        max_value: The maximum allowed value (can be None for context-dependent limits)
        description: Human-readable description of the parameter
        allow_float: Whether float values are allowed
        allow_int: Whether integer values are allowed
    """

    type: str = "numeric"
    min_value: float
    max_value: Optional[float] = None
    description: str
    allow_float: bool = True
    allow_int: bool = True

    model_config = {
        "arbitrary_types_allowed": True,
    }


class EnumConstraint(BaseModel):
    """Constraint for enum parameters.

    This defines the valid values for enum parameters.

    Attributes:
        type: The constraint type, always "enum"
        allowed_values: List of allowed string values
        description: Human-readable description of the parameter
    """

    type: str = "enum"
    allowed_values: List[str]
    description: str

    model_config = {
        "arbitrary_types_allowed": True,
    }


class ParameterReference(BaseModel):
    """Reference to a parameter constraint.

    This is used in model capabilities to reference constraints.

    Attributes:
        ref: Reference to a constraint (e.g., "numeric_constraints.temperature")
        max_value: Optional override for the max_value in the referenced constraint
    """

    ref: str
    max_value: Optional[float] = None

    model_config = {
        "arbitrary_types_allowed": True,
    }
