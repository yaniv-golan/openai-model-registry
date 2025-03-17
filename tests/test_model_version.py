"""Tests for model_version.py."""

import pytest

from openai_model_registry.model_version import ModelVersion


class TestModelVersion:
    """Tests for the ModelVersion class."""

    def test_init(self) -> None:
        """Test initialization."""
        version = ModelVersion(2024, 5, 15)
        assert version.year == 2024
        assert version.month == 5
        assert version.day == 15

    def test_eq(self) -> None:
        """Test equality comparison."""
        v1 = ModelVersion(2024, 5, 15)
        v2 = ModelVersion(2024, 5, 15)
        v3 = ModelVersion(2024, 6, 15)

        assert v1 == v2
        assert v1 != v3
        assert v1 != "not-a-version"

    def test_lt(self) -> None:
        """Test less than comparison."""
        v1 = ModelVersion(2023, 5, 15)
        v2 = ModelVersion(2024, 5, 15)
        v3 = ModelVersion(2024, 4, 15)
        v4 = ModelVersion(2024, 5, 14)

        assert v1 < v2  # Different year
        assert v3 < v2  # Same year, different month
        assert v4 < v2  # Same year and month, different day
        assert not (v2 < v1)  # Reverse comparison

    def test_le(self) -> None:
        """Test less than or equal comparison."""
        v1 = ModelVersion(2023, 5, 15)
        v2 = ModelVersion(2024, 5, 15)
        v_same = ModelVersion(2024, 5, 15)

        assert v1 <= v2
        assert v2 <= v_same
        assert not (v2 <= v1)

    def test_gt(self) -> None:
        """Test greater than comparison."""
        v1 = ModelVersion(2024, 5, 15)
        v2 = ModelVersion(2023, 5, 15)
        v3 = ModelVersion(2024, 4, 15)
        v4 = ModelVersion(2024, 5, 14)

        assert v1 > v2  # Different year
        assert v1 > v3  # Same year, different month
        assert v1 > v4  # Same year and month, different day
        assert not (v2 > v1)  # Reverse comparison

    def test_ge(self) -> None:
        """Test greater than or equal comparison."""
        v1 = ModelVersion(2024, 5, 15)
        v2 = ModelVersion(2023, 5, 15)
        v_same = ModelVersion(2024, 5, 15)

        assert v1 >= v2
        assert v1 >= v_same
        assert not (v2 >= v1)

    def test_repr(self) -> None:
        """Test string representation."""
        version = ModelVersion(2024, 5, 15)
        assert repr(version) == "2024-05-15"

        # Test padding for single digit month/day
        version = ModelVersion(2024, 1, 1)
        assert repr(version) == "2024-01-01"

    def test_from_string_valid(self) -> None:
        """Test creating a version from valid string."""
        version = ModelVersion.from_string("2024-05-15")
        assert version.year == 2024
        assert version.month == 5
        assert version.day == 15

    def test_from_string_invalid_format(self) -> None:
        """Test creating a version from invalid format."""
        with pytest.raises(ValueError, match="Invalid version format"):
            ModelVersion.from_string("2024/05/15")

        with pytest.raises(ValueError, match="Invalid version format"):
            ModelVersion.from_string("2024-05")

    def test_from_string_invalid_components(self) -> None:
        """Test creating a version with invalid components."""
        with pytest.raises(ValueError, match="must be integers"):
            ModelVersion.from_string("year-05-15")

    def test_from_string_invalid_ranges(self) -> None:
        """Test creating a version with out-of-range values."""
        with pytest.raises(ValueError, match="Invalid year"):
            ModelVersion.from_string("999-05-15")

        with pytest.raises(ValueError, match="Invalid month"):
            ModelVersion.from_string("2024-13-15")

        with pytest.raises(ValueError, match="Invalid day"):
            ModelVersion.from_string("2024-05-32")

    def test_parse_from_model_valid(self) -> None:
        """Test parsing a valid model string."""
        result = ModelVersion.parse_from_model("gpt-4o-2024-05-15")
        assert result is not None
        base_model, version = result
        assert base_model == "gpt-4o"
        assert version.year == 2024
        assert version.month == 5
        assert version.day == 15

    def test_parse_from_model_invalid(self) -> None:
        """Test parsing invalid model strings."""
        # No date
        assert ModelVersion.parse_from_model("gpt-4o") is None

        # Invalid date format
        assert ModelVersion.parse_from_model("gpt-4o-2024/05/15") is None

        # Invalid date
        assert ModelVersion.parse_from_model("gpt-4o-2024-13-15") is None

    def test_is_dated_model(self) -> None:
        """Test checking if a model name follows the dated format."""
        # Valid dated models
        assert ModelVersion.is_dated_model("gpt-4o-2024-05-15")
        assert ModelVersion.is_dated_model("model-name-with-dashes-2024-05-15")

        # Invalid dated models
        assert not ModelVersion.is_dated_model("gpt-4o")
        assert not ModelVersion.is_dated_model("gpt-4o-preview")
        assert not ModelVersion.is_dated_model("gpt-4o-2024-0515")
        assert not ModelVersion.is_dated_model("gpt-4o-20240515")
