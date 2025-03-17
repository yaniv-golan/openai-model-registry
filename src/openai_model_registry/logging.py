"""Logging utilities for the model registry.

This module provides standardized logging functionality for registry operations.
"""

import logging
from enum import Enum
from typing import Any, Optional

# Create the logger
logger = logging.getLogger("openai_model_registry")


class LogEvent(str, Enum):
    """Event types for registry logging."""

    MODEL_REGISTRY = "model_registry"
    MODEL_CAPABILITIES = "model_capabilities"
    PARAMETER_VALIDATION = "parameter_validation"
    VERSION_VALIDATION = "version_validation"
    REGISTRY_UPDATE = "registry_update"


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger for a module.

    Args:
        name: Optional name for the logger. If None, returns the root package logger.

    Returns:
        A configured logger instance
    """
    if name:
        return logging.getLogger(f"openai_model_registry.{name}")
    return logger


def log_debug(event: LogEvent, message: str, **kwargs: Any) -> None:
    """Log a debug message.

    Args:
        event: The event type
        message: The message to log
        **kwargs: Additional data to include in the log
    """
    extra = {"event": str(event), **kwargs}
    logger.debug(f"{message}", extra=extra)


def log_info(event: LogEvent, message: str, **kwargs: Any) -> None:
    """Log an info message.

    Args:
        event: The event type
        message: The message to log
        **kwargs: Additional data to include in the log
    """
    extra = {"event": str(event), **kwargs}
    logger.info(f"{message}", extra=extra)


def log_warning(event: LogEvent, message: str, **kwargs: Any) -> None:
    """Log a warning message.

    Args:
        event: The event type
        message: The message to log
        **kwargs: Additional data to include in the log
    """
    extra = {"event": str(event), **kwargs}
    logger.warning(f"{message}", extra=extra)


def log_error(event: LogEvent, message: str, **kwargs: Any) -> None:
    """Log an error message.

    Args:
        event: The event type
        message: The message to log
        **kwargs: Additional data to include in the log
    """
    extra = {"event": str(event), **kwargs}
    logger.error(f"{message}", extra=extra)


def log_critical(event: LogEvent, message: str, **kwargs: Any) -> None:
    """Log a critical message.

    Args:
        event: The event type
        message: The message to log
        **kwargs: Additional data to include in the log
    """
    extra = {"event": str(event), **kwargs}
    logger.critical(f"{message}", extra=extra)
