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

Model information is stored in two main YAML files located in the `src/openai_model_registry/config/` directory:

1. **`models.yml`**: Contains model definitions, capabilities, and references to parameter constraints
1. **`parameter_constraints.yml`**: Defines reusable parameter constraints that can be referenced by models

### Structure of `models.yml`

This file has the following key sections:

1. **`version`**: The version of the model data schema
1. **`dated_models`**: Contains each model variant with a specific date in its name
   - Each model entry includes:
     - `context_window`: Maximum token limit for input
     - `max_output_tokens`: Maximum tokens the model can output
     - `supports_structured`: Boolean indicating if structured output is supported
     - `supports_streaming`: Boolean indicating if streaming is supported
     - `supported_parameters`: List of parameters the model accepts, with references to constraints
     - `description`: Short description of the model
     - `min_version`: Date information for version validation
1. **`aliases`**: Maps generic model names to their dated versions

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

### Structure of `parameter_constraints.yml`

This file defines reusable constraints for model parameters, organized by type:

1. **`numeric_constraints`**: For numerical parameters like temperature or top_p
   - Each entry includes type, min/max values, description, and allowed data types
1. **`enum_constraints`**: For parameters with specific allowed values
   - Each entry includes type, allowed values list, and description

Example constraint:

```yaml
temperature:
  type: numeric
  min_value: 0.0
  max_value: 2.0
  description: Controls randomness in the output
  allow_float: true
  allow_int: true
```

### How to Add or Update Models

1. **Adding a new model**:

   - Add a new entry under `dated_models` in `models.yml`
   - Use the format `model-name-YYYY-MM-DD` for the key
   - Fill in all required fields (context_window, max_output_tokens, etc.)
   - Reference existing parameter constraints using the `ref` field
   - Add an alias in the `aliases` section if needed

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
