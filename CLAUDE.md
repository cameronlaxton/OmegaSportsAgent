# CLAUDE.md - OmegaSportsAgent

## Project Overview
OmegaSportsAgent is a quantitative sports betting engine being rebuilt with a "Quant Fund" architecture using PostgreSQL with a Hybrid Schema (Relational + JSONB).

## Architecture

### Hybrid Schema Design
- **Relational columns**: Universal data (IDs, Names, Dates)
- **JSONB columns**: Sport-specific stats (Box Scores)
- **Why**: NBA has rebounds, NFL has passing_yards. We use JSONB to avoid 200 sparse columns.

### Entity Resolution
- Scrapers return inconsistent names ("LeBron James" vs "L. James")
- `canonical_names` table + `aliases` JSONB field maps all variations to a single UUID
- See `src/utils/entity_resolver.py`

### Key Files
```
src/db/schema.py              # Hybrid Schema (SQLAlchemy 2.0)
src/db/alembic/versions/      # Database migrations
src/utils/entity_resolver.py  # Name resolution service
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
| `canonical_names` | Entity resolution | - |

## Commands

```bash
# Apply migrations
alembic upgrade head

# Generate migration
alembic revision --autogenerate -m "description"

# Run with Docker
docker-compose up -d
```

## Environment Variables
```env
DATABASE_URL=postgresql://user:pass@host:5432/omega_sports
ODDS_API_KEY=xxx
BALLDONTLIE_API_KEY=xxx
```

## Development Rules

1. **JSONB for sport-specific data** - Never add sparse columns
2. **Entity resolution required** - All scraper names must resolve to UUIDs
3. **Containerized** - Must work in Docker, not local-only
4. **SQLAlchemy 2.0 Async** - Use async patterns
5. **Pydantic v2** - For data validation

## Roadmap
See `BETTING_STRATEGY_ROADMAP.md` for technical implementation phases.
