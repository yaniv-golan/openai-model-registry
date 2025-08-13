# Data Changelog

This file tracks changes to the model registry data files (models.yaml and overrides.yaml).

## Format

Each entry should include:

- **Version**: Semantic version (e.g., v1.0.0)
- **Date**: Release date in YYYY-MM-DD format
- **Changes**: List of changes made

## Changelog

### v1.0.0 - 2025-07-15

**First release of new data format**

- New data format using models.yaml and overrides.yaml structure
- Schema version 1.0.0 for the new data format
- Comprehensive model definitions with capabilities, pricing, and constraints
- Independent data versioning system separate from library releases

**Models Added:**

- Complete OpenAI model catalog including GPT-4o, GPT-4, GPT-3.5, and specialized models
- All models with detailed capabilities, context windows, and pricing information
- Support for multimodal models with vision and audio capabilities

**Models Updated:**

- Unified pricing format to per-million-token basis
- Comprehensive capability definitions for all models
- Structured model metadata with provider information

**Models Removed:**

- None (first release of new format)

______________________________________________________________________

## Template for Future Releases

```
### vX.Y.Z - YYYY-MM-DD

**Brief description of changes**

**Models Added:**
- model-name: Brief description

**Models Updated:**
- model-name: What changed

**Models Removed:**
- model-name: Reason for removal

**Configuration Changes:**
- Description of any structural changes
```
