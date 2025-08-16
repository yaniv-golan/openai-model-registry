# OMR CLI Reference

The OpenAI Model Registry CLI (`omr`) provides a powerful command-line interface for inspecting, debugging, and managing your model registry data.

## Installation

The CLI requires the optional `[cli]` extra dependencies:

```bash
pip install openai-model-registry[cli]
```

After installation, the `omr` command should be available in your shell.

> **Note**: The core library (`pip install openai-model-registry`) does not include CLI dependencies. You must install the `[cli]` extra to use the `omr` command.

## Quick Start

```bash
# Show help
omr --help

# List all models
omr models list

# Show data source paths
omr data paths

# Check for updates
omr update check

# Clear cache
omr cache clear --yes

# Programmatic model-card access examples
# Parameters-only view
omr --format json models get gpt-4o --parameters-only | jq '.'

# Inspect web-search billing block
omr --format json models get gpt-4o | jq '.billing.web_search'

# Inspect input/output modalities
omr --format json models get gpt-4o | jq '.input_modalities, .output_modalities'

# View per-image pricing tiers (e.g., DALL·E)
omr --format json models get dall-e-3 | jq '.pricing.tiers'
```

## Global Options

These options can be used with any command:

- `--provider <openai|azure>`: Override the active provider (takes precedence over `OMR_PROVIDER` environment variable)
- `--format <table|json|csv|yaml>`: Output format (defaults to `table` for TTY, `json` for non-TTY)
  - **Note**: Not all commands support all formats - see individual command documentation
- `--verbose`, `-v`: Increase verbosity (stackable: `-vv` for more verbose)
- `--quiet`, `-q`: Decrease verbosity (stackable)
- `--debug`: Enable debug-level logging
- `--no-color`: Disable color output
- `--version`: Show version information
- `--help`: Show help information
- `--help-json`: Show help in JSON format for programmatic use

## Commands

### Data Commands (`omr data`)

Inspect data sources and configuration.

#### `omr data paths`

Show resolved data source paths and their precedence:

```bash
omr data paths
omr data paths --format json
```

#### `omr data env`

Show effective OMR environment variables:

```bash
omr data env
omr data env --format json
```

#### `omr data dump`

Dump registry data in various formats:

```bash
# Dump effective (merged) data as JSON
omr data dump --effective

# Dump raw data as YAML
omr data dump --raw --format yaml

# Save to file
omr data dump --effective --output effective.json
```

**Supported formats**: `json`, `yaml` (on TTY, requesting `table`/`csv` falls back to JSON; use `--format yaml` to force YAML)

Options:

- `--raw`: Dump original on-disk/bundled YAML (no provider merge)
- `--effective`: Dump fully merged, provider-adjusted dataset (default)
- `--output FILE`: Write to file instead of stdout

See also: Data files and merge behavior in
[`Advanced Usage → Data files and provider overrides`](advanced-usage.md#data-files-and-provider-overrides).

### Update Commands (`omr update`)

Manage registry data updates.

#### `omr update check`

Check for available updates:

```bash
omr update check
omr update check --format json
```

Exit codes:

- `0`: Up to date
- `10`: Update available (CI-friendly)

#### `omr update apply`

Apply available updates:

```bash
omr update apply
omr update apply --force
```

Options:

- `--force`: Force update even if current version is newer
- `--url URL`: Override update URL

Note: This command writes updated data files (e.g., `models.yaml`, `overrides.yaml`) to the user data directory by default. If `OMR_DATA_DIR` is set, that directory is used. The `OMR_MODEL_REGISTRY_PATH` override is read-only and is never modified by updates.

#### `omr update refresh`

One-shot validate/check/apply wrapper:

```bash
omr update refresh
omr update refresh --validate-only
omr update refresh --force
```

Options:

- `--validate-only`: Only validate remote data without applying
- `--force`: Force refresh even if current version is newer
- `--url URL`: Override update URL

Note: When applying updates (without `--validate-only`), files are written to the user data directory (or `OMR_DATA_DIR` if set). `OMR_MODEL_REGISTRY_PATH` is only used for reading `models.yaml` and is not modified.

#### `omr update show-config`

Show effective update-related configuration:

```bash
omr update show-config
```

### Model Commands (`omr models`)

Inspect and list models.

#### `omr models list`

List all available models:

```bash
# Basic list
omr models list

# JSON format
omr --format json models list

# CSV format with custom columns (including billing)
omr models list --format csv --columns "name,pricing.input_cost_per_unit,pricing.unit,billing.web_search.call_fee_per_1000"

# Filter models
omr models list --filter "gpt-4"
```

Options:

- `--filter EXPR`: Filter models using simple expression
- `--columns COLS`: Comma-separated columns to display (supports dotted paths)

#### `omr models get`

Get detailed information about a specific model:

```bash
# Get effective model data (default)
omr models get gpt-4o

# Get raw model data as YAML
omr models get gpt-4o --raw --format yaml

# Parameters only (effective)
omr --format json models get gpt-4o --parameters-only

# Save to file
omr models get gpt-4o --output gpt-4o.json
```

**Supported formats**: `json`, `yaml` (falls back to JSON for `table`/`csv` with verbose message)

Options:

- `--effective`: Show effective model data with provider overrides (default)
- `--raw`: Show raw model data without provider overrides
- `--output FILE`: Write to file instead of stdout

For how provider overrides are applied, see
[`Advanced Usage → Data files and provider overrides`](advanced-usage.md#data-files-and-provider-overrides).

Tip: To view web-search billing for a model in JSON:

```bash
omr --format json models get gpt-4o | jq '.billing.web_search'
```

### Provider Commands (`omr providers`)

Manage and inspect providers.

#### `omr providers list`

List all available providers:

```bash
omr providers list
omr --format json providers list
```

#### `omr providers current`

Show the currently active provider and its source:

```bash
omr providers current
```

### Cache Commands (`omr cache`)

Manage registry cache.

#### `omr cache info`

Show cache directory and file information:

```bash
omr cache info
omr --format json cache info
```

#### `omr cache clear`

Clear cached registry data files:

```bash
# Interactive confirmation
omr cache clear

# Non-interactive (required for scripts)
omr cache clear --yes
```

**Warning**: This removes cached `models.yaml` and `overrides.yaml` files. The registry will fall back to bundled data until the next update.

## Environment Variables

The CLI respects these environment variables (all prefixed with `OMR_`):

- `OMR_PROVIDER`: Default provider (`openai` or `azure`)
- `OMR_DATA_DIR`: Custom data directory
- `OMR_DISABLE_DATA_UPDATES`: Disable automatic updates (`true`/`false`)
- `OMR_DATA_VERSION_PIN`: Pin to specific data version
- `OMR_MODEL_REGISTRY_PATH`: Override models.yaml path
- `OMR_PARAMETER_CONSTRAINTS_PATH`: Override constraints path

Note: Pricing updates are fetched and merged via CI using [ostruct](https://github.com/yaniv-golan/ostruct). When running locally, you can execute the same workflow via our helper scripts or by invoking `ostruct` with `pipx`.

## Output Formats

**Format Support by Command:**

- **Full support** (table, json, csv, yaml): `models list`, `providers list`, `providers current`, `data paths`, `data env`, `cache info`, `update` commands
- **JSON/YAML only**: `data dump`, `models get` (automatically falls back to JSON for table/csv with verbose message)

### Table Format (Default for TTY)

Human-readable tables with colors and formatting:

```
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Model     ┃ Context Window ┃ Input Cost  ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ gpt-4o    │ 128000         │ $2.5        │
│ gpt-4o-mini│ 128000        │ $0.15       │
└───────────┴────────────────┴─────────────┘
```

Note on narrow terminals:

- Tables render to your current terminal width. If the console isn't wide
  enough to fit all columns, cell contents may be truncated on the right.
- Two-line headers (e.g., "Context\\nWindow") will still display fully, but
  their corresponding column values may be shortened to fit.
- To see more:
  - Reduce columns: `omr models list --columns name,context_window.total`
  - Use a wider terminal or a pager without wrapping: `omr models list | less -S`
  - Switch to machine-friendly formats: `--format json` or `--format yaml`

### JSON Format (Default for non-TTY)

Machine-readable JSON with stable keys:

```json
{
  "models": [
    {
      "name": "gpt-4o",
      "context_window": {
        "total": 128000,
        "output": 16384
      },
      "pricing": {
        "scheme": "per_token",
        "unit": "million_tokens",
        "input_cost_per_unit": 2.5,
        "output_cost_per_unit": 10.0
      }
    }
  ],
  "count": 1
}
```

### CSV Format

Comma-separated values for spreadsheet import:

```csv
name,context_window.total,pricing.input_cost_per_unit,pricing.unit
gpt-4o,128000,2.5,million_tokens
gpt-4o-mini,128000,0.15,million_tokens
```

### YAML Format

Human-readable YAML:

```yaml
provider: openai
models:
  gpt-4o:
    context_window:
      total: 128000
      output: 16384
```

## Common Workflows

### Development and Debugging

```bash
# Check current configuration
omr data env
omr data paths

# List available models with pricing
omr models list --columns "name,pricing.input_cost_per_unit,pricing.output_cost_per_unit,pricing.unit"

# Get detailed model info
omr models get gpt-4o --effective

# Switch provider and compare
omr --provider azure models get gpt-4o --effective
```

### CI/CD Integration

```bash
# Check for updates (exit code 0 = up to date, 10 = update available)
omr update check --format json

# Apply updates in CI
omr update apply --force

# Validate data without applying
omr update refresh --validate-only
```

### Data Management

```bash
# Export current effective data
omr data dump --effective --output backup.json

# Clear cache and start fresh
omr cache clear --yes
omr update apply

# Check cache status
omr cache info
```

### Provider Comparison

```bash
# Compare pricing between providers
omr --provider openai models list --format json > openai.json
omr --provider azure models list --format json > azure.json

# Check which providers are available
omr providers list
```

## Exit Codes

The CLI uses standard exit codes for CI/CD integration:

- `0`: Success
- `1`: Generic error
- `2`: Invalid usage/arguments
- `3`: Model not found
- `4`: Data source missing/corrupt
- `10`: Update available (used by `omr update check`)

## Troubleshooting

### Command Not Found

If `omr` command is not found after installation:

```bash
# Check if it's installed
pip show openai-model-registry

# Try using the module directly
python -m openai_model_registry.cli --help
```

### No Models Listed

If `omr models list` shows no models:

```bash
# Check data sources
omr data paths

# Check for data loading errors
omr --debug models list

# Try updating data
omr update apply
```

### Permission Errors

If you get permission errors with cache operations:

```bash
# Check cache directory permissions
omr cache info

# Clear cache with appropriate permissions
sudo omr cache clear --yes
```

### Provider Issues

If provider switching doesn't work:

```bash
# Check current provider
omr providers current

# Check environment
omr data env

# Set provider explicitly
export OMR_PROVIDER=azure
omr providers current
```
