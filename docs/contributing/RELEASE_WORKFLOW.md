# Release & Hot-Fix Workflow

This document explains how to cut a new feature release, data release, or hot-fix in the OpenAI Model Registry project.

## Table of Contents

- [Branching Model](#branching-model)
- [Release Types](#release-types)
- [Library Release Workflow](#library-release-workflow)
- [Data Release Workflow](#data-release-workflow)
- [Hot-Fix Workflow](#hot-fix-workflow)
- [Do's and Don'ts](#dos-and-donts)
- [Troubleshooting](#troubleshooting)

## Branching Model

- **`main`** – the only long-lived branch. All daily work happens here.
- **Tags** – every published version (`v1.0.0`, `v1.0.1`, `data-v1.0.0`) is an *annotated* git tag on `main`.
- **Hot-fix branch** – created *only if* you must fix the current release *without* pulling in unreleased work that is already on `main`. Delete it right after the tag is pushed.

## Release Types

### 1. Library Releases

Library releases contain the Python package code and are published to PyPI.

- **Tag Format**: `v1.0.0`, `v1.0.1`, `v1.1.0`
- **RC Format**: `v1.0.0-rc1`, `v1.0.0-rc2`
- **Publishing**:
  - RC → TestPyPI
  - Final → PyPI

### 2. Data Releases

Data releases contain model configuration files and are published as GitHub releases.

- **Tag Format**: `data-v1.0.0`, `data-v1.0.1`
- **RC Format**: `data-v1.0.0-rc1`, `data-v1.0.0-rc2`
- **Publishing**: GitHub Releases with data packages

## Library Release Workflow

### Before Writing Code

1. Make sure you are on `main` and up-to-date:

   ```bash
   git switch main
   git pull --ff-only origin main
   ```

1. Create a short feature branch *(optional but recommended)*:

   ```bash
   git switch -c feature/<short-name>
   ```

1. Implement the feature, update tests, **update `CHANGELOG.md` incrementally**.

1. Open a PR (even if you merge it yourself) – CI must be green.

### Creating a Release Candidate

1. Merge your PR into `main`.

1. Verify `CHANGELOG.md` and docs are ready.

1. Run pre-release validation:

   ```bash
   ./scripts/release/create-rc.sh
   ```

1. Create RC tag:

   ```bash
   ./scripts/release/create-rc.sh 1.0.0 1
   ```

1. **CI automatically**:

   - Builds the package
   - Runs tests
   - Publishes to TestPyPI
   - Creates GitHub release (marked as prerelease)

1. **Test the RC**:

   ```bash
   pip install --index-url https://test.pypi.org/simple/ \
     --extra-index-url https://pypi.org/simple/ \
     "openai-model-registry==1.0.0rc1"
   ```

1. **Verify functionality**:

   ```bash
   python -c "import openai_model_registry; print('✅ Import works')"
   python -c "from openai_model_registry import ModelRegistry, RegistryConfig; registry = ModelRegistry(RegistryConfig(auto_update=False)); print('✅ Registry works')"
   ```

### Creating the Final Release

1. After RC testing is complete and successful:

   ```bash
   ./scripts/release/create-final.sh 1.0.0
   ```

1. **CI automatically**:

   - Builds the package
   - Runs tests
   - Publishes to PyPI
   - Creates GitHub release (production)

1. **Verify PyPI publication**:

   ```bash
   pip install openai-model-registry==1.0.0
   python -c "import openai_model_registry; print('✅ PyPI install works')"
   ```

## Data Release Workflow

### Automatic Data Releases

Data releases are automatically triggered when configuration files change:

1. **Edit data files** in `data/`:

   - `models.yaml` - Model definitions
   - `overrides.yaml` - Provider-specific overrides
   - Update `checksums.txt` if needed

1. **Commit and push** to `main`:

   ```bash
   git add data/
   git commit -m "feat: add new model definitions"
   git push origin main
   ```

1. **CI automatically**:

   - Detects config changes
   - Validates YAML files
   - Creates data package
   - Increments version
   - Creates GitHub release

### Contributor Data Release Playbook

Use this checklist when publishing a new data release (or RC):

1. Update files:
   - `data/models.yaml`
   - `data/overrides.yaml`
   - Regenerate `data/checksums.txt`
   - Update `data/data-changelog.md` (summarize changes, breaking notes)
1. Tag and publish:
   - RC: `data-vX.Y.Z-rcN`
   - Final: `data-vX.Y.Z`
   - Attach assets: `models.yaml`, `overrides.yaml`, `checksums.txt`
   - Provide clear Release notes and link to changelog
1. Verify client awareness:
   - Run `omr --format json update check` → exit code `10` indicates an available update
   - In code: `ModelRegistry.check_for_updates()` / `get_update_info()` returns latest
   - Optionally notify via GitHub Releases (watch → releases)
1. Respect environments:
   - Clients may pin via `OMR_DATA_VERSION_PIN`
   - Clients may disable updates via `OMR_DISABLE_DATA_UPDATES`
1. Confirm integrity:
   - Checksums verified for assets
   - Fallback raw URLs (only if needed) should be tag-pinned for immutability

### Manual Data Releases

For manual data releases or RCs:

1. **Create RC**:

   ```bash
   ./scripts/release/create-rc.sh 1.0.0 1 --data
   ```

1. **Create final release**:

   ```bash
   ./scripts/release/create-final.sh 1.0.0 --data
   ```

1. **Test data release**:

   ```bash
   # Download and verify
   curl -L https://github.com/yaniv-golan/openai-model-registry/releases/download/data-v1.0.0/openai-model-registry-data-1.0.0.tar.gz -o data.tar.gz
   tar -xzf data.tar.gz
   cd data-package
   sha256sum -c checksums.txt
   ```

## Hot-Fix Workflow

### Scenario A – Fix is already on `main` and safe to release

1. Ensure `CHANGELOG.md` has a *Hot-fix* entry.

1. Tag and push directly from `main`:

   ```bash
   git switch main && git pull --ff-only
   ./scripts/release/create-final.sh 1.1.1
   ```

### Scenario B – Fix must not include unreleased work on `main`

1. Create a throw-away branch from the last tag:

   ```bash
   git switch -c hotfix/v1.1.1 v1.1.0
   ```

1. Cherry-pick or implement just the necessary commits.

1. Update `CHANGELOG.md` in that branch.

1. Tag & push:

   ```bash
   git tag -a v1.1.1 -m "v1.1.1: security hot-fix"
   git push origin hotfix/v1.1.1 v1.1.1
   ```

1. **After CI turns green**, delete the branch:

   ```bash
   git push origin --delete hotfix/v1.1.1
   git branch -D hotfix/v1.1.1
   ```

## Do's and Don'ts

### Do ✓

- Keep `main` in a releasable state; let CI protect you.
- Use **annotated tags** (`-a`) for every version.
- Update the **CHANGELOG** steadily while you code.
- Delete merged or obsolete branches immediately.
- Test release candidates thoroughly before final release.
- Use the provided scripts for consistent release process.
- Run validation before creating releases.

### Don't ✗

- ✗ Don't create long-lived `release/x.y` branches – history gets messy.
- ✗ Don't manually publish to PyPI – CI handles this automatically.
- ✗ Don't force-push to shared branches or tags.
- ✗ Don't skip RC testing for significant releases.
- ✗ Don't forget to update CHANGELOG.md.

## Troubleshooting

### Common Issues

#### Release Script Fails

```bash
# Check if you're on main branch
git branch --show-current

# Ensure you're up to date
git pull --ff-only origin main

# Check for existing tags
git tag -l | grep v1.0.0
```

#### CI Build Fails

1. **Check GitHub Actions logs** for detailed error messages

1. **Run validation locally**:

   ```bash
   ./scripts/release/create-final.sh
   ```

1. **Test locally**:

   ```bash
   poetry run pytest -v
   poetry build
   python -m twine check dist/*
   ```

#### TestPyPI Installation Fails

```bash
# Try with verbose output
pip install -v --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  "openai-model-registry==1.0.0rc1"

# Check if dependencies are available
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  --dry-run "openai-model-registry==1.0.0rc1"
```

#### Version Mismatch

```bash
# Check current versions
poetry version --short
python -c "import openai_model_registry; print(openai_model_registry.__version__)"

# Update if needed
poetry version 1.0.0
```

### Getting Help

1. **Check CI logs** in GitHub Actions
1. **Review validation output** from CI workflows (build/tests/docs) triggered by the release tag
1. **Test in clean environment** to isolate issues
1. **Check existing tags** to avoid conflicts

## Automation Overview

### GitHub Actions Workflows

1. **[release.yml](https://github.com/yaniv-golan/openai-model-registry/blob/main/.github/workflows/release.yml)** - Library releases

   - Triggered by `v*` and `v*-rc*` tags
   - Builds package, runs tests, publishes to PyPI/TestPyPI
   - Creates GitHub releases

1. **[data-release-enhanced.yml](https://github.com/yaniv-golan/openai-model-registry/blob/main/.github/workflows/data-release-enhanced.yml)** - Data releases

   - Triggered by config file changes or `data-v*` tags
   - Validates YAML, creates data packages
   - Creates GitHub releases

1. **[cross-platform-test.yml](https://github.com/yaniv-golan/openai-model-registry/blob/main/.github/workflows/cross-platform-test.yml)** - Cross-platform testing

   - Tests installation across OS and Python versions
   - Validates package quality and performance

### Scripts

1. **[create-rc.sh](https://github.com/yaniv-golan/openai-model-registry/blob/main/scripts/release/create-rc.sh)** - Create release candidates
1. **[create-final.sh](https://github.com/yaniv-golan/openai-model-registry/blob/main/scripts/release/create-final.sh)** - Create final releases
1. Use GitHub Actions logs for validation (build/tests/docs) instead of local `validate-release.py`

## Related Documentation

- [RELEASE_CHECKLIST.md](/RELEASE_CHECKLIST.md) - Pre-release validation checklist
- [CHANGELOG.md](/CHANGELOG.md) - Version history and changes
- [CONTRIBUTING.md](/CONTRIBUTING.md) - General contribution guidelines
- [ostruct pricing automation](/scripts/ostruct/README.md) - Detector and per-model pricing extraction templates used by CI
