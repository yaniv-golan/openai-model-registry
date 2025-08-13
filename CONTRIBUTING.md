# Contributing to OpenAI Model Registry

Thank you for considering contributing to the OpenAI Model Registry! We welcome contributions of all kinds, from bug fixes to feature enhancements, documentation improvements, and more.

## Development Environment

This project uses Poetry for dependency management. Here's how to set up your development environment:

```bash
# Install Poetry if you don't have it already
curl -sSL https://install.python-poetry.org | python3 -

# Clone the repository
git clone https://github.com/yourusername/openai-model-registry.git
cd openai-model-registry

# Install dependencies
poetry install

# Activate the virtual environment
poetry shell
```

## Pre-commit Hooks

We use pre-commit hooks to ensure code quality. Install them with:

```bash
poetry run pre-commit install
```

You can manually run the pre-commit checks with:

```bash
poetry run pre-commit run --all-files
```

## Testing

Run tests to ensure your changes don't break existing functionality:

```bash
# Run all tests
poetry run pytest

# Run specific tests
poetry run pytest tests/test_registry.py
```

## Pull Request Process

1. Fork the repository and create a branch for your feature or bug fix
1. Write your code and tests
1. Update documentation if necessary
1. Ensure all tests pass and pre-commit checks succeed
1. Submit a pull request to the main repository

## Code Style

We follow these conventions:

- PEP 8 style guide for Python code
- Type hints for all function arguments, return types, and variables
- Docstrings following Google style
- Black for code formatting
- Ruff for linting
- Maximum line length of 79 characters

## Versioning

We use [Semantic Versioning](https://semver.org/). Please don't bump version numbers in your PR; the maintainers will handle this.

## License

By contributing to this project, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).

## Questions?

If you have any questions or need help, please open an issue on GitHub or contact the maintainers directly.

## Model Information Management

The model registry maintains information about OpenAI models and their capabilities in YAML configuration files. These files define which models are supported, their capabilities, and the constraints on their parameters.

### Configuration Files Location

Model information is stored in YAML files packaged with the library under `openai_model_registry/data/`:

1. **`models.yaml`**: Contains model definitions, capabilities, and inline parameters
1. **`overrides.yaml`**: Contains provider-specific overrides

### Structure of `models.yaml`

This file has the following key sections:

1. **`version`**: The version of the model data schema
1. **`models`**: Contains each model definition; dated variants include a date in the name
   - Each model entry includes:
     - `context_window`: Maximum token limit for input
     - `max_output_tokens`: Maximum tokens the model can output
     - `supports_structured`: Boolean indicating if structured output is supported
     - `supports_streaming`: Boolean indicating if streaming is supported
     - `parameters`: Inline parameter definitions for validation (type, min/max, enum)
     - `description`: Short description of the model
     - `min_version`: Date information for version validation
1. Aliases are represented as separate named models where needed; global alias blocks are not used

Example model entry:

```yaml
gpt-4o-2024-08-06:
  context_window: 128000
  max_output_tokens: 16384
  supports_structured: true
  supports_streaming: true
  supported_parameters:
    - ref: "numeric_constraints.temperature"
      max_value: null
    - ref: "numeric_constraints.top_p"
      max_value: null
  description: "Initial release with 16k output support"
  min_version:
    year: 2024
    month: 8
    day: 6
```

### Inline Parameters

Parameters are defined inline per model, for example:

```yaml
parameters:
  temperature:
    type: number
    min: 0.0
    max: 2.0
  response_format:
    type: enum
    enum: ["json", "text"]
```

### How to Add or Update Models

1. **Adding a new model**:

   - Add a new entry under `models` in `models.yaml`
   - Use the format `model-name-YYYY-MM-DD` for the key
   - Fill in all required fields (context_window, max_output_tokens, etc.)
   - Define parameters inline under the `parameters` block

1. **Updating an existing model**:

   - Locate the model entry in `dated_models`
   - Update the relevant fields as needed
   - Consider adding a new dated version rather than modifying existing ones if the changes are significant

1. **Adding new parameter constraints**:

   - Add new entries to the appropriate section in `parameter_constraints.yml`
   - Follow the existing format for the type of constraint (numeric or enum)

### Testing Your Changes

After making changes to the configuration files:

1. Run the test suite to verify the changes don't break existing functionality:

   ```bash
   poetry run pytest
   ```

1. Create a test that uses the model you added or modified to ensure it's correctly loaded:

   ```python
   def test_new_model_capabilities():
       registry = ModelRegistry()
       capabilities = registry.get_capabilities("new-model")
       assert capabilities.max_output_tokens == expected_value
   ```

### Best Practices

1. **Maintain backward compatibility** when possible
1. **Document changes** in CHANGELOG.md
1. **Use semantic versioning** for library releases
1. **Be conservative** with parameter constraints to avoid false positives
1. **Add tests** for any new models or constraints
1. **Update documentation** if you add new constraint types or model parameters

## Release Documentation

For maintainers and contributors involved in the release process, see:

- [Release Checklist](docs/contributing/RELEASE_CHECKLIST.md) - Step-by-step release process
- [Release Workflow](docs/contributing/RELEASE_WORKFLOW.md) - Detailed workflow documentation
