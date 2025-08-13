# ostruct pricing automation

This folder contains the ostruct templates and schemas used to keep pricing data up to date.

## Files

- `pricing_template.j2` / `pricing_schema.json`: Per-model pricing extractor. Produces unified pricing:
  - `scheme` (per_token|per_minute|per_image|per_request)
  - `unit` (million_tokens|minute|image|request)
  - `input_cost_per_unit`, `output_cost_per_unit`, `currency`
- `pricing_change_detector.j2` / `pricing_change_detector_schema.json`: Lightweight detector that uses Web Search to find recent pricing changes and new model announcements. Accepts `-V today=YYYY-MM-DD` and optional `-J allowed_models='["..."]'`.

## How CI uses this

- A scheduled workflow runs a fast detector step first:
  - Builds `allowed_models` dynamically from `data/models.yaml` (models that have a `pricing` block and are not deprecated)
  - Calls detector with Web Search and `today` to decide whether to proceed
  - Daily: skip if no changes; Weekly (Sunday): always proceed
- If proceeding, the workflow runs per-model ostruct pricing extraction and merges the results into `data/models.yaml` (and `data/overrides.yaml`), normalizes, validates, and commits.

## Local testing

- Detector (requires OPENAI_API_KEY):

  ```bash
  TODAY=$(date -u +%F)
  ALLOWED_MODELS=$(python - <<'PY'
  import json, yaml; d=yaml.safe_load(open('data/models.yaml'))
  m=[k for k,v in (d.get('models') or {}).items() if isinstance(v,dict) and 'pricing' in v and not (v.get('deprecation',{}).get('status')=='deprecated')]
  print(json.dumps(m))
  PY
  )
  pipx run --spec ostruct-cli==1.6.1 \
    ostruct run scripts/ostruct/pricing_change_detector.j2 scripts/ostruct/pricing_change_detector_schema.json \
    --enable-tool web-search --tool-choice web-search --ws-context-size low \
    -V today="$TODAY" -J allowed_models="$ALLOWED_MODELS" \
    --model gpt-4.1 --temperature 0
  ```

- Per-model pricing fetch (writes to `pricing_data/`):

  ```bash
  poetry run python src/openai_model_registry/scripts/fetch_pricing_ostruct.py --model gpt-4.1
  poetry run python scripts/update_pricing.py
  poetry run python scripts/data_convert_unified_pricing.py
  ```

## Notes & limitations

- The official pricing page may be protected (Cloudflare). The detector avoids scraping by searching for authoritative pricing announcements and the OpenAI pricing page (`https://openai.com/api/pricing`).
- Use `pipx run` for a clean ostruct environment in CI to avoid dependency drift.
- For new models, the detector may emit `initial_pricing` with non-normalized labels (e.g., “per 1M tokens”); the merge step is responsible for mapping to the unified schema when needed.
