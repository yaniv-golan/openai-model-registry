"""Additional unit tests to raise overall coverage.

These tests focus on modules that previously had low coverage:
    • deprecation.py (assert_model_active, sunset_headers)
    • constraints.py (ObjectConstraint validation)
    • model_version.py (parsing and comparison helpers)
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict

import pytest

from openai_model_registry.constraints import ObjectConstraint
from openai_model_registry.deprecation import (
    DeprecationInfo,
    ModelSunsetError,
    assert_model_active,
    sunset_headers,
)
from openai_model_registry.model_version import ModelVersion


class TestDeprecationHelpers:
    """Tests for helper functions in the *deprecation* module."""

    def test_assert_model_active_active(self) -> None:  # noqa: D401
        """No exception or warning for active models."""
        info = DeprecationInfo(
            status="active",
            deprecates_on=None,
            sunsets_on=None,
            replacement=None,
            migration_guide=None,
            reason="active",
        )
        # Should simply return without error / warning
        assert_model_active("test-model", info)

    def test_assert_model_active_deprecated_warns(self) -> None:  # noqa: D401
        """Deprecated models emit *DeprecationWarning*."""
        info = DeprecationInfo(
            status="deprecated",
            deprecates_on=date(2025, 1, 1),
            sunsets_on=date(2025, 6, 1),
            replacement="new-model",
            migration_guide="https://example.com/migrate",
            reason="legacy",
        )
        with pytest.warns(DeprecationWarning):
            assert_model_active("old-model", info)

    def test_assert_model_active_sunset_raises(self) -> None:  # noqa: D401
        """Sunset models raise *ModelSunsetError*."""
        info = DeprecationInfo(
            status="sunset",
            deprecates_on=date(2024, 1, 1),
            sunsets_on=date(2024, 6, 1),
            replacement=None,
            migration_guide=None,
            reason="unsupported",
        )
        with pytest.raises(ModelSunsetError):
            assert_model_active("really-old-model", info)

    def test_sunset_headers_generation(self) -> None:  # noqa: D401
        """Headers are generated according to RFC specs when applicable."""
        info = DeprecationInfo(
            status="deprecated",
            deprecates_on=date(2030, 1, 1),
            sunsets_on=date(2030, 12, 31),
            replacement="next-gen",
            migration_guide="https://docs.example.com/migrate",
            reason="EOL",
        )
        headers: Dict[str, str] = sunset_headers(info)
        assert headers["Deprecation"] == "2030-01-01"
        assert headers["Sunset"] == "2030-12-31"
        assert re.match(r"<https://docs\.example\.com/migrate>.*", headers["Link"])


class TestObjectConstraint:
    """Validation scenarios for *ObjectConstraint*."""

    def test_object_constraint_valid(self) -> None:  # noqa: D401
        """A valid dictionary passes validation."""
        constraint = ObjectConstraint(
            required_keys=["foo"],
            allowed_keys=["foo", "bar"],
        )
        value: Dict[str, Any] = {"foo": 1, "bar": 2}
        constraint.validate("obj", value)  # Should not raise

    def test_object_constraint_missing_required(self) -> None:  # noqa: D401
        """Missing required keys triggers *ModelRegistryError*."""
        from openai_model_registry.errors import ModelRegistryError

        constraint = ObjectConstraint(required_keys=["foo"])
        with pytest.raises(ModelRegistryError):
            constraint.validate("obj", {"bar": 2})

    def test_object_constraint_invalid_keys(self) -> None:  # noqa: D401
        """Keys outside *allowed_keys* are rejected."""
        from openai_model_registry.errors import ModelRegistryError

        constraint = ObjectConstraint(allowed_keys=["a", "b"])
        with pytest.raises(ModelRegistryError):
            constraint.validate("obj", {"a": 1, "z": 2})


class TestModelVersion:
    """Unit tests for *ModelVersion* utilities."""

    def test_from_string_and_comparison(self) -> None:  # noqa: D401
        """Parsing and rich comparison operators work as expected."""
        v1 = ModelVersion.from_string("2024-05-13")
        v2 = ModelVersion.from_string("2024-06-01")

        assert str(v1) == "2024-05-13"
        assert v1 < v2
        assert v1 <= v2
        assert v2 > v1
        assert v2 >= v1
        assert v1 != v2

    @pytest.mark.parametrize(
        "bad_str",
        [
            "invalid",  # no dashes
            "2024-13-01",  # invalid month
            "2024-02-30",  # invalid day (Feb 30)
            "999-01-01",  # year too short
        ],
    )
    def test_from_string_invalid(self, bad_str: str) -> None:  # noqa: D401
        """Invalid strings raise *InvalidDateError*."""
        from openai_model_registry.errors import InvalidDateError

        with pytest.raises(InvalidDateError):
            ModelVersion.from_string(bad_str)

    def test_parse_from_model_success(self) -> None:  # noqa: D401
        """Model names with version suffix are parsed correctly."""
        base, version = ModelVersion.parse_from_model("gpt-4o-2024-08-06")
        assert base == "gpt-4o"
        assert str(version) == "2024-08-06"

    def test_parse_from_model_invalid(self) -> None:  # noqa: D401
        """Invalid model names raise *ModelFormatError*."""
        from openai_model_registry.errors import ModelFormatError

        with pytest.raises(ModelFormatError):
            ModelVersion.parse_from_model("not-a-valid-model-name")

    @pytest.mark.parametrize(
        "name,is_dated",
        [
            ("gpt-4o-2024-08-06", True),
            ("gpt-4o", False),
            ("model-1234-12-30", True),
        ],
    )
    def test_is_dated_model(self, name: str, is_dated: bool) -> None:  # noqa: D401
        """Helper detects dated models using regex."""
        assert ModelVersion.is_dated_model(name) is is_dated
