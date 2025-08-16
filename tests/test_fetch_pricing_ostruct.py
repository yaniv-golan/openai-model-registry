"""Unit test for fetch_pricing_ostruct script (offline, no OpenAI key)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import yaml

from openai_model_registry.scripts.fetch_pricing_ostruct import (
    OUTPUT_DIR,
    run_ostruct,
    write_yaml,
)


def _fake_subprocess_run(cmd: list[str], capture_output: bool, text: bool, check: bool) -> Any:  # noqa: D401
    """Return deterministic JSON payload for pricing."""
    model_arg = next(x for x in cmd if x.startswith("model="))
    model = model_arg.split("=", 1)[1]

    payload: Dict[str, Any] = {
        "model": model,
        "currency": "USD",
        "input_per_million": 5.0,
        "output_per_million": 15.0,
    }

    class _Res:  # minimal CompletedProcess stub
        stdout = json.dumps(payload)

    return _Res()


@patch("subprocess.run", _fake_subprocess_run)  # noqa: D401
@patch.dict("os.environ", {"OMR_TEST_ALLOW_FAKE": "1"})
def test_run_ostruct_mock(tmp_path: Path) -> None:
    """Script returns dict and writes YAML deterministically."""
    # Ensure OUTPUT_DIR points to tmp
    orig_dir = OUTPUT_DIR
    try:
        globals_dict = globals()
        globals_dict["OUTPUT_DIR"] = tmp_path
        (tmp_path).mkdir(exist_ok=True)

        data = run_ostruct("gpt-4o")
        assert data["model"] == "gpt-4o"
        out_file = tmp_path / "gpt-4o.yaml"
        write_yaml(data, out_file)
        loaded = yaml.safe_load(out_file.read_text())
        assert loaded == data
    finally:
        globals_dict["OUTPUT_DIR"] = orig_dir
