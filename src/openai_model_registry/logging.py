"""Logging utilities for the model registry.

This module provides standardized logging functionality for registry operations.
"""

import logging
from enum import Enum
from typing import Any, Callable, Dict

# Type for log callback functions
LogCallback = Callable[[int, str, Dict[str, Any]], None]


class LogLevel(int, Enum):
    """Log levels for the registry."""

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class LogEvent(str, Enum):
    """Event types for registry logging."""

    MODEL_REGISTRY = "model_registry"
    MODEL_CAPABILITIES = "model_capabilities"
    PARAMETER_VALIDATION = "parameter_validation"
    VERSION_VALIDATION = "version_validation"
    REGISTRY_UPDATE = "registry_update"


def _log(
    callback: LogCallback,
    level: LogLevel,
    event: LogEvent,
    data: Dict[str, Any],
) -> None:
    """Log an event with the provided callback.

    Args:
        callback: Function to call with the log data
        level: Severity level
        event: Event type
        data: Dictionary of event data
    """
    try:
        callback(level, str(event), data)
    except Exception as e:
        # Fallback to standard logging if callback fails
        logging.error(
            f"Logging callback failed with error: {e}. Original log: "
            f"level={level}, event={event}, data={data}"
        )
