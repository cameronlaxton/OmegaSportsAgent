# OmegaSportsAgent Architecture

## Layer Boundaries

The system has four clear layers. Each layer has strict **allowed** and **not allowed** responsibilities.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Frontend (Next.js)                                                         │
│  Allowed: UI, calling FastAPI JSON endpoints, displaying results          │
│  Not allowed: Direct DB access, live data fetching, simulation logic        │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Agent (LLM + web search)                                                    │
│  Allowed: Fetching live data (schedules, stats, odds), calling APIs,      │
│           scraping, Perplexity/ESPN/BBRef/NBA Stats API, then calling       │
│           FastAPI with fully-populated requests (games, context, odds)      │
│  Not allowed: Running simulation/calibration internals; must use service    │
│               entry points (analyze_game, analyze_slate) with pre-filled   │
│               inputs                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  FastAPI Service (server/)                                                  │
│  Allowed: Expose JSON APIs only; validate request; call engine/contracts   │
│           with request data; return status + skip_reason / ErrorResponse     │
│  Not allowed: HTTP/scraping/API calls to fetch live data; must receive      │
│               games, context, and odds from the request or return skipped   │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Engine (src/simulation, src/validation, src/betting)                       │
│  Allowed: Simulation, calibration, edge/Kelly calculations; operate on     │
│           fully-populated inputs (teams, league, odds, stats dicts)         │
│  Not allowed: Any network access; must never call get_team_context,         │
│               get_todays_games, or any module that does HTTP/API calls      │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

- **Engine**: Input-driven only. Receives `home_context`, `away_context`, and game parameters. If context is missing, returns `success: false` with `skip_reason`; it does **not** fetch.
- **Service**: Entry points are `GameAnalysisRequest` and `SlateAnalysisRequest`. Request bodies may include optional `home_context`, `away_context`, and (for slate) `games`. If required data is missing, the service returns `status: "skipped"` with `skip_reason`.
- **Agent**: The only place that fetches live data. It uses `src/data/` modules that perform HTTP/API (e.g. `stats_ingestion`, `schedule_api`, `nba_stats_api`, `stats_scraper`). The agent then calls the FastAPI endpoints with populated requests.
- **Frontend**: Calls FastAPI; may delegate “fetch and analyze” to the agent or to a backend that uses the agent.

## Project Layout

| Path | Purpose |
|------|---------|
| `src/` | Engine + core utilities (simulation, validation, betting, contracts, db, foundation). No network calls from engine paths. |
| `server/` | FastAPI app; JSON-in/JSON-out only. |
| `agent/` | LLM + web search; when present, the only place that invokes live data-fetching in `src/data/`. |
| `frontend/` | Next.js (or other) UI. |
| `scripts/` | One-off or maintenance scripts; non-core. |
| `experiments/` | Notebooks and experimental code; non-core. |

## Public API Contract

- **Stable entry points** from outside the backend: `GameAnalysisRequest` → `GameAnalysisResponse`, `SlateAnalysisRequest` → `SlateAnalysisResponse`.
- Request/response models must not expose internal provider names (e.g. espn, bbref, nba_stats_api, perplexity) in stable fields. Provider details are for agent-side logging only.
- All API responses use `status` plus optional `skip_reason`; errors use `ErrorResponse` with `error_code`, `message`, and optional `fallback_hint`.

## Detailed Module Reference

### Engine Layer (`src/`)

#### Simulation Engine (`src/simulation/simulation_engine.py`)
- `OmegaSimulationEngine` — Monte Carlo simulation across 9 sport archetypes.
- Key methods: `run_game_simulation()`, `run_fast_game_simulation()`, `run_player_prop_simulation()`.
- Archetype-specific simulators: `_sim_basketball`, `_sim_american_football`, `_sim_baseball`, `_sim_hockey`, `_sim_soccer`, `_sim_tennis`, `_sim_golf`, `_sim_fighting`, `_sim_esports`.
- Graceful degradation: `_skip_result()` returns structured skip when required keys are missing.

#### Sport Archetypes (`src/simulation/sport_archetypes.py`)
- `SportArchetype` frozen dataclass defining `required_team_keys`, `prop_stat_keys`, `supported_markets` per sport.
- `LEAGUE_TO_ARCHETYPE` maps 60+ league strings (NBA, NFL, EPL, UFC, etc.) to 9 archetypes.

#### Betting (`src/betting/`)
- `odds_eval.py` — `american_to_decimal()`, `implied_probability()`, `edge_percentage()`, `expected_value_percent()`.
- `kelly_staking.py` — `kelly_fraction()`, `recommend_stake()` with tier multipliers (A=0.50, B=0.25, C=0.10 of full Kelly).

#### Validation / Calibration (`src/validation/`)
- `PerformanceTracker` — tracks prediction accuracy over time.
- `ParameterTuner` — adjusts simulation parameters based on observed results.
- `AutoCalibrator` — autonomous calibration loop (tracker → tuner → apply).
- `CalibrationEngine` — probability transforms (Platt scaling, shrinkage, isotonic).

#### Contracts (`src/contracts/`)
- `schemas.py` — Pydantic v2 models defining the JSON contract: `GameAnalysisRequest`, `GameAnalysisResponse`, `SlateAnalysisRequest`, `SlateAnalysisResponse`, `PlayerPropRequest`, `PlayerPropResponse`, `SimulationResult`, `EdgeDetail`, `BetSlip`, `ErrorResponse`, etc.
- `service.py` — Stable service interface: `analyze_game()`, `analyze_slate()`, `analyze_player_prop()`. Never raises — returns `status="skipped"` or `status="error"` on failure.

#### Foundation (`src/foundation/`)
- `api_config.py` — Environment variable reader for API keys (`ODDS_API_KEY`, `BALLDONTLIE_API_KEY`).
- `model_config.py` — `get_edge_thresholds()`, `get_simulation_params()` with defaults.
- `league_config.py` — `get_league_config(league)` returns sport-specific parameters (avg_total, home_advantage, std, etc.) for 25+ leagues.
- `core_abstractions.py` — `Team` dataclass (name, league, abbreviation, record, stats).

#### Utilities (`src/utilities/`)
- `output_formatter.py` — `format_full_output()` for text/JSON rendering of analysis.
- `data_logging.py` — `log_bet_recommendation()` for persisting picks.
- `sandbox_persistence.py` — `OmegaCacheLogger` file-based key-value cache with SHA256 keys.

### Service Layer (`server/`)

#### FastAPI Application (`server/app.py`)
- CORS enabled for `localhost:3000` (Next.js dev server).
- Endpoints:
  - `GET /health` — liveness check.
  - `POST /analyze/game` — single-game analysis (accepts `GameAnalysisRequest`).
  - `POST /analyze/prop` — player prop analysis (accepts `PlayerPropRequest`).
  - `POST /analyze/slate` — multi-game slate analysis (accepts `SlateAnalysisRequest`).
- Request logging middleware for observability.

### Agent Layer (`agent/`)

#### Orchestrator (`agent/orchestrator.py`)
- `AgentOrchestrator` — stateful agent with retry, caching, and error handling.
- `AgentConfig` — configures LLM provider, backend mode (`in_process` / `http`), cache settings.
- `AgentCache` — TTL-aware file cache for idempotent re-queries.
- `AgentError` — structured errors with `code`, `message`, `context`, `fallback_hint`, `retryable`.
- Flow: `handle_query()` → `parse_intent()` → `gather_data()` → `_run_game()` / `_run_slate()` with retry loop.
- `parse_intent()` — regex-based team extraction, league detection from keywords.
- `gather_data()` — tries `src.data.free_sources`, falls back gracefully with structured skip.

### Frontend Layer (`frontend/`)

#### Stack
- Next.js 15 (App Router) + React 19 + TypeScript + Tailwind CSS 3 + Recharts.

#### Key Files
- `src/types/schemas.ts` — TypeScript interfaces mirroring Python Pydantic models.
- `src/lib/api.ts` — `analyzeGame()`, `analyzeSlate()`, `healthCheck()` calling FastAPI via `/api/*` proxy.
- `src/app/page.tsx` — Main page: query input → analysis state → MatchupCard rendering.
- `src/components/QueryInput.tsx` — Natural-language text input + Analyze button.
- `src/components/MatchupCard.tsx` — Card rendering simulation results, probability bar, edge table, best bet.
- `src/components/ProbabilityBar.tsx` — Gradient bar showing home/draw/away probabilities.
- `src/components/EdgeTable.tsx` — Table with model prob, market prob, edge, EV%, odds, confidence tier.
- `src/components/BetSlipCard.tsx` — Green-gradient card for best bet recommendation.
- `next.config.ts` — API proxy rewrites (`/api/*` → `localhost:8000`).

### Support Modules

#### Bet Recording (`src/utilities/bet_recorder.py`)
- `BetRecorder` — static class persisting picks to daily JSON files in `outputs/recommendations/`.
- Methods: `record_bet()`, `get_bets_for_date()`.

#### Calibration Loading (`src/foundation/calibration_loader.py`)
- `CalibrationLoader` — loads calibration config from `config/calibration/universal_latest.json`.
- Methods: `get_edge_threshold()`, `get_kelly_fraction()`, `get_kelly_policy()`, `get_probability_transform()`.
- Builds chained transform functions (Platt scaling + shrinkage).

## Running the System

### Backend
```bash
# Install Python dependencies
pip install -r requirements.txt

# Run tests (from repo root)
PYTHONPATH=. PYTHONIOENCODING=utf-8 python -m pytest tests/ -v

# Start FastAPI server
PYTHONPATH=. uvicorn server.app:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev          # Dev server on localhost:3000
npm run build        # Production build
```

### Environment Variables
```bash
DATABASE_URL=postgresql://user:pass@host:5432/omega_sports
ODDS_API_KEY=xxx
BALLDONTLIE_API_KEY=xxx
```

## Test Suites

| Suite | File | Tests | Coverage |
|-------|------|-------|----------|
| Engine | `tests/test_engine.py` | 7 | Simulation, schemas, CLI, config |
| Calibration | `tests/test_calibration.py` | 4 | Tracker, tuner, auto-calibrator, Markov |
| Integration | `tests/test_calibration_integration.py` | 4 | Bet recorder, calibration loader, imports |
| API Config | `tests/test_api_config.py` | 2 | Key loading, env overrides |
