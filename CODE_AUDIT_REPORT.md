# CactiAutomation – Source Audit and Refactor Report

Date: 2025-10-22

## Overview
- Stack: Python, Flask, Selenium, EasyOCR, JSON storage
- Goal: Clean codebase, remove redundant/experimental code, standardize logging, and ensure safer, clearer flow across modules.

## Changes Summary

### Files Refactored
- `main_pipeline.py`
  - Rewritten with logging, clear docstrings, and type hints.
  - Removed garbled/unicode artifacts in console prints.
  - Standardized step functions and centralized progress updates.
  - Removed unused EasyOCR imports.
  - Replaced prints with `logging` and improved messages.

- `ScrapingImageCacti.py`
  - Fixed Selenium credential input (`send_keys(userLogin/userPass)` instead of dict literal).
  - Replaced prints with `logger` calls; kept existing file/console handlers.
  - Reduced noisy debug prints; kept essential progress logs.
  - Removed unused import `urlparse`.
  - Minor readability and consistency improvements.

- `easyocr_image_to_text.py`
  - Introduced `logger` and replaced prints with `logging` at appropriate levels.
  - Kept existing functions and behavior; improved visibility of warnings/errors.

- `progress_tracker.py`
  - Removed duplicated class definitions.
  - Implemented a proper singleton with a lock and an atomic `update()` method.
  - Added module docstring, clarified responsibilities.

- `App.py`
  - Replaced prints in SSE stream and download route with `app.logger`.
  - Removed unused import `redirect`.

- `data_cleaner.py` (new; replaces `testingClean.py`)
  - Clear name and responsibility.
  - PEP257 docstrings and logging.
  - Exposed `process_csv()` converting 100..999 Kbps to Mbps.

### Files Removed
- `testingClean.py` → superseded by `data_cleaner.py` with same functionality and clearer semantics.
- `testingimport.py` → ad-hoc import test script, not part of production flow.
- `test_connection.py` → hardcoded credentials and not used by app; unsafe to keep.

### Structural & Quality Improvements
- Logging
  - Standardized across modules using `logging`. No bare `print()` in core paths.
  - App routes now log via `app.logger`.

- Progress tracking
  - `progress_tracker` simplified, thread-safe singleton with `update()` API.

- Pipeline
  - Clear step boundaries, consistent messages, type hints, and docstrings.
  - Reduced unused imports and noisy prints.

- Naming & Responsibility
  - Replaced ambiguous `testingClean.py` with `data_cleaner.py`.
  - Eliminated experimental/test-only scripts from the root.

## Database Layer
- No active DB usage found in production paths.
- `graph_storage.py` uses JSON files and already leverages logging.
- Removed `test_connection.py` (unsafe hardcoded credentials). If DB is reintroduced, ensure:
  - Use parameterized queries, context managers, and robust error handling.
  - Centralize connection management and secrets via environment variables.

## Web Layer (Flask)
- Routes remain consistent (`/`, `/run_pipeline`, `/progress`, `/download`).
- SSE stream now logs connect/disconnect/errors.
- Consider moving `pipeline_lock` to a shared runtime module to avoid cross-imports if the codebase grows.

## Cleanups & Optimizations
- Did not delete `build/`, `downloaded_graphs/`, or logs to avoid disrupting environment/state.
- Recommend excluding heavy artifacts (models, outputs) from VCS or pruning old runs periodically.
- Consider adding `.env` for config and `.env.example` for defaults.

## Recommendations
- Centralize logging configuration (e.g., `utils/logging_config.py`) and import it in `App.py` and CLIs.
- Add unit tests around:
  - `data_cleaner.process_csv()`
  - `progress_tracker.update()` thread-safety
  - OCR parsing correctness for representative inputs
- Consider extracting Selenium scraping into a service class to simplify `login_and_scrape` and enable mocking.
- If DB logging is desired, implement a DAO layer and migrate from JSON storage accordingly.

## Refactored Files List
- App.py
- main_pipeline.py
- ScrapingImageCacti.py
- easyocr_image_to_text.py
- progress_tracker.py
- data_cleaner.py (new)

## Deleted Files List
- testingimport.py
- testingClean.py
- test_connection.py

## Notes
- Functionality preserved per current flow: scrape → ocr → csv clean → download.
- No schema or API breaking changes introduced.

