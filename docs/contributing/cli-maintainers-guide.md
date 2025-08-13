## CLI Maintainers Guide

This document is for contributors maintaining the `omr` CLI. It captures design goals, architecture, and maintainer-centric practices. User-facing usage and examples live in `docs/user-guide/cli.md` and the CLI's `--help`/`--help-json`.

### Goals

- Keep CLI thin and stable; delegate logic to public library APIs
- Human-friendly tables and robust machine outputs (JSON/CSV/YAML)
- Read-only by default; explicit flags for destructive actions
- Cross-platform, non-interactive CI-friendly behavior

### Architecture

- Entry point: `omr` → `openai_model_registry.cli:app`
- Frameworks: `click`, `rich-click`, `rich`
- Module layout:

```
src/openai_model_registry/cli/
├── app.py                  # Root command group and global options
├── commands/
│   ├── data.py             # data paths/env/dump
│   ├── update.py           # update check/apply/refresh/show-config
│   ├── models.py           # models list/get
│   ├── providers.py        # providers list/current
│   └── cache.py            # cache info/clear
├── formatters/
│   ├── table.py            # Rich tables
│   └── json.py             # JSON/YAML/CSV
└── utils/
    ├── options.py          # Shared options
    └── helpers.py          # Helpers and exit codes
```

### Public API contract

CLI uses only public APIs:

- `ModelRegistry.get_default()` / `ModelRegistry()`
- `ModelRegistry.models`
- `ModelRegistry.get_capabilities(model)`
- `ModelRegistry.get_data_info()`
- `ModelRegistry.check_for_updates()` / `get_update_info()` / `update_data()` / `refresh_from_remote()`
- Added for CLI ergonomics:
  - `list_providers()`
  - `dump_effective()`
  - `get_raw_data_paths()`
  - `clear_cache()`
  - `get_bundled_data_content(filename)`
  - `get_raw_model_data(model_name)`

If any of these contracts change, update `docs/user-guide/cli.md` and `tests/test_cli.py` accordingly.

### Output conventions

- TTY default: tables; non-TTY default: JSON
- `models get`/`data dump` only support JSON/YAML (fallback to JSON if table/csv requested)
- JSON outputs sorted for stability; custom serializer for dates/enums

### Columns and filtering

- `models list --columns` supports dotted paths; dynamic column discovery includes third-level keys (e.g., `billing.web_search.call_fee_per_1000`)
- `--filter` supports simple expressions and case-insensitive AND

### Provider handling

- Precedence: `--provider` > `OMR_PROVIDER` env > default `openai`
- `providers current` surfaces provider and source (flag/env/default)

### Testing

- Keep `tests/test_cli.py` updated for:
  - `--help-json` structure
  - Provider resolution precedence
  - Format fallbacks and CSV/JSON/YAML correctness
  - Exit codes for update/check, model not found, invalid usage
  - `--parameters-only` for `models get`

### Pricing automation (ostruct)

- See `scripts/ostruct/README.md` for detector/per-model templates and CI workflow
- In short: detector web-search step + dynamic per-model fetch + merge/normalize/validate/commit

### Maintenance checklist

- When adding new model fields, ensure `dump_effective()` surfaces them and `formatters/table.py` handles display
- Keep `docs/user-guide/cli.md` aligned with CLI behaviors
- Run pre-commit hooks locally; keep mypy/ruff clean
