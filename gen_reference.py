"""Generate API reference Markdown files for MkDocs with mkdocstrings.

This script should be executed during the documentation build step.
"""

from __future__ import annotations

from pathlib import Path

import mkdocs_gen_files  # type: ignore

PACKAGE = "openai_model_registry"


def main() -> None:  # noqa: D401
    """Generate reference Markdown files automatically."""
    nav = mkdocs_gen_files.Nav()

    package_dir = Path("src") / PACKAGE

    # Walk through package to collect .py files
    for path in sorted(package_dir.rglob("*.py")):
        relative_path = path.relative_to(package_dir)
        if relative_path.name == "__init__.py":
            continue  # skip root __init__

        module_path = ".".join([PACKAGE, *relative_path.with_suffix("").parts])
        doc_path = Path("api_reference", *relative_path.with_suffix(".md").parts)

        nav[module_path.split(".")[1:]] = doc_path.as_posix()

        with mkdocs_gen_files.open(doc_path, "w") as fd:
            print(f"::: {module_path}", file=fd)

    # Write navigation file
    with mkdocs_gen_files.open("api_reference/SUMMARY.md", "w") as nav_file:
        nav_lines = nav.build_literate_nav()
        nav_file.writelines("\n".join(nav_lines))


if __name__ == "__main__":
    main()
