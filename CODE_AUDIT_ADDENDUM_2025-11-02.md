# CactiAutomation — Architecture, Performance, and Hardening Addendum

Date: 2025-11-02

This addendum complements the existing CODE_AUDIT_REPORT.md with a deeper scan across scraping, OCR, pipeline, and web layers, including prioritized recommendations and a practical upgrade plan.

## Key Findings

1) Pipeline & Orchestration
- `main_pipeline.py:147` defines `step3_clean_csv` and writes per-run summary; however it parses `scraping_report.txt` from the repository root (`main_pipeline.py:196` uses `os.path.dirname(__file__)`). Move the report into the active run folder (e.g., `output/<ts>/scraping_report.txt`) to keep runs isolated.
- Global `current_scraping_folder` in `main_pipeline.py:23` is legacy; state is already tracked via `tracking/progress.progress`. Remove to avoid confusion.
- Several broad `except Exception` blocks hide root causes. Narrow exception scopes and add actionable context.

2) Scraping (Selenium)
- `scraping/scraper.py:188` duplicates logging setup (`setup_logging`) instead of using `utils/logging_config.setup_logging`. Unify logging to avoid handler duplication and drift.
- Network IO lacks timeouts/retries when downloading graphs (`scraping/scraper.py:44` in `save_graph_image`). Add `timeout=(5, 30)` and a retry adapter with backoff.
- Add optional headless Chrome via env/config for CI/servers; pin driver versions for reproducibility.
- Use short, deterministic filenames (e.g., `<username>_<yyyymmddHHMM>_<hash8>.png`) and persist full titles in metadata (`graph_storage.py`).
- Replace `time.sleep` with explicit waits where possible; store “no zoom” diagnostics under the active run folder, not repo root.

3) OCR & Post-processing
- EasyOCR reader reuse is good (`easyocr_image_to_text.py:73`). Consider light parallelism for CPU mode; expose GPU toggle in UI.
- Preprocessing (`easyocr_image_to_text.py:56`) resizes to width=2000; make configurable for speed/accuracy tradeoff.
- `clean_ocr_text` has repeated keys and overlapping regexes (`easyocr_image_to_text.py:21-53`). Consolidate rules, add comments and unit tests with representative samples.
- CSV cleaner converts only numeric dtypes (`data_cleaner.py:33`). Promote safe string→numeric coercion and handle `k/M` suffixes.

4) Storage & Data
- JSON storage is OK for single-user. For concurrency or richer queries, migrate to SQLite with indices on `timestamp` and `title`.
- If keeping JSON, add query helpers (by time range, by username) and a compaction tool.

5) Web Layer (Flask)
- `web/app.py:282-283` runs with `debug=True`. Default to `debug=False` and provide a WSGI entrypoint (waitress/gunicorn) for deployment.
- CORS is wide-open; restrict origins via env when possible.
- `/download` expects specific names; fall back to enumerating latest CSV in the run folder.

6) Observability & DX
- Central logging is solid (`utils/logging_config.py`). Bind a `run_id` to log records during pipeline runs, add request logging middleware.
- Provide `.env` and typed settings for headless mode, timeouts, base URL allowlist, CORS, model dir, output root.
- Add `requirements.txt` with pinned versions; optional `Makefile` or `invoke` tasks.

7) Security
- Validate `target_url` against an allowlist to avoid SSRF.
- Force all write paths under `output/` and sanitize filenames.

## Quick Wins (1–2 days)
- Pipeline
  - Write `scraping_report.txt` into the per-run folder and load it from there in `main_pipeline.py`.
  - Remove legacy `current_scraping_folder` global.
- Scraper
  - Replace local logging config with `utils.logging_config.setup_logging`.
  - Add `requests` timeouts and retry adapter in `save_graph_image`.
  - Add `HEADLESS` env toggle; store diagnostics under `output/<ts>/diagnostics/`.
- OCR
  - Consolidate corrections dict; extract into `ocr/rules.py`.
  - Make `target_width` and `batch_size` configurable; default width 1400–1600.
- CSV
  - Coerce string numerics and handle `k/M` suffixes; add unit tests for `process_csv`.
- Web
  - Default `debug=False`; document waitress launch; restrict CORS via env.

## Medium Items (1–2 weeks)
- Replace JSON storage with SQLite (or keep JSON and add indices/compaction).
- Add per-run `run.json` manifest with inputs, counts, timings, file paths.
- Parallel OCR (process pool) for CPU-only deployments.
- Integration tests: mock Selenium and validate end-to-end on a tiny fixture set.
- CI: ruff + black + mypy + pytest on push.

## Implementation Notes with File Pointers
- Per-run report path: change `report_path` at `main_pipeline.py:196` to point into the active run folder.
- Logging unification: remove local `setup_logging` at `scraping/scraper.py:188`; call centralized setup early (e.g., CLI and `web/app.py:16`).
- Timeouts/retries: in `scraping/scraper.py:44`, use `session.get(url, timeout=(5,30))` and mount a `Retry` adapter.
- CSV coercion: extend `data_cleaner.py:33` to coerce string numerics and optional `k/M` suffixes.
- Safer downloads: let `/download` enumerate `*.csv` in the active run folder if named files aren’t found (`web/app.py:190`).

## Proposed Next Steps
1) Approve Quick Wins scope; implement behind `.env`-driven config without breaking current flows.
2) Add `requirements.txt` and a short README “Runbook” section including waitress launch and headless mode.
3) After validating on a sample run, schedule Medium Items (storage, tests, parallel OCR).

## Risks & Mitigations
- Selenium selectors are brittle; keep them centralized and configurable; always capture per-run diagnostics.
- OCR accuracy varies; any rule changes must include tests and a validation set.
- Headless Chrome can differ slightly; validate flows in both modes.

