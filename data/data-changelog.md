# Data Changelog

This file tracks changes to the model registry data files (models.yaml and overrides.yaml).

## Format

Each entry should include:

- **Version**: Semantic version (e.g., v1.0.0)
- **Date**: Release date in YYYY-MM-DD format
- **Changes**: List of changes made

## Changelog

### v1.0.2 - 2025-01-15

**GPT-5 Model Specifications Update**

Critical fixes to GPT-5 model specifications to align with OpenAI's official Responses API documentation and current pricing.

**Models Added:**

- **gpt-4.5-preview**: Added as deprecated model (sunset 2025-08-07) for completeness and historical reference
- **gpt-oss-120b**: Large open-weight model for data centers and high-end desktops (Apache 2.0 license)
- **gpt-oss-20b**: Medium open-weight model for most desktops and laptops (Apache 2.0 license)

**Models Updated:**

- **gpt-5**: Fixed context window allocation (272k input/400k total), updated pricing to official rates ($1.25/$10.00 per 1M tokens), added missing parameters (reasoning_effort with minimal option, verbosity), changed max_tokens to max_output_tokens for Responses API compatibility, removed audio from input modalities, updated web search billing to $10/1k calls
- **gpt-5-chat-latest**: Fixed context window to 128k (non-reasoning variant), applied same parameter and pricing updates as gpt-5
- **gpt-5-mini**: Fixed context window allocation, updated pricing scaling, added missing parameters, applied modality and billing fixes
- **gpt-5-nano**: Fixed context window allocation, updated pricing scaling, added missing parameters (text-only variant), applied billing fixes

**Configuration Changes:**

- Updated web search billing from $25/1k to $10/1k calls for GPT-5 family models
- Changed billing policy from "included_in_call_fee" to "billed_at_model_rate"
- Added support for new GPT-5 capabilities: file_search and image_generation
- Enhanced parameter validation with proper type specifications
- Added licensing field for open-weight models with Apache 2.0 license information

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
