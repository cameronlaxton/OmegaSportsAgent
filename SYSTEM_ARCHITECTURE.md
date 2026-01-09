## OmegaSportsAgent Monorepo Architecture

### Overview
- **Agent (live)**: daily scraping → simulation → bet logging.
- **Lab (audit/calibration)**: ingests Agent outputs → runs calibration → updates calibration pack.
- **Single source of truth for calibration**: `config/calibration/nba_latest.json`.

### Directory Layout
- `main.py`, `scraper_engine.py` — CLI entry points.
- `omega/` — Agent source (analysis, data, simulation, betting, workflows).
- `config/` — Calibration loader, Perplexity instructions, calibration packs.
- `data/` — Runtime logs/exports/outputs (Agent).
- `outputs/` — Daily recommendations `recommendations_YYYYMMDD.json`.
- `lab/` — Validation Lab (moved inside repo).
- `tests/` — Agent tests.

### Data & File Flows
```
Daily (Agent)
  main.py --morning-bets
    → omega.workflows.morning_bets
    → simulations + edge eval
    → outputs/recommendations_YYYYMMDD.json
    → data/logs/, data/exports/

Daily Grading (optional)
  omega.workflows.daily_grading
    → updates bet results in data/logs/ and data/exports/

Weekly Calibration (Lab)
  lab/core/calibration_runner.py --use-agent-outputs
    → reads outputs/ and data/logs/
    → writes config/calibration/nba_latest.json
```

### Calibration Single Source
- **Calibration pack**: `config/calibration/nba_latest.json`
  - edge_thresholds, probability_transforms, kelly_staking, variance_scalars, metadata.
- **Loader**: `config/calibration_loader.py`
- **Auto-calibrator**: stores tuned parameters in `config/calibration/tuned_parameters.json`.

### GitHub Actions Automation (proposed)
- `.github/workflows/daily-predictions.yml` — 7 AM ET: run `python main.py --morning-bets --leagues NBA NFL`, commit `outputs/`, `data/`.
- `.github/workflows/daily-grading.yml` — 1 AM ET: run grading, commit updated logs.
- `.github/workflows/weekly-calibration.yml` — Sunday 11 PM ET: run `lab/core/calibration_runner.py --use-agent-outputs --output ../config/calibration/nba_latest.json`, commit updated pack.

### API Keys (GitHub Secrets)
- `ODDS_API_KEY` — The Odds API (live odds).
- `BALLDONTLIE_API_KEY` — BallDontLie (NBA/NFL stats).

### Golden Path Workflow
1) Agent daily:
   - Scrape odds/stats → simulate → log bets → write `outputs/` + `data/logs/`.
2) Lab weekly:
   - Ingest `outputs/` + `data/logs/` → calibrate → update `config/calibration/nba_latest.json`.
3) Agent uses updated pack next run via `CalibrationLoader`.

### Testing
- Agent tests live in `tests/`.
- Lab tests remain under `lab/tests/`.

### Cleanup Policy
- Archives and stale status docs removed; only keep current README/guide/system architecture.

