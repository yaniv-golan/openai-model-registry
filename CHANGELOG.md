# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2025-03-18

### Added

- Enhanced error handling with new exception hierarchy
- Added `ParameterNotSupportedError` for more precise error reporting
- Added `ConstraintNotFoundError` for missing constraint references
- Added `ConfigResult` class for standardized configuration loading results
- Added comprehensive exception documentation in advanced usage guide
- Added type annotations to improve type safety and mypy compatibility
- Added explicit error handling for network operations and configuration loading

### Changed

- Streamlined logging API by removing individual logging functions from the public interface
- Simplified logging documentation in advanced usage guide to focus on essential information
- Improved type safety throughout the codebase with proper annotations
- Enhanced configuration loading with better error reporting and handling
- Refactored model version validation to use specific exception types
- Updated documentation to include detailed exception handling examples
- Improved error messages with more context and troubleshooting information

### Fixed

- Fixed type annotations in logging module to properly support Optional parameters
- Fixed tests to handle structured logging data correctly
- Removed legacy `_log` function and updated all code to use direct logging functions
- Fixed mypy errors related to logging implementation
- Fixed mypy type errors in registry and configuration handling
- Fixed handling of configuration results in version comparison logic
- Fixed documentation build configuration for mkdocstrings 0.29.0
- Fixed potential issues with None values in configuration data
- Fixed thread safety issue in registry cleanup method
- Fixed resource leak in network requests by properly closing response objects
- Fixed thread safety issue in cleanup method to prevent race conditions
- Fixed race condition in configuration refresh by adding proper locking around version check
- Fixed duplicate alias detection to prevent multiple models using the same alias

## [0.3.0] - 2025-03-17

### Added

- Implemented caching for get_capabilities using LRU cache with configurable size
- Implemented semantic versioning comparison for registry updates
- Added validation after registry reload to verify successful loading
- Added timeout to HTTP requests to prevent indefinite hanging
- Added handling for NaN and infinity values in NumericConstraint
- Added test coverage improvements
- Added support for new model types (gpt-4.5-preview and o3-mini)

### Changed

- Added packaging dependency for semantic versioning support
- Optimized performance by pre-compiling regex patterns
- Improved error handling for file operations and HTTP requests
- Type checking and validation enhancements in constraint deserialization
- Updated documentation generation with mkdocstrings 0.29.0
- Streamlined CI/CD workflows to eliminate redundant processes

### Fixed

- Added thread safety to the singleton instance creation in ModelRegistry
- Fixed duplicate network requests in check_for_updates method
- Fixed unchecked None return in _save_cache_metadata
- Fixed missing write permission check in config directory creation
- Fixed unsafe callback usage in logging by adding exception handling
- Fixed inconsistent error parameter type in ModelNotSupportedError
- Fixed calendar date validation in ModelVersion
- Fixed shared references issue by using deepcopy for constraints dictionary
- Fixed documentation build process in GitHub Actions

## [0.2.2] - 2024-03-01

### Added

- Initial public release of the OpenAI Model Registry
