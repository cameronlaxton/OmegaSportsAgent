## Tasks Overview (Daily / Grading / Weekly Calibration)

Repo: https://github.com/cameronlaxton/OmegaSportsAgent-1  
Single calibration source: `config/calibration/nba_latest.json` (edge_thresholds, probability_transforms, kelly_staking, variance_scalars).  
Outputs consumed by Lab: `outputs/`, `data/logs/`.  
Tuned parameters (auto-calibrator): `config/calibration/tuned_parameters.json`.

---

### Task 1: Daily Predictions (Agent) — mandatory
**Goal:** Generate daily bets and outputs.  
**Read:** `main.py`; `omega/foundation/model_config.py`; `config/calibration/nba_latest.json`.  
**Write/Return:** `outputs/recommendations_YYYYMMDD.json`; `data/logs/predictions.json`; `data/exports/BetLog.csv` (if logging/export runs).

**LLM prompt (Perplexity-ready):**
```
You are running the OmegaSportsAgent daily predictions.
Repo: https://github.com/cameronlaxton/OmegaSportsAgent-1
Steps:
1) Read config/calibration/nba_latest.json for edge_thresholds, probability_transforms, kelly_staking.
2) Ensure omega/foundation/model_config.py uses the pack’s thresholds (min_edge_pct).
3) Run: python main.py --morning-bets --leagues NBA NFL
4) Collect outputs: outputs/recommendations_YYYYMMDD.json, data/logs/predictions.json, data/exports/BetLog.csv (if present).
If live odds/stats are unavailable via APIs, web-scrape public odds/scoreboards as fallback.
Return the three output files.
```

---

### Task 2: Daily Grading (optional but recommended)
**Goal:** Grade prior bets and update logs.  
**Read:** `omega/workflows/daily_grading.py`; latest `outputs/recommendations_*.json`; `data/logs/predictions.json`.  
**Write/Return:** Updated `data/logs/predictions.json`; updated `data/exports/BetLog.csv` (if export run).

**LLM prompt:**
```
You are grading yesterday’s bets for OmegaSportsAgent.
Repo: https://github.com/cameronlaxton/OmegaSportsAgent-1
Steps:
1) Read outputs/recommendations_*.json and data/logs/predictions.json.
2) Run grading: python -m omega.workflows.daily_grading
3) Update data/logs/predictions.json and data/exports/BetLog.csv.
If no APIs are available, scrape public scoreboards to resolve outcomes.
Return the updated predictions.json and BetLog.csv.
```

---

### Task 3: Weekly Calibration (Lab) — mandatory
**Goal:** Recalibrate using last week’s outputs/logs; update calibration pack.  
**Read:** `lab/core/calibration_runner.py`; `outputs/recommendations_*.json`; `data/logs/predictions.json`; current `config/calibration/nba_latest.json`.  
**Write/Return:** Updated `config/calibration/nba_latest.json`; optional calibration report in `lab/data/experiments/` or summary text.

**LLM prompt:**
```
You are recalibrating OmegaSportsAgent using last week’s outputs.
Repo: https://github.com/cameronlaxton/OmegaSportsAgent-1
Steps:
1) Gather agent outputs: outputs/recommendations_*.json and data/logs/predictions.json.
2) Run: cd lab && python -m core.calibration_runner --league NBA --use-agent-outputs --output ../config/calibration/nba_latest.json
3) Update config/calibration/nba_latest.json with the new pack.
If live data is needed and no API keys exist, scrape public odds/results as a proxy.
Return the updated calibration pack file.
```

---

### Consistency & Threshold Alignment
- Calibration pack is the single source; Agent reads it via `config/calibration_loader.py`.  
- `omega/foundation/model_config.py` derives `min_edge_pct` from the pack when present (pack values are decimals; model uses percentage points).  
- Auto-calibrator/tuner persists tuned parameters under `config/calibration/tuned_parameters.json` (kept alongside the pack).  
- All tasks read/write within `config/calibration/`, `outputs/`, and `data/` to keep Agent↔Lab in sync.

### API Key Note
- GitHub Actions and these prompts do not require API keys; if keys are absent, rely on web-scraping public odds/scoreboards.  
- If later desired, see `docs/API_KEYS.md` for optional The Odds API / BallDontLie secrets.

