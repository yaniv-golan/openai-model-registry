"""Configuration loading result object.

This module defines a standard result object for configuration loading operations.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ConfigResult:
    """Result of a configuration loading operation.

    This class provides a standardized way to handle results of configuration
    loading operations, including success/failure status and error information.

    Attributes:
        success: Whether the operation was successful
        data: Configuration data (if successful)
        error: Error message (if unsuccessful)
        exception: Original exception (if an error occurred)
        path: Path to the configuration file (if applicable)
    """

    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    exception: Optional[Exception] = None
    path: Optional[str] = None
