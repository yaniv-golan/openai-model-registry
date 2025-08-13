"""Data manager for OpenAI Model Registry.

This module handles fetching, caching, and managing model registry data files
from GitHub releases with version tracking and integrity verification.
"""

import hashlib
import json
import os
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

try:
    from importlib import resources
except ImportError:
    # Fallback for Python < 3.9
    import importlib_resources as resources  # type: ignore

try:
    import requests
except ImportError:
    requests = None  # type: ignore

from platformdirs import user_data_dir

from .logging import get_logger

logger = get_logger(__name__)

# GitHub API configuration
GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_FALLBACK_BASES = [
    "https://api.github.com",
    "https://github.com/api/v3",  # Alternative GitHub API endpoint
]
GITHUB_REPO = "yaniv-golan/openai-model-registry"
DATA_RELEASE_TAG_PREFIX = "data-v"

# Environment variables (all prefixed with OMR_)
ENV_DISABLE_DATA_UPDATES = "OMR_DISABLE_DATA_UPDATES"
ENV_DATA_VERSION_PIN = "OMR_DATA_VERSION_PIN"
ENV_DATA_DIR = "OMR_DATA_DIR"

# File names
MODELS_YAML = "models.yaml"
OVERRIDES_YAML = "overrides.yaml"
CHECKSUMS_TXT = "checksums.txt"
VERSION_INFO_JSON = "version_info.json"


class DataManager:
    """Manages model registry data files with automatic updates and caching."""

    def __init__(self) -> None:
        """Initialize the data manager."""
        self._data_dir = self._get_data_directory()
        self._ensure_data_directory()
        self._version_lock = threading.Lock()

    def _get_data_directory(self) -> Path:
        """Get the data directory path, respecting OMR_DATA_DIR override."""
        custom_dir = os.getenv(ENV_DATA_DIR)
        if custom_dir:
            return Path(custom_dir)

        return Path(user_data_dir("openai-model-registry"))

    def _ensure_data_directory(self) -> None:
        """Ensure the data directory exists with proper permissions."""
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # Set secure permissions (readable/writable by owner only)
        if hasattr(os, "chmod"):
            os.chmod(self._data_dir, 0o700)  # Only owner can read/write/execute

    def _get_github_api_url(self, endpoint: str, base_url: Optional[str] = None) -> str:
        """Get GitHub API URL for the given endpoint."""
        base = base_url or GITHUB_API_BASE
        return f"{base}/repos/{GITHUB_REPO}/{endpoint}"

    def _fetch_latest_data_release(self) -> Optional[Dict[str, Any]]:
        """Fetch information about the latest data release from GitHub API with fallback URLs."""
        if requests is None:
            logger.error("requests module not available - cannot fetch data releases")
            return None

        # Try each fallback base URL
        for base_url in GITHUB_API_FALLBACK_BASES:
            try:
                url = self._get_github_api_url("releases", base_url)
                response = requests.get(url, timeout=30)
                response.raise_for_status()

                releases = response.json()

                # Find the latest data release
                for release in releases:
                    tag_name = release.get("tag_name", "")
                    if tag_name.startswith(DATA_RELEASE_TAG_PREFIX):
                        return cast(Dict[str, Any], release)

                logger.warning("No data releases found in GitHub API response")
                return None

            except requests.RequestException as e:
                logger.warning(f"Failed to fetch releases from {base_url}: {e}")
                continue  # Try next fallback URL
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Invalid response from {base_url}: {e}")
                continue  # Try next fallback URL

        logger.error("Failed to fetch releases from all fallback URLs")
        return None

    def _parse_version(self, version_str: str) -> Tuple[int, int, int]:
        """Parse a semantic version string into components."""
        # Strip whitespace and validate input
        version_str = version_str.strip()
        if not version_str:
            raise ValueError("Version string cannot be empty")

        # Check for reasonable string length (prevent excessive input)
        if len(version_str) > 50:
            raise ValueError(f"Version string too long: {len(version_str)} characters. Maximum allowed: 50")

        if version_str.startswith(DATA_RELEASE_TAG_PREFIX):
            version_str = version_str[len(DATA_RELEASE_TAG_PREFIX) :]

        try:
            parts = version_str.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid version format")

            return (int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid version format '{version_str}': {e}")

    def _compare_versions(self, version1: str, version2: str) -> int:
        """Compare two version strings. Returns: -1 if v1 < v2, 0 if equal, 1 if v1 > v2."""
        try:
            v1_parts = self._parse_version(version1)
            v2_parts = self._parse_version(version2)

            if v1_parts < v2_parts:
                return -1
            elif v1_parts > v2_parts:
                return 1
            else:
                return 0
        except ValueError as e:
            logger.error(f"Version comparison failed: {e}")
            return 0

    def _get_current_version(self) -> Optional[str]:
        """Get the currently installed data version."""
        version_file = self._data_dir / VERSION_INFO_JSON
        if not version_file.exists():
            return None

        try:
            with open(version_file, "r") as f:
                version_info = json.load(f)
            return cast(Optional[str], version_info.get("version"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read version info: {e}")
            return None

    def _save_version_info(self, version: str, release_info: Dict[str, Any]) -> None:
        """Save version information to local file with thread safety."""
        version_info = {
            "version": version,
            "tag_name": release_info.get("tag_name"),
            "published_at": release_info.get("published_at"),
            "download_url": release_info.get("html_url"),
        }

        version_file = self._data_dir / VERSION_INFO_JSON
        with self._version_lock:
            try:
                with open(version_file, "w") as f:
                    json.dump(version_info, f, indent=2)

                # Set secure permissions
                if hasattr(os, "chmod"):
                    os.chmod(version_file, 0o644)

            except OSError as e:
                logger.error(f"Failed to save version info: {e}")

    def _download_file(self, url: str, target_path: Path) -> bool:
        """Download a file from URL to target path."""
        if requests is None:
            logger.error("requests module not available - cannot download files")
            return False

        try:
            response = requests.get(url, timeout=60, stream=True)
            response.raise_for_status()

            with open(target_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Set secure permissions
            if hasattr(os, "chmod"):
                os.chmod(target_path, 0o644)

            return True

        except requests.RequestException as e:
            logger.error(f"Failed to download {url}: {e}")
            return False
        except OSError as e:
            logger.error(f"Failed to write file {target_path}: {e}")
            return False

    def _verify_checksums(self, checksums_file: Path) -> bool:
        """Verify file checksums against checksums.txt."""
        if not checksums_file.exists():
            logger.warning("Checksums file not found, skipping verification")
            return True

        try:
            with open(checksums_file, "r") as f:
                checksum_lines = f.read().strip().split("\n")

            for line in checksum_lines:
                if not line.strip():
                    continue

                parts = line.split(None, 1)
                if len(parts) != 2:
                    continue

                expected_hash, filename = parts
                file_path = self._data_dir / filename

                if not file_path.exists():
                    logger.error(f"File {filename} not found for checksum verification")
                    return False

                # Calculate actual hash
                hasher = hashlib.sha256()
                with open(file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hasher.update(chunk)

                actual_hash = hasher.hexdigest()
                if actual_hash != expected_hash:
                    logger.error(f"Checksum mismatch for {filename}: expected {expected_hash}, got {actual_hash}")
                    return False

            logger.info("All checksums verified successfully")
            return True

        except (OSError, ValueError) as e:
            logger.error(f"Checksum verification failed: {e}")
            return False

    def _download_data_files(self, release_info: Dict[str, Any]) -> bool:
        """Download data files from a GitHub release."""
        assets = release_info.get("assets", [])

        # Create temporary directory for downloads
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Download all assets
            for asset in assets:
                asset_name = asset.get("name", "")
                download_url = asset.get("browser_download_url")

                if not download_url:
                    continue

                if asset_name in [MODELS_YAML, OVERRIDES_YAML, CHECKSUMS_TXT]:
                    target_path = temp_path / asset_name
                    if not self._download_file(download_url, target_path):
                        return False

            # Verify checksums
            checksums_file = temp_path / CHECKSUMS_TXT
            if not self._verify_checksums(checksums_file):
                return False

            # Move files to final location
            for filename in [MODELS_YAML, OVERRIDES_YAML]:
                temp_file = temp_path / filename
                if temp_file.exists():
                    final_path = self._data_dir / filename
                    shutil.move(str(temp_file), str(final_path))

            # Save version info
            version = release_info.get("tag_name", "").replace(DATA_RELEASE_TAG_PREFIX, "")
            self._save_version_info(version, release_info)

            return True

    def should_update_data(self) -> bool:
        """Check if data should be updated based on environment variables."""
        # Check if updates are disabled
        if os.getenv(ENV_DISABLE_DATA_UPDATES, "").lower() in ("1", "true", "yes"):
            logger.info("Data updates disabled by environment variable")
            return False

        # Check if version is pinned
        pinned_version = os.getenv(ENV_DATA_VERSION_PIN)
        if pinned_version:
            current_version = self._get_current_version()
            if current_version == pinned_version:
                logger.info(f"Data version pinned to {pinned_version}, skipping update")
                return False

        return True

    def check_for_updates(self) -> bool:
        """Check if there are newer data files available and update if needed."""
        if not self.should_update_data():
            return False

        # Check for pinned version
        pinned_version = os.getenv(ENV_DATA_VERSION_PIN)
        if pinned_version:
            logger.info(f"Checking for pinned version: {pinned_version}")
            # For pinned versions, we would need to fetch specific release
            # This is a simplified implementation
            return False

        # Get latest release info
        latest_release = self._fetch_latest_data_release()
        if not latest_release:
            logger.info("No data releases found, using bundled data")
            return False

        latest_version = latest_release.get("tag_name", "")
        current_version = self._get_current_version()

        if current_version and self._compare_versions(latest_version, current_version) <= 0:
            logger.info(f"Current version {current_version} is up to date")
            return False

        logger.info(f"Updating data from {current_version or 'bundled'} to {latest_version}")

        # Download and install update
        if self._download_data_files(latest_release):
            logger.info(f"Successfully updated to {latest_version}")
            return True
        else:
            logger.error("Failed to update data files")
            return False

    def _get_bundled_data_content(self, filename: str) -> Optional[str]:
        """Get bundled data file content as fallback with checksum verification."""
        try:
            # Try to load from package data using importlib.resources
            try:
                # Use modern importlib.resources API (Python 3.9+)
                data_package = resources.files("openai_model_registry.data")
                pkg_file = data_package / filename
                if pkg_file.is_file():
                    content = pkg_file.read_text()

                    # Verify checksum using temp file
                    with tempfile.NamedTemporaryFile(mode="w", suffix=f"_{filename}", delete=False) as tmp_file:
                        tmp_file.write(content)
                        tmp_path = Path(tmp_file.name)
                    try:
                        if not self._verify_bundled_file_checksum(tmp_path):
                            logger.error(f"Bundled data file {filename} failed checksum verification")
                            return None
                    finally:
                        tmp_path.unlink(missing_ok=True)

                    return content
            except Exception:
                # Ignore and fall through to filesystem fallback
                pass

            # Always try filesystem fallback regardless of importlib.resources result
            bundled_path = Path(__file__).parent.parent.parent / "data" / filename
            if bundled_path.exists():
                # Verify checksum if available
                if not self._verify_bundled_file_checksum(bundled_path):
                    logger.error(f"Bundled data file {filename} failed checksum verification")
                    return None

                with open(bundled_path, "r") as f:
                    return f.read()

        except (OSError, IOError) as e:
            logger.warning(f"Failed to load bundled data {filename}: {e}")
        return None

    def _verify_bundled_file_checksum(self, file_path: Path) -> bool:
        """Verify checksum of a bundled data file to prevent tampering.

        Args:
            file_path: Path to the bundled data file

        Returns:
            True if checksum is valid or no checksum file exists, False if verification fails
        """
        try:
            # Look for checksum file in the same directory
            checksum_file = file_path.parent / "checksums.txt"
            if not checksum_file.exists():
                # No checksum file means no verification needed (for bundled data)
                logger.debug("No checksum file found for bundled data, skipping verification")
                return True

            # Read expected checksum
            with open(checksum_file, "r") as f:
                checksum_lines = f.read().strip().split("\n")

            filename = file_path.name
            expected_hash = None

            for line in checksum_lines:
                if not line.strip():
                    continue

                parts = line.split(None, 1)
                if len(parts) == 2 and parts[1] == filename:
                    expected_hash = parts[0]
                    break

            if expected_hash is None:
                logger.debug(f"No checksum found for {filename} in bundled checksums")
                return True

            # Calculate actual hash
            hasher = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)

            actual_hash = hasher.hexdigest()

            if actual_hash != expected_hash:
                logger.error(f"Bundled file {filename} checksum mismatch: expected {expected_hash}, got {actual_hash}")
                return False

            logger.debug(f"Bundled file {filename} checksum verified successfully")
            return True

        except (OSError, ValueError) as e:
            logger.warning(f"Failed to verify bundled file checksum for {file_path}: {e}")
            # If checksum verification fails, allow the file to be used (non-critical)
            return True

    def get_data_file_path(self, filename: str) -> Optional[Path]:
        """Get the path to a data file, checking user directory first."""
        # Sanitize filename to prevent path traversal attacks
        if not self._is_safe_filename(filename):
            logger.warning(f"Unsafe filename rejected: {filename}")
            return None

        user_file = self._data_dir / filename

        # Additional security check: ensure resolved path is within data directory
        try:
            resolved_path = user_file.resolve()
            data_dir_resolved = self._data_dir.resolve()

            # Check if the resolved path is within the data directory
            if not str(resolved_path).startswith(str(data_dir_resolved)):
                logger.warning(f"Path traversal attempt blocked: {filename} -> {resolved_path}")
                return None

        except (OSError, RuntimeError) as e:
            logger.warning(f"Path resolution failed for {filename}: {e}")
            return None

        if user_file.exists():
            return user_file

        return None

    def _is_safe_filename(self, filename: str) -> bool:
        """Check if a filename is safe (no path traversal attempts).

        Args:
            filename: The filename to validate

        Returns:
            True if filename is safe, False otherwise
        """
        # Reject empty or None filenames
        if not filename or not filename.strip():
            return False

        # Reject filenames with path separators or traversal attempts
        dangerous_patterns = [
            "..",  # Parent directory traversal
            "/",  # Unix path separator
            "\\",  # Windows path separator
            "\0",  # Null byte
            "\n",  # Newline
            "\r",  # Carriage return
        ]

        for pattern in dangerous_patterns:
            if pattern in filename:
                return False

        # Reject filenames that are too long (potential buffer overflow)
        if len(filename) > 255:
            return False

        # Reject filenames starting with dot (hidden files)
        if filename.startswith("."):
            return False

        # Only allow alphanumeric characters, hyphens, underscores, and dots
        import re

        if not re.match(r"^[a-zA-Z0-9._-]+$", filename):
            return False

        return True

    def get_data_file_content(self, filename: str) -> Optional[str]:
        """Get data file content with fallback priority: (1) Env var, (2) User dir, (3) Bundled."""
        # Check for environment variable override (for tests)
        if filename == "models.yaml":
            env_path = os.getenv("OMR_MODEL_REGISTRY_PATH")
            if env_path and Path(env_path).exists():
                try:
                    with open(env_path, "r") as f:
                        return f.read()
                except (OSError, IOError) as e:
                    logger.warning(f"Failed to read env data file {env_path}: {e}")

        # First try user directory
        user_file = self._data_dir / filename
        if user_file.exists():
            try:
                with open(user_file, "r") as f:
                    return f.read()
            except (OSError, IOError) as e:
                logger.warning(f"Failed to read user data file {filename}: {e}")

        # Fallback to bundled data
        logger.info(f"Using bundled data for {filename}")
        return self._get_bundled_data_content(filename)

    def force_update(self) -> bool:
        """Force update data files regardless of current version."""
        latest_release = self._fetch_latest_data_release()
        if not latest_release:
            logger.error("No data releases found")
            return False

        latest_version = latest_release.get("tag_name", "")
        logger.info(f"Force updating to {latest_version}")

        return self._download_data_files(latest_release)

    def _get_current_version_info(self) -> Optional[Dict[str, Any]]:
        """Get the current version information including date and metadata."""
        version_file = self._data_dir / VERSION_INFO_JSON
        if not version_file.exists():
            return None

        try:
            with open(version_file, "r") as f:
                return cast(Dict[str, Any], json.load(f))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read version info: {e}")
            return None

    def _fetch_all_data_releases(self) -> List[Dict[str, Any]]:
        """Fetch all data releases from GitHub API."""
        if requests is None:
            logger.error("requests module not available - cannot fetch data releases")
            return []

        all_releases = []

        # Try each fallback base URL
        for base_url in GITHUB_API_FALLBACK_BASES:
            try:
                url = self._get_github_api_url("releases", base_url)
                response = requests.get(url, timeout=30)
                response.raise_for_status()

                releases = response.json()

                # Filter for data releases only
                for release in releases:
                    tag_name = release.get("tag_name", "")
                    if tag_name.startswith(DATA_RELEASE_TAG_PREFIX):
                        all_releases.append(release)

                # Sort by version (newest first)
                all_releases.sort(key=lambda x: x.get("tag_name", ""), reverse=True)
                return all_releases

            except requests.RequestException as e:
                logger.warning(f"Failed to fetch releases from {base_url}: {e}")
                continue  # Try next fallback URL
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Invalid response from {base_url}: {e}")
                continue  # Try next fallback URL

        logger.error("Failed to fetch releases from all fallback URLs")
        return []

    def get_accumulated_changes(self, current_version: Optional[str], latest_version: str) -> List[Dict[str, Any]]:
        """Get accumulated changes between current and latest version.

        Args:
            current_version: Current version string (e.g., "data-v1.0.0")
            latest_version: Latest version string (e.g., "data-v1.2.0")

        Returns:
            List of dictionaries containing change information for each version
        """
        if not current_version:
            # If no current version, return just the latest version info
            latest_release = self._fetch_latest_data_release()
            if latest_release:
                return [
                    {
                        "version": latest_version,
                        "date": latest_release.get("published_at"),
                        "description": latest_release.get("body", "No description available"),
                        "url": latest_release.get("html_url"),
                    }
                ]
            return []

        # Fetch all releases to find changes between versions
        all_releases = self._fetch_all_data_releases()
        if not all_releases:
            return []

        changes = []
        found_current = False

        for release in all_releases:
            release_version = release.get("tag_name", "")

            # Stop when we reach the current version
            if release_version == current_version:
                found_current = True
                break

            # Add releases newer than current version
            if self._compare_versions(release_version, current_version) > 0:
                changes.append(
                    {
                        "version": release_version,
                        "date": release.get("published_at"),
                        "description": self._extract_change_summary(release.get("body", "")),
                        "url": release.get("html_url"),
                    }
                )

        # If we didn't find the current version, include all releases up to latest
        if not found_current:
            # Find the latest release and include it
            for release in all_releases:
                if release.get("tag_name") == latest_version:
                    changes.append(
                        {
                            "version": latest_version,
                            "date": release.get("published_at"),
                            "description": self._extract_change_summary(release.get("body", "")),
                            "url": release.get("html_url"),
                        }
                    )
                    break

        # Sort by version (newest first)
        changes.sort(key=lambda x: x["version"], reverse=True)
        return changes

    def _extract_change_summary(self, release_body: str) -> str:
        """Extract a one-sentence summary from release body.

        Args:
            release_body: The full release body text

        Returns:
            One-sentence summary of the changes
        """
        if not release_body:
            return "No description available"

        # Clean up the release body
        lines = release_body.strip().split("\n")

        # Look for the first meaningful line that's not a header
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("**") and len(line) > 10:
                # Take first sentence or first 100 characters
                if "." in line:
                    first_sentence = line.split(".")[0] + "."
                    if len(first_sentence) > 20:  # Make sure it's substantial
                        return first_sentence

                # Fallback to first 100 characters
                if len(line) > 100:
                    return line[:97] + "..."
                return line

        # Fallback to first non-empty line
        for line in lines:
            line = line.strip()
            if line:
                if len(line) > 100:
                    return line[:97] + "..."
                return line

        return "No description available"
