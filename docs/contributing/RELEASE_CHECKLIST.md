# Release Readiness Checklist for OpenAI Model Registry

This checklist covers validation steps **after** you decide a version is ready for release.

For **detailed release workflow** and **branching rules**, see the full guide in this section ([Release Workflow](RELEASE_WORKFLOW.md)).

## 🏷️ Dynamic Versioning & Release Process

**IMPORTANT**: This project uses semantic versioning with Git tags for releases.

### Version Management

- ✅ **DO**: Create Git tags to set versions (`git tag v1.0.0` or `git tag v1.0.0-rc1`)
- ✅ **DO**: Use semantic versioning (MAJOR.MINOR.PATCH)
- ✅ **Verification**: Check version consistency with `poetry version --short`

### Release Types

#### 1. Library Releases

- **Current Version**: v1.0.0 (First stable release)
- **Release Candidates**: `v1.0.0-rc1`, `v1.0.0-rc2`, etc.
- **Final Releases**: `v1.0.0`, `v1.0.1`, `v1.1.0`, etc.
- **Publishing**: RC → TestPyPI, Final → PyPI

#### 2. Data Releases

- **Current Version**: data-v1.0.0 (First data format release)
- **Release Candidates**: `data-v1.0.0-rc1`, `data-v1.0.0-rc2`, etc.
- **Final Releases**: `data-v1.0.0`, `data-v1.0.1`, etc.
- **Publishing**: GitHub Releases with data packages

### Release Candidate (RC) Process

1. **Create RC tag:**

   ```bash
   # Library RC
   ./scripts/release/create-rc.sh 1.0.0 1

   # Data RC
   ./scripts/release/create-rc.sh 1.0.0 1 --data
   ```

1. **CI automatically handles:**

   - ✅ Building the package from the tagged commit
   - ✅ Publishing library RCs to TestPyPI
   - ✅ Creating GitHub release with artifacts
   - ✅ Marking as prerelease

1. **Test RC:**

   ```bash
   # Library RC from TestPyPI
   pip install --index-url https://test.pypi.org/simple/ \
     --extra-index-url https://pypi.org/simple/ \
     "openai-model-registry==1.0.0rc1"

   ```

# Data RC from GitHub Releases (see Releases tab in repository)

````

4. **Verify RC works:**

```bash
python -c "import openai_model_registry; print('✅ Import successful')"
python -c "from openai_model_registry import ModelRegistry, RegistryConfig; registry = ModelRegistry(RegistryConfig(auto_update=False)); print('✅ Registry creation successful')"
````

### Final Release Process

1. **Create final tag:**

   ```bash
   # Library release
   ./scripts/release/create-final.sh 1.0.0

   # Data release
   ./scripts/release/create-final.sh 1.0.0 --data
   ```

1. **CI automatically publishes:**

   - ✅ Library releases to PyPI
   - ✅ Data releases to GitHub Releases
   - ✅ Creates comprehensive release notes

### Common Pitfalls to Avoid

- 🚫 **Don't skip RC testing** - Always test release candidates thoroughly
- 🚫 **Don't manually publish to PyPI** - CI handles this automatically
- 🚫 **Don't forget to test both library and data releases** - They're separate but related
- 🚫 **Don't assume TestPyPI install worked** - Always verify functionality

## Pre-Release Testing Strategy

### 1. Automated Validation (REQUIRED)

Run the automated validation script:

```bash
# Full validation with clean installation tests
./scripts/release/create-rc.sh

# Quick validation (skip slow clean install tests)
./scripts/release/create-final.sh
```

This script performs:

- ✅ Version consistency checks
- ✅ pyproject.toml validation
- ✅ Package building (wheel + sdist)
- ✅ Dependency resolution testing
- ✅ Test suite execution
- ✅ Documentation building
- ✅ Clean virtual environment installation testing

You can also run individual commands manually:

```bash
# Run tests
poetry run pytest -v

# Check package
poetry check
poetry build
python -m twine check dist/*

# Test installation
pip install dist/*.whl
```

### 2. Manual Testing (RECOMMENDED)

#### Test Core Functionality

```bash
# Test basic registry operations
python -c "
from openai_model_registry import ModelRegistry, RegistryConfig
config = RegistryConfig(auto_update=False)
registry = ModelRegistry(config)
print(f'Registry has {len(registry.list_models())} models')
"

# Test model lookup
python -c "
from openai_model_registry import ModelRegistry, RegistryConfig
config = RegistryConfig(auto_update=False)
registry = ModelRegistry(config)
try:
    model = registry.get_model('gpt-4')
    print(f'Model: {model.name}')
except Exception as e:
    print(f'Model lookup: {e}')
"
```

#### Test Update Functionality

```bash
# Test update information
python -c "
from openai_model_registry import ModelRegistry, RegistryConfig
config = RegistryConfig(auto_update=False)
registry = ModelRegistry(config)
update_info = registry.get_update_info()
print(f'Update available: {update_info.update_available}')
print(f'Current version: {update_info.current_version}')
"
```

#### Test in Fresh Virtual Environments

```bash
# Test Python 3.10
python3.10 -m venv test_env_310
source test_env_310/bin/activate
pip install dist/*.whl
python -c "import openai_model_registry; print('✅ Python 3.10 works')"
deactivate

# Test Python 3.11
python3.11 -m venv test_env_311
source test_env_311/bin/activate
pip install dist/*.whl
python -c "import openai_model_registry; print('✅ Python 3.11 works')"
deactivate

# Test Python 3.12
python3.12 -m venv test_env_312
source test_env_312/bin/activate
pip install dist/*.whl
python -c "import openai_model_registry; print('✅ Python 3.12 works')"
deactivate
```

### 3. Cross-Platform Testing

The cross-platform workflow automatically tests:

- ✅ Installation on Ubuntu, Windows, macOS
- ✅ Python 3.10, 3.11, 3.12 compatibility
- ✅ Wheel and sdist installation
- ✅ Import performance
- ✅ Memory usage
- ✅ Dependency resolution

## Release Validation Checklist

### Pre-Release Validation

- [ ] **Automated validation passes**: CI workflows (build/tests/docs) are green
- [ ] **All tests pass**: `poetry run pytest -v`
- [ ] **Package builds cleanly**: `poetry build`
- [ ] **Documentation builds**: Check docs build in CI
- [ ] **Version consistency**: Poetry and package versions match

### Package Quality

- [ ] **Package size is reasonable**: Check `dist/` directory (\< 10MB for wheel)
- [ ] **Both wheel and sdist created**: Check `dist/` directory
- [ ] **Package metadata is correct**: `python -m twine check dist/*`
- [ ] **Dependencies are correct**: `poetry show --tree`

### Functionality Testing

- [ ] **Basic import works**: `python -c "import openai_model_registry"`
- [ ] **Registry creation works**: Test ModelRegistry instantiation
- [ ] **Model lookup works**: Test getting models from registry
- [ ] **Update system works**: Test update information retrieval
- [ ] **Configuration system works**: Test RegistryConfig options

### Cross-Platform Testing

- [ ] **CI tests pass**: All GitHub Actions workflows green
- [ ] **Multiple Python versions**: 3.10, 3.11, 3.12 tested
- [ ] **Multiple OS**: Ubuntu, Windows, macOS tested
- [ ] **Installation methods**: wheel, sdist, and PyPI installation tested

## GitHub Actions CI Validation

Ensure your GitHub Actions CI is passing:

- [ ] **Main CI workflow**: Tests pass on all supported Python versions and OS
- [ ] **Cross-platform tests**: Installation tests pass
- [ ] **Documentation builds**: Docs build successfully
- [ ] **Security scans**: No security issues found

## Final Steps Before Release

1. **Run comprehensive validation:**

   ```bash
   ./scripts/release/create-rc.sh
   ```

1. **Verify CI is green** on the main branch

1. **Update CHANGELOG.md** with version changes

1. **Create RC first** (recommended):

   ```bash
   ./scripts/release/create-rc.sh 1.0.0 1
   ```

1. **Test RC thoroughly** from TestPyPI

1. **Create final release**:

   ```bash
   ./scripts/release/create-final.sh 1.0.0
   ```

1. **CI automatically publishes to PyPI** (no manual action needed)

## Post-Release Verification

After publishing to PyPI:

1. **Test installation from PyPI:**

   ```bash
   pip install openai-model-registry==<VERSION>
   python -c "import openai_model_registry; print('✅ PyPI installation works')"
   ```

1. **Test in fresh environment:**

   ```bash
   python -m venv test_env
   source test_env/bin/activate  # or test_env\Scripts\activate on Windows
   pip install openai-model-registry==<VERSION>
   python -c "from openai_model_registry import ModelRegistry; print('✅ Fresh install works')"
   deactivate
   ```

1. **Verify GitHub release** has correct artifacts and release notes

1. **Test data releases** if applicable

## Troubleshooting

### Common Issues

1. **Version mismatch**: Ensure poetry and package versions match
1. **Test failures**: Run `poetry run pytest -v` to see detailed errors
1. **Build failures**: Check `poetry build` output for errors
1. **Import errors**: Test in clean virtual environment

### Getting Help

- **CI logs**: Check GitHub Actions for detailed error messages
- **Local testing**: Use `poetry run pytest -q` and `poetry run mkdocs build` for smoke testing
- **Documentation**: See [Release Workflow](RELEASE_WORKFLOW.md) for detailed procedures

## Related Files

- [scripts/release/create-rc.sh](https://github.com/yaniv-golan/openai-model-registry/blob/main/scripts/release/create-rc.sh) - Create release candidates
- [scripts/release/create-final.sh](https://github.com/yaniv-golan/openai-model-registry/blob/main/scripts/release/create-final.sh) - Create final releases
- Release automation uses shell scripts and GitHub Actions; `validate-release.py` is no longer used
- [.github/workflows/release.yml](https://github.com/yaniv-golan/openai-model-registry/blob/main/.github/workflows/release.yml) - Library release workflow
- [.github/workflows/data-release-enhanced.yml](https://github.com/yaniv-golan/openai-model-registry/blob/main/.github/workflows/data-release-enhanced.yml) - Data release workflow
- [.github/workflows/cross-platform-test.yml](https://github.com/yaniv-golan/openai-model-registry/blob/main/.github/workflows/cross-platform-test.yml) - Cross-platform testing
