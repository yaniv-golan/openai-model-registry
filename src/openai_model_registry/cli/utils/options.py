"""Common CLI options and decorators."""

from functools import wraps
from typing import Any, Callable, TypeVar, cast

import click

from .helpers import validate_provider

F = TypeVar("F", bound=Callable[..., Any])


def provider_option(func: F) -> F:
    """Add --provider option to a command."""

    @click.option(
        "--provider",
        type=str,
        help="Override active provider (openai, azure, etc.). Takes precedence over OMR_PROVIDER environment variable.",
    )
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if kwargs.get("provider"):
            kwargs["provider"] = validate_provider(kwargs["provider"])
        return func(*args, **kwargs)

    return cast(F, wrapper)


def format_option(func: F) -> F:
    """Add --format option to a command."""

    @click.option(
        "--format",
        type=click.Choice(["table", "json", "csv", "yaml"], case_sensitive=False),
        help="Output format. Defaults to 'table' for TTY, 'json' for non-TTY.",
    )
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    return cast(F, wrapper)


def output_option(func: F) -> F:
    """Add --output option to a command."""

    @click.option("--output", "-o", type=click.Path(), help="Write output to file instead of stdout.")
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    return cast(F, wrapper)


def verbosity_options(func: F) -> F:
    """Add verbosity options to a command."""

    @click.option("--verbose", "-v", count=True, help="Increase verbosity (can be used multiple times).")
    @click.option("--quiet", "-q", count=True, help="Decrease verbosity (can be used multiple times).")
    @click.option("--debug", is_flag=True, help="Enable debug-level logging.")
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    return cast(F, wrapper)


def common_options(func: F) -> F:
    """Add common options (provider, format, verbosity) to a command."""
    func = provider_option(func)
    func = format_option(func)
    func = verbosity_options(func)
    return func


# help_json_option removed - only root-level --help-json is supported
