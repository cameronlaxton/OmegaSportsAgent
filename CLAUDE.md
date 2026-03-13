# CLAUDE.md - OmegaSportsAgent

## Project Overview
OmegaSportsAgent is a quantitative sports betting engine with a "Quant Fund" architecture using PostgreSQL with a Hybrid Schema (Relational + JSONB).

## Architecture

### Layer Boundaries
- **Engine** (src/simulation, validation, betting): Input-driven only; no network calls.
- **Service** (server/, src/contracts): JSON APIs only; does not fetch games or context.
- **Agent** (agent/): Only place that fetches live data; calls FastAPI with pre-filled requests.
- **Frontend** (frontend/): Calls FastAPI. See `docs/ARCHITECTURE.md` for full rules.

### Hybrid Schema Design
- **Relational columns**: Universal data (IDs, Names, Dates)
- **JSONB columns**: Sport-specific stats (Box Scores)
- **Why**: NBA has rebounds, NFL has passing_yards. We use JSONB to avoid 200 sparse columns.

### Entity Resolution (NOT YET WIRED)
- `canonical_names` table + `aliases` JSONB field defined in schema
- `src/utilities/entity_resolver.py` exists but is not called by any runtime code
- Scrapers currently use raw names; entity resolution is planned but not enforced

### Key Files

```text
src/db/schema.py                    # Hybrid Schema (SQLAlchemy ORM)
src/db/alembic/versions/            # Database migrations
src/contracts/schemas.py            # API request/response models (Pydantic v2)
src/contracts/service.py            # Stable service interface
src/simulation/simulation_engine.py # Monte Carlo engine (9 sport archetypes)
```

## Schema Quick Reference

| Table | Purpose | JSONB Fields |
|-------|---------|--------------|
| `leagues` | League config | `config` |
| `teams` | Canonical teams | `aliases`, `season_stats` |
| `players` | Canonical players | `aliases`, `details` |
| `games` | Game events | `environment` |
| `player_game_logs` | **THE BOX SCORE** | `stats` |
| `odds_snapshots` | CLV tracking | `markets` |
| `wagers` | Bet ledger | - |
| `canonical_names` | Entity resolution (defined, not yet used at runtime) | - |

## Commands

```bash
# Run tests
PYTHONPATH=. python -m pytest tests/ -v

# Start FastAPI server
PYTHONPATH=. uvicorn server.app:app --reload --port 8000

# Apply migrations (requires DATABASE_URL)
alembic upgrade head

# Generate migration
alembic revision --autogenerate -m "description"
```

## Environment Variables

```bash
DATABASE_URL=postgresql://user:pass@host:5432/omega_sports
ODDS_API_KEY=xxx
BALLDONTLIE_API_KEY=xxx
```

## Development Rules

1. **JSONB for sport-specific data** - Never add sparse columns
2. **Pydantic v2** - For data validation
3. **Layer boundaries** - Engine never fetches; Agent is the only data-fetcher
4. **Synchronous DB** - Current DB layer uses synchronous SQLAlchemy (not async)

## Current Status

### What Works
- NBA and NFL: full data pipeline + simulation
- NCAAB/NCAAF: simulation + generic ESPN data
- MLB/NHL: simulation only (no data collector)

### Legacy Modules (do not extend)
- `src/db/models.py` + `src/db/database.py` — pre-Hybrid ORM, not tracked by Alembic
- `src/schema.py` — superseded by `src/contracts/schemas.py`
