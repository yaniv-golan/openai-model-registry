"""Supplementary tests for *config_paths* path-precedence helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

from openai_model_registry import config_paths


@pytest.fixture()
def temp_file(tmp_path: Path) -> Iterator[Path]:
    """Create a temporary dummy YAML file and yield its path."""
    file_path = tmp_path / "dummy.yaml"
    file_path.write_text("version: 1\n")
    yield file_path


# Model registry path functionality moved to DataManager


def test_get_parameter_constraints_path_env_var(monkeypatch: pytest.MonkeyPatch, temp_file: Path) -> None:  # noqa: D401
    """Environment variable *PARAM_CONSTRAINTS_PATH* overrides defaults."""
    monkeypatch.setenv(config_paths.ENV_PARAM_CONSTRAINTS, str(temp_file))
    resolved = config_paths.get_parameter_constraints_path()
    assert resolved == str(temp_file)
