# OmegaSportsAgent: Technical Roadmap (Hybrid Schema Edition)

## Phase 1: The "Box Score" Foundation
**Goal:** Ingest granular data into the new Hybrid JSONB Schema.
- [ ] **1.1 Database Deploy:** Spin up PostgreSQL 15+ container. Apply `schema.py` via Alembic.
- [ ] **1.2 Entity Resolver:** Build the "Rosetta Stone" service that maps messy scraper names ("G. Antetokounmpo") to our UUIDs.
- [ ] **1.3 Box Score Ingestor:**
  - Create universal ingestion pipeline: `Source -> Normalize -> EntityResolve -> Upsert to PlayerGameLog`.
  - Supports dynamic keys: `{"pts": 24}` for NBA, `{"receptions": 5}` for NFL.
- [ ] **1.4 Odds Poller:** Service that runs every 15 mins, scrapes odds, and saves to `OddsSnapshot` (for future CLV analysis).

## Phase 2: The Logic Engine
**Goal:** Turn "Stats" into "Projections".
- [ ] **2.1 Feature Store:** SQL views that flatten the JSONB stats into training columns.
  - *Example:* `SELECT stats->>'pts' as points_L10 FROM player_game_logs...`
- [ ] **2.2 "Market Truth" Calibration:**
  - Build a module that compares our `OddsSnapshot` vs. Final Scores.
  - Determine which books are "Sharp" (predictive) vs "Soft".
- [ ] **2.3 The Simulator:** Port the Monte Carlo engine to read from `PlayerGameLog` history instead of API calls.

## Phase 3: The Agent Interface
**Goal:** Allow LLM queries to hit the DB.
- [ ] **3.1 Text-to-SQL Layer:** Enable the agent to answer "How has LeBron performed in the last 5 games vs Top 10 Defenses?" by querying the JSONB.
- [ ] **3.2 Execution API:** A strict API (`POST /wager`) that agents use to place bets, requiring `game_id`, `units`, and `model_confidence`.

---

## Architecture Decisions

### Why JSONB for Stats?
**The Problem:** ESPN box scores change. New metrics (like "catch probability") appear.

**The Fix:** With `stats = Column(JSONB)`, your scraper can dump everything it finds. You don't need to migrate the database just because you decided to start tracking "Yards After Catch".

### Why Entity Resolution First?
Most scraping projects fail because they have `LeBron James (ID 1)` and `L. James (ID 502)` as two different people. By forcing an `aliases` list in the database `Player` table, we solve this permanently.

### Why Headless/Containerized?
The schema and roadmap assume this lives on a server (or in a Docker container), accessed by AI agents via function calls, which aligns with the workflow.

---

## Current Implementation Status

### Phase 1 Progress
- [x] **1.1 Database Schema:** `src/db/schema.py` - Hybrid Schema with JSONB
- [x] **1.2 Entity Resolver:** `src/utils/entity_resolver.py` - Multi-tier resolution
- [x] **Alembic Migration:** `src/db/alembic/versions/001_hybrid_schema_foundation.py`
- [ ] **1.3 Box Score Ingestor:** Not yet implemented
- [ ] **1.4 Odds Poller:** Not yet implemented

---

## Schema Reference

### Core Entities

| Table | Purpose | JSONB Fields |
|-------|---------|--------------|
| `leagues` | League configuration | `config` (rules, season info) |
| `teams` | Canonical teams | `aliases`, `season_stats` |
| `players` | Canonical players | `aliases`, `details` |

### Data Lake (Box Scores)

| Table | Purpose | JSONB Fields |
|-------|---------|--------------|
| `games` | Central game events | `environment` (weather, refs) |
| `player_game_logs` | **THE BOX SCORE** | `stats` (sport-specific) |

### Market & Execution

| Table | Purpose | JSONB Fields |
|-------|---------|--------------|
| `odds_snapshots` | CLV/Steam tracking | `markets` (all book odds) |
| `wagers` | Betting ledger | None |

### Entity Resolution

| Table | Purpose |
|-------|---------|
| `canonical_names` | Maps scraper aliases to UUIDs |

---

## Example Queries

### Get Player's Last 5 Games (NBA)
```sql
SELECT
    g.date,
    pgl.stats->>'pts' as points,
    pgl.stats->>'reb' as rebounds,
    pgl.stats->>'ast' as assists
FROM player_game_logs pgl
JOIN games g ON pgl.game_id = g.id
WHERE pgl.player_id = 'uuid-lebron-james'
ORDER BY g.date DESC
LIMIT 5;
```

### Get Player Props Performance
```sql
SELECT
    AVG((stats->>'pts')::float) as avg_pts,
    STDDEV((stats->>'pts')::float) as stddev_pts
FROM player_game_logs
WHERE player_id = 'uuid-lebron-james'
AND game_id IN (SELECT id FROM games WHERE date > NOW() - INTERVAL '30 days');
```

### Search JSONB Stats
```sql
-- Find all games where a player scored 30+ points
SELECT * FROM player_game_logs
WHERE (stats->>'pts')::int >= 30;
```

---

## Deployment

### Docker Container Setup
```dockerfile
# Dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

### Environment Variables
```env
DATABASE_URL=postgresql://user:pass@host:5432/omega_sports
ODDS_API_KEY=xxx
BALLDONTLIE_API_KEY=xxx
```

### Running Migrations
```bash
# Apply migrations
alembic upgrade head

# Generate new migration after schema changes
alembic revision --autogenerate -m "description"
```
