#!/usr/bin/env python3
"""
Release automation script for OpenAI Model Registry.

Inspired by ostruct's release process.

Usage:
    python scripts/release.py patch    # 0.1.0 -> 0.1.1
    python scripts/release.py minor    # 0.1.0 -> 0.2.0
    python scripts/release.py major    # 0.1.0 -> 1.0.0
    python scripts/release.py --dry-run patch
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional


# Colors for output
class Colors:
    """ANSI color codes for terminal output."""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"  # No Color


def log_info(message: str) -> None:
    """Print info message in green."""
    print(f"{Colors.GREEN}[INFO]{Colors.NC} {message}")


def log_warn(message: str) -> None:
    """Print warning message in yellow."""
    print(f"{Colors.YELLOW}[WARN]{Colors.NC} {message}")


def log_error(message: str) -> None:
    """Print error message in red."""
    print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")


def log_step(message: str) -> None:
    """Print step message in blue."""
    print(f"{Colors.BLUE}[STEP]{Colors.NC} {message}")


def run_command(
    cmd: str, check: bool = True, capture_output: bool = False
) -> Optional[str]:
    """Run a shell command and return output if requested."""
    try:
        if capture_output:
            result = subprocess.run(
                cmd, shell=True, check=check, capture_output=True, text=True
            )
            return result.stdout.strip()
        else:
            subprocess.run(cmd, shell=True, check=check)
            return None
    except subprocess.CalledProcessError as e:
        log_error(f"Command failed: {cmd}")
        if capture_output:
            log_error(f"Error output: {e.stderr}")
        sys.exit(1)


def validate_environment() -> None:
    """Validate the environment before starting release process."""
    log_step("Validating environment...")

    # Check if we're in the project root
    if not Path("pyproject.toml").exists():
        log_error("pyproject.toml not found. Are you in the project root?")
        sys.exit(1)

    # Check if Poetry is available
    try:
        run_command("poetry --version", capture_output=True)
    except subprocess.CalledProcessError:
        log_error("Poetry not found. Please install Poetry.")
        sys.exit(1)

    # Check if we're on main branch
    current_branch = run_command(
        "git branch --show-current", capture_output=True
    )
    if current_branch != "main":
        log_error(f"Must be on main branch. Current: {current_branch}")
        sys.exit(1)

    # Check for uncommitted changes
    status = run_command("git status --porcelain", capture_output=True)
    if status:
        log_error(
            "Uncommitted changes detected. Please commit or stash changes."
        )
        sys.exit(1)

    # Check if we're up to date with remote
    run_command("git fetch origin")
    local_commit = run_command("git rev-parse HEAD", capture_output=True)
    remote_commit = run_command(
        "git rev-parse origin/main", capture_output=True
    )
    if local_commit != remote_commit:
        log_error("Local branch is not up to date with origin/main")
        sys.exit(1)

    log_info("Environment validation passed")


def get_current_version() -> str:
    """Get current version from Poetry."""
    version = run_command("poetry version -s", capture_output=True)
    if version is None:
        log_error("Failed to get current version from Poetry")
        sys.exit(1)
    return version


def bump_version(release_type: str, dry_run: bool = False) -> str:
    """Bump version using Poetry."""
    current_version = get_current_version()
    log_info(f"Current version: {current_version}")

    if dry_run:
        log_warn(f"DRY RUN: Would bump {release_type} version")
        # Simulate version bump for dry run
        parts = current_version.split(".")
        if release_type == "patch":
            parts[2] = str(int(parts[2]) + 1)
        elif release_type == "minor":
            parts[1] = str(int(parts[1]) + 1)
            parts[2] = "0"
        elif release_type == "major":
            parts[0] = str(int(parts[0]) + 1)
            parts[1] = "0"
            parts[2] = "0"
        return ".".join(parts)

    run_command(f"poetry version {release_type}")
    new_version = get_current_version()
    log_info(f"New version: {new_version}")
    return new_version


def run_tests(dry_run: bool = False) -> None:
    """Run comprehensive tests."""
    log_step("Running tests...")

    if dry_run:
        log_warn("DRY RUN: Would run tests")
        return

    # Install dependencies
    run_command("poetry install --with dev,test")

    # Run tests
    log_info("Running pytest...")
    run_command("poetry run pytest -xvs")

    # Run type checking
    log_info("Running mypy...")
    run_command("poetry run mypy src/")

    # Run linting
    log_info("Running flake8...")
    run_command("poetry run flake8 src/")

    # Test import
    log_info("Testing package import...")
    run_command(
        "poetry run python -c 'import openai_model_registry; print(\"✅ Import successful\")'"
    )

    log_info("All tests passed")


def update_changelog(version: str, dry_run: bool = False) -> None:
    """Update CHANGELOG.md with new version."""
    changelog_path = Path("CHANGELOG.md")

    if not changelog_path.exists():
        log_warn("CHANGELOG.md not found, creating one...")
        if not dry_run:
            changelog_path.write_text(
                "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n"
            )

    if dry_run:
        log_warn(f"DRY RUN: Would update changelog for version {version}")
        return

    # Read existing changelog
    content = changelog_path.read_text()

    # Create new entry
    from datetime import datetime

    date = datetime.now().strftime("%Y-%m-%d")
    new_entry = f"""## [{version}] - {date}

### Added
-

### Changed
-

### Fixed
-

### Removed
-

"""

    # Insert new entry after the header
    lines = content.split("\n")
    header_end = 0
    for i, line in enumerate(lines):
        if line.startswith("## ") or i == len(lines) - 1:
            header_end = i
            break

    # Insert new entry
    lines.insert(header_end, new_entry)

    # Write back
    changelog_path.write_text("\n".join(lines))
    log_info(f"Updated CHANGELOG.md for version {version}")


def create_release_commit(version: str, dry_run: bool = False) -> None:
    """Create release commit and tag."""
    if dry_run:
        log_warn(f"DRY RUN: Would create release commit for v{version}")
        return

    # Add changed files
    run_command("git add pyproject.toml CHANGELOG.md")

    # Create commit
    run_command(f'git commit -m "Release v{version}"')

    # Create tag
    run_command(f"git tag v{version}")

    log_info(f"Created release commit and tag for v{version}")


def push_release(dry_run: bool = False) -> None:
    """Push release to origin."""
    if dry_run:
        log_warn("DRY RUN: Would push release to origin")
        return

    run_command("git push origin main")
    run_command("git push origin --tags")

    log_info("Pushed release to origin")


def create_github_release(version: str, dry_run: bool = False) -> None:
    """Create GitHub release using gh CLI."""
    if dry_run:
        log_warn(f"DRY RUN: Would create GitHub release for v{version}")
        return

    # Check if gh CLI is available
    try:
        run_command("gh --version", capture_output=True)
    except subprocess.CalledProcessError:
        log_warn(
            "GitHub CLI (gh) not found. Skipping GitHub release creation."
        )
        log_info(
            "You can create the release manually at: https://github.com/yaniv-golan/openai-model-registry/releases/new"
        )
        return

    # Extract changelog for this version
    changelog_path = Path("CHANGELOG.md")
    if changelog_path.exists():
        content = changelog_path.read_text()
        lines = content.split("\n")

        # Find the section for this version
        start_idx = None
        end_idx = None
        for i, line in enumerate(lines):
            if line.startswith(f"## [{version}]"):
                start_idx = i
            elif (
                start_idx is not None
                and line.startswith("## [")
                and not line.startswith(f"## [{version}]")
            ):
                end_idx = i
                break

        if start_idx is not None:
            if end_idx is None:
                end_idx = len(lines)
            release_notes = "\n".join(lines[start_idx:end_idx]).strip()
        else:
            release_notes = f"Release v{version}"
    else:
        release_notes = f"Release v{version}"

    # Create GitHub release
    run_command(
        f'gh release create v{version} --title "Release v{version}" --notes "{release_notes}"'
    )
    log_info(f"Created GitHub release for v{version}")


def main() -> None:
    """Main release automation function."""
    parser = argparse.ArgumentParser(
        description="Release automation for OpenAI Model Registry"
    )
    parser.add_argument(
        "release_type",
        choices=["patch", "minor", "major"],
        help="Type of release to create",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests (not recommended)",
    )
    parser.add_argument(
        "--skip-github-release",
        action="store_true",
        help="Skip creating GitHub release",
    )

    args = parser.parse_args()

    log_info("Starting release process...")
    log_info(f"Release type: {args.release_type}")
    if args.dry_run:
        log_warn("DRY RUN MODE - No changes will be made")

    # Validate environment
    validate_environment()

    # Run tests first
    if not args.skip_tests:
        run_tests(args.dry_run)
    else:
        log_warn("Skipping tests (--skip-tests flag)")

    # Bump version
    new_version = bump_version(args.release_type, args.dry_run)

    # Update changelog
    update_changelog(new_version, args.dry_run)

    # Create release commit and tag
    create_release_commit(new_version, args.dry_run)

    # Push to origin
    push_release(args.dry_run)

    # Create GitHub release
    if not args.skip_github_release:
        create_github_release(new_version, args.dry_run)

    log_info("Release process completed successfully!")
    log_info(f"Version {new_version} has been released")

    if not args.dry_run:
        log_info("GitHub Actions will handle PyPI publishing automatically")
        log_info(
            "Monitor the release at: https://github.com/yaniv-golan/openai-model-registry/actions"
        )


if __name__ == "__main__":
    main()
