# Examples Directory

Canonical location for runnable examples (moved out of repo root to reduce noise).

- `example_complete_workflow.py` — end-to-end workflow run
- `example_markov_simulation.py` — Markov simulation usage
- `example_autonomous_calibration.py` — calibration/autonomous run example
- `daily_grading_example.py` — grading workflow example

Notes:
- Scraping entrypoint is `scraper_engine.py` (Playwright/requests) plus data adapters in `src/data/`.
- Examples assume calibration packs load from `config/calibration/` (universal-first).

