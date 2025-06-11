# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## \[0.7.2\] - 2025-06-11

### Added

- Added `py.typed` file to the package to support PEP 561-style type checking. This allows consumers of the library to type check their code against the library's type hints.
- Added new `o3-pro` model.

## \[0.7.1\] - 2025-05-31

### Added

- **Azure OpenAI Documentation**: Added comprehensive guidance for Azure OpenAI users
  - New dedicated [Azure OpenAI Usage Guide](docs/user-guide/azure-openai.md) explaining platform limitations
  - Detailed explanation of why standard Azure endpoints don't support `web_search_preview` tool
  - Code examples for detecting Azure endpoints and implementing graceful fallbacks
  - Alternative approaches: Azure Assistants API (Browse tool) and external search integration
  - Platform-aware capability detection patterns and best practices

### Changed

- **Enhanced Documentation Discoverability**: Added Azure guidance references across multiple documentation entry points
  - Added warning callout in Web Search Support section of model capabilities guide
  - Added Azure user notice in main documentation index and README
  - Added Azure guide to user guide navigation and features list
  - Improved user experience for Azure OpenAI users to prevent runtime errors

### Technical Details

- Documentation-only release - no code changes or breaking changes
- Addresses user confusion about web search capabilities on Azure endpoints
- Provides immediate guidance while maintaining backward compatibility
- Empowers developers to implement correct Azure-specific logic in their applications

## \[0.7.0\] - 2025-05-31

### Added

- **Web Search Capability Support**: Added comprehensive support for tracking web search capabilities across OpenAI models
  - Added `supports_web_search` boolean field to `ModelCapabilities` class
  - Added support for Chat Completions API search-preview models (`gpt-4o-search-preview`, `gpt-4o-mini-search-preview`)
  - Added support for Responses API tool-based web search (GPT-4o, GPT-4.1, O-series models)
  - Added aliases for search-preview models for easier access
- **Object Constraint Type**: Added new `ObjectConstraint` class for validating object/dictionary parameters
  - Supports required keys validation
  - Supports allowed keys restriction
  - Enhanced constraint validation system to handle object parameters
- **Enhanced Documentation**: Added comprehensive web search documentation
  - Detailed explanation of Chat API vs Responses API web search approaches
  - Complete usage examples showing how to detect and use web search capabilities
  - Clear guidance on API endpoint selection based on model type
- **New Models**: Added support for 2 new search-preview model variants
  - `gpt-4o-search-preview-2025-03-11`: GPT-4o with built-in web search (always searches)
  - `gpt-4o-mini-search-preview-2025-03-11`: GPT-4o Mini with built-in web search (always searches)

### Changed

- **Enhanced Model Capabilities**: Updated 11 existing models with web search capability flags
  - GPT-4o series: `supports_web_search: true` (Responses API tool-based)
  - GPT-4.1 series: `supports_web_search: true` for regular and mini variants
  - O-series models: `supports_web_search: true` for all reasoning models (o1, o3, o4)
  - GPT-4.1-nano: `supports_web_search: false` (explicitly unsupported per OpenAI docs)
- **Type System Enhancement**: Updated constraint type hints throughout codebase
  - Enhanced `ModelCapabilities._constraints` to support `ObjectConstraint`
  - Updated `ModelRegistry._constraints` type annotations
  - Updated constraint validation methods to handle object types
- **Improved API Exports**: Added `ObjectConstraint` to public API exports in `__init__.py`

### Technical Details

- Web search capability tracking follows unified boolean flag approach for simplicity
- Registry indicates *capability availability*, application layer handles *API usage differences*
- Maintains backward compatibility - all existing code continues to work unchanged
- Search-preview models are documented as "always search" behavior in descriptions
- Tool-based models use conditional search via Responses API `web_search_preview` tool
- Added comprehensive test coverage for web search capability detection
- Enhanced documentation with practical usage examples and troubleshooting guidance
- **Schema Version**: Updated models.yml schema from v1.1.0 to v1.2.0 to reflect web search capability additions

## \[0.6.1\] - 2025-05-28

### Fixed

- Fixed broken URLs in registry refresh functionality that were pointing to non-existent repository
- Fixed refresh logic to properly handle validation-only mode and fetch failures
- Updated remote configuration URLs to point to correct repository: `yaniv-golan/openai-model-registry`
- Improved error handling in `refresh_from_remote` method to fail gracefully when remote fetch fails
- Fixed test failures related to refresh validation and fetch error scenarios

### Technical Details

- Updated both `refresh_from_remote` and `check_for_updates` methods to use correct GitHub repository URLs
- Restructured refresh logic to always fetch and validate remote config before checking version updates
- Enhanced validation-only mode to properly return `VALIDATED` status after successful remote validation
- Improved error propagation when remote configuration fetch fails

## \[0.6.0\] - 2025-05-26

### Added

- Added proper cross-platform directory handling using `platformdirs`
- Added `get_user_data_dir()` function for programmatically updated files
- Added `ensure_user_data_dir_exists()` function for data directory management
- Added `copy_default_to_user_data()` function for copying defaults to data directory
- Added comprehensive testing documentation for pytest and pyfakefs usage
- Added user guide section for testing applications that use the registry

### Changed

- **BREAKING (Internal)**: Model registry files now stored in user data directory instead of config directory
  - Linux: `~/.local/share/openai-model-registry/` instead of `~/.config/openai-model-registry/`
  - macOS/Windows: No change (same directory used for both data and config)
- Enhanced cross-platform path resolution following XDG Base Directory specification
- Updated registry update functionality to write to data directory
- Improved backward compatibility with fallback to legacy config directory locations

### Technical Details

- Follows XDG Base Directory specification: data files go in data directories, config files in config directories
- Maintains full backward compatibility by checking config directory as fallback
- Enhanced documentation for developers testing code that depends on this library
- No breaking changes to public API - all existing code continues to work

## \[0.5.0\] - 2025-05-23

### Added

- Added support for new GPT-4.1 series models (gpt-4.1, gpt-4.1-mini, gpt-4.1-nano) with 1M context window and 32K output tokens
- Added support for O-series reasoning models (o1-mini, o3, o4-mini) with specialized parameter constraints
- Added support for GPT-4.5 preview model (deprecated mid-2025)
- Added new model aliases for easier access to latest model versions
- Added reasoning_effort parameter constraint for O3 and O4-mini models with enum values (low, medium, high)
- Added comprehensive deprecation metadata support with null values for unknown deprecation timelines
- Added proper semantic versioning support for schema backward compatibility

### Changed

- Updated constraint loading to support nested parameter constraint references (e.g., "numeric_constraints.temperature")
- Enhanced parameter validation system to handle model-specific parameter restrictions
- Improved model capability detection for new model features and limitations
- Updated model release dates to match official OpenAI documentation (gpt-4o-2024-05-13 instead of gpt-4o-2024-08-06)
- Updated streaming capabilities for O-series models (o1-mini now supports streaming, o1-2024-12-17 does not)
- Enhanced deprecation system to handle null dates gracefully for active models
- Improved schema versioning to support true backward compatibility between v1.0.0 and v1.1.0+
- Updated registry loading to properly handle both legacy and current schema formats
- Enhanced min_version parsing to support both dictionary and string formats

### Fixed

- Fixed constraint loading mechanism to properly handle nested YAML structure in parameter constraints
- Fixed parameter validation tests to work with updated constraint reference format
- Fixed registry initialization tests to handle new constraint structure properly
- Fixed deprecation date validation to skip ordering checks when dates are null
- Fixed sunset header generation to handle null deprecation dates
- Fixed alias resolution in registry capabilities lookup
- Fixed test suite to use corrected model names and schema versions
- Fixed schema compatibility to properly support semantic versioning principles
- Fixed all tests to pass with proper backward compatibility implementation

## \[0.4.0\] - 2025-03-18

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

## \[0.3.0\] - 2025-03-17

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
- Fixed unchecked None return in \_save_cache_metadata
- Fixed missing write permission check in config directory creation
- Fixed unsafe callback usage in logging by adding exception handling
- Fixed inconsistent error parameter type in ModelNotSupportedError
- Fixed calendar date validation in ModelVersion
- Fixed shared references issue by using deepcopy for constraints dictionary
- Fixed documentation build process in GitHub Actions

## \[0.2.2\] - 2024-03-01

### Added

- Initial public release of the OpenAI Model Registry
