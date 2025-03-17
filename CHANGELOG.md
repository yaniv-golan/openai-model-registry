# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
