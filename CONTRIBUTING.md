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
2. Write your code and tests
3. Update documentation if necessary
4. Ensure all tests pass and pre-commit checks succeed
5. Submit a pull request to the main repository

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
