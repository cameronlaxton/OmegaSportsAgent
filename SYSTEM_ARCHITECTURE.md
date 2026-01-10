OmegaSportsAgent System Architecture
====================================

Scope: current repo structure (no LLM instruction packs) with a universal-first calibration strategy. Agent runtime lives in `src/`; Validation Lab in `lab/`.

## High-Level View
- Agent runtime: CLI `main.py` orchestrates workflows.
- Data adapters: `src/data/` (schedule, odds, stats, injury) + `scraper_engine.py` for JS-rendered pages.
- Simulation: `src/simulation/simulation_engine.py`, Markov utilities in `src/api/`.
- Betting: `src/betting/odds_eval.py`, `src/betting/kelly_staking.py`.
- Output: `src/utilities/output_formatter.py` → `outputs/` (timestamped) and `data/outputs/` caches.
- Calibration/Audit: `lab/core/calibration_runner.py`, `lab/tests/`, calibration packs under `config/calibration/`.

## Directory Layout (canonical)
```
main.py                      # CLI entry
scraper_engine.py            # Playwright/requests scraper
src/
  data/                      # schedule_api, odds_scraper, stats_scraper, injury_api
  simulation/                # simulation_engine
  betting/                   # odds_eval, kelly_staking
  workflows/                 # morning_bets, daily_grading
  api/                       # markov analysis endpoints
  utilities/                 # output_formatter, helpers
lab/
  core/                      # calibration_runner, calibration_diagnostics
  tests/                     # lab tests
config/
  calibration/               # universal_latest.json (+ optional league packs)
  settings.yaml              # runtime settings
data/
  logs/, exports/, outputs/  # runtime artifacts
outputs/                     # timestamped CLI outputs
```

## Data & Workflow Flow
1) Morning bets (`main.py --task morning_bets`)
   - Fetch schedule/odds/stats/injuries via `src/data/*` + optional scraping
   - Simulate (`simulation_engine.py`)
   - Evaluate edge/EV and stake (`odds_eval.py`, `kelly_staking.py`, thresholds from calibration)
   - Write results to `outputs/` (timestamped) and `data/outputs/picks_<date>.json`

2) Daily grading (`main.py --task nightly_audit` or workflow class)
   - Grade prior bets; update `data/logs/` and `data/exports/`

3) Calibration (Lab)
   - `lab/core/calibration_runner.py --use-agent-outputs`
   - Reads `outputs/` + `data/logs/` → writes `config/calibration/universal_latest.json` (and optional league packs)

## Calibration Strategy
- Default: `config/calibration/universal_latest.json` with `leagues.{LEAGUE}` overrides.
- Legacy/override: `config/calibration/nba_latest.json` retained for compatibility.
- Loader: `CalibrationLoader` loads universal-first, then league-specific.

## Automation
- Present: `.github/workflows/daily-grading.yml` (grading).
- Planned: daily predictions (morning bets) and weekly calibration (lab runner).

## Scraping & Sources
- Web scraping: `scraper_engine.py` (Playwright + requests/BS4), targets include sharp/public books and news/injury sites.
- APIs: BallDontLie (NBA/NFL), The Odds API (live odds).

## Outputs & Logging
- Primary outputs: `outputs/<task>_<timestamp>.json|md`
- Cached daily picks: `data/outputs/picks_<date>.json`
- Logs/exports: `data/logs/`, `data/exports/BetLog.csv`

