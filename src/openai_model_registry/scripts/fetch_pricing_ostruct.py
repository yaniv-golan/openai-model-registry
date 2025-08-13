"""Fetch model pricing using the *ostruct* CLI.

The script calls::

    ostruct run <template> <schema> -V model=<MODEL>

and writes deterministic YAML to ``pricing_data/{model}.yaml`` so that the
GitHub Action can commit only on change.

Uses gpt-4.1 as the underlying LLM to ensure deterministic high-quality extraction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[3]  # project root
SCRIPT_DIR = ROOT / "scripts" / "ostruct"
TEMPLATE = SCRIPT_DIR / "pricing_template.j2"
SCHEMA = SCRIPT_DIR / "pricing_schema.json"
OUTPUT_DIR = ROOT / "pricing_data"
OUTPUT_DIR.mkdir(exist_ok=True)


def run_ostruct(model: str) -> Dict[str, Any]:
    """Invoke ostruct CLI and return parsed JSON.

    Resolution order:
    1) Use system-resolved "ostruct" if available (recommended, provisioned by CI)
    2) If not found and OMR_ALLOW_PIPX in {1, true, yes}, try pipx run with pinned version
    """
    base_args = [
        "run",
        str(TEMPLATE),
        str(SCHEMA),
        "--enable-tool",
        "web-search",
        "-V",
        f"model={model}",
        "-V",
        "root_url=https://platform.openai.com/docs/models/",
        "--model",
        "gpt-4.1",
        "--temperature",
        "0",
    ]

    def _exec(cmd: list[str]) -> Dict[str, Any]:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        parsed: Dict[str, Any] = json.loads(result.stdout.strip())
        return parsed

    # First: try system ostruct if on PATH
    if shutil.which("ostruct"):
        return _exec(["ostruct", *base_args])

    # Fallback: optional pipx run if allowed
    allow_pipx = os.getenv("OMR_ALLOW_PIPX", "").lower() in {"1", "true", "yes"}
    if allow_pipx and shutil.which("pipx"):
        return _exec(["pipx", "run", "--spec", "ostruct-cli==1.6.1", "ostruct", *base_args])

    raise RuntimeError("ostruct CLI not found. Install it or run with OMR_ALLOW_PIPX=1 and pipx available.")


def write_yaml(data: Dict[str, Any], path: Path) -> None:
    """Write pricing *data* to *path* in deterministic YAML format."""
    import yaml  # local import to avoid hard dep if script unused

    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=True)


def sha256_of_file(path: Path) -> str:
    """Return the SHA-256 checksum (hex digest) of the file at *path*."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        h.update(f.read())
    return h.hexdigest()


def main() -> None:  # noqa: D401
    """CLI entry point that fetches pricing and updates cached YAML files."""
    parser = argparse.ArgumentParser(description="Fetch pricing via ostruct")
    parser.add_argument("--model", required=True, help="Model name, e.g. gpt-4o")
    args = parser.parse_args()

    pricing = run_ostruct(args.model)

    output_path = OUTPUT_DIR / f"{args.model}.yaml"
    tmp_path = output_path.with_suffix(".tmp")
    write_yaml(pricing, tmp_path)

    new_checksum = sha256_of_file(tmp_path)
    old_checksum = sha256_of_file(output_path) if output_path.exists() else ""

    if new_checksum != old_checksum:
        tmp_path.rename(output_path)
        print(f"Updated pricing file: {output_path} ({new_checksum})")
    else:
        tmp_path.unlink()
        print("No pricing change detected – nothing to commit.")


if __name__ == "__main__":
    main()
