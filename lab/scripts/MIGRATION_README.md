# Grand Unification Migration Guide

This directory contains scripts to consolidate your legacy data architecture into a unified SQLite database (`data/sports_data.db`).

## 📊 Current State Analysis

Run this first to see what you have:

```bash
python scripts/audit_state.py
python scripts/audit_state.py --verbose  # For detailed breakdowns
```

**Current Database Status** (as of audit):
- ✅ **7,770 NBA games** (2019-2025 seasons)
- ⚠️ **46.8% enriched** with player stats (4,135 games missing)
- ⚠️ **15.3% have odds** data (1,191 games)
- ⚠️ **Perplexity cache**: Empty (legacy DB not yet migrated)

## 🚀 4-Step Migration Plan

### Step 1: Audit Current State

**Script**: `scripts/audit_state.py`

Inspects your `sports_data.db` and reports:
- Row counts for all tables (`games`, `odds_history`, `player_props`, `perplexity_cache`)
- Data quality metrics (% of games with player stats, odds, etc.)
- Missing data identification

```bash
# Basic audit
python scripts/audit_state.py

# Verbose with season breakdowns
python scripts/audit_state.py --verbose
```

**Example Output**:
```
📊 GAMES TABLE
Total Games:      7,770
Completed Games:  7,767
With Scores:      7,770

📈 ENRICHMENT STATUS
Player Stats:     3,632 / 7,767 (46.8%)
Odds Data:        1,191 / 7,770 (15.3%)

⚠️  WARNING: 4,135 completed games missing player stats!

📋 RECOMMENDATIONS
⚠️  4,135 games missing player stats - run enrich_stats.py
✅ Odds history populated (3,570 records)
```

---

### Step 2: Migrate Legacy Data

**Script**: `scripts/finalize_migration.py`

Consolidates all scattered legacy data into `sports_data.db`:

1. **Perplexity Cache**: `data/cache/perplexity.db` → `perplexity_cache` table
2. **Game Results**: `data/historical/nba_*.json` → `games` table
   - ✅ Preserves `player_stats` JSON blobs
   - ✅ Updates scores and metadata
3. **Odds Data**: `data/odds_cache/**/*.json` → `odds_history` table
   - ✅ Separate rows for moneyline/spread/total
   - ✅ Matches to existing games by team + date

```bash
# Dry run first (see what would happen)
python scripts/finalize_migration.py --dry-run

# Execute migration
python scripts/finalize_migration.py

# Skip specific parts if needed
python scripts/finalize_migration.py --skip-perplexity
python scripts/finalize_migration.py --skip-odds
```

**What It Does**:
- Reads all `nba_2020_games.json`, `nba_2023_games.json`, `nba_2024_games.json`
- Inserts/updates games with scores, player stats, and betting lines
- Reads all odds_cache JSON files (230+ daily snapshots)
- Inserts odds into normalized `odds_history` table
- Merges old perplexity.db cache into unified database

**Expected Results**:
```
📊 MIGRATION SUMMARY
  Games Inserted:       500
  Games Updated:        7,270
  Odds Inserted:        25,000+
  Perplexity Migrated:  0 (if empty)

✅ Migration Complete!
```

---

### Step 3: Enrich Player Stats

**Script**: `scripts/enrich_stats.py`

Fills in missing player statistics using multiple data sources:

1. **BallDontLie API** (primary) - Structured NBA/NFL stats, 60 req/min
2. **ESPN Scraping** (fallback) - Box score data
3. **Perplexity** (last resort) - Web search if APIs fail

```bash
# Dry run to see what would be enriched
python scripts/enrich_stats.py --dry-run

# Enrich all NBA games missing stats
python scripts/enrich_stats.py --sport NBA

# Enrich specific season
python scripts/enrich_stats.py --sport NBA --season 2024

# Limit number of games (for testing)
python scripts/enrich_stats.py --limit 100

# Adjust rate limit (default: 1.0s = 60/min)
python scripts/enrich_stats.py --rate-limit 2.0  # Slower: 30/min
```

**What It Does**:
- Finds games where `has_player_stats = 0` or `player_stats IS NULL`
- Calls BallDontLie API to fetch player game logs
- Falls back to ESPN box score scraping if API unavailable
- Updates `games.player_stats` JSON column with structured data
- Sets `has_player_stats = 1` flag

**Player Stats Format**:
```json
[
  {
    "player_name": "LeBron James",
    "team": "Los Angeles Lakers",
    "minutes": "36:24",
    "points": 28,
    "rebounds": 7,
    "assists": 11,
    "steals": 2,
    "blocks": 1,
    "fg_made": 11,
    "fg_attempted": 21,
    "fg_pct": 0.524,
    "three_pt_made": 3,
    "three_pt_attempted": 8,
    "three_pt_pct": 0.375,
    "ft_made": 3,
    "ft_attempted": 4,
    "ft_pct": 0.750
  }
]
```

**Expected Results**:
```
📊 ENRICHMENT SUMMARY
Total Missing:  4,135
Enriched:       4,000
Failed:         135
Success Rate:   96.7%

✅ Enrichment Complete!

---

### Step 3.5: Backfill Player Props Actuals

**Script**: `scripts/backfill_player_props.py`

Creates `player_props` rows (actual outcomes) from the `games.player_stats` JSON blobs.

```bash
# Backfill all enriched games
python scripts/backfill_player_props.py

# Backfill specific season
python scripts/backfill_player_props.py --sport NBA --season 2024

# Limit for testing
python scripts/backfill_player_props.py --limit 500
```

What it writes:
- One row per (game, player, prop_type)
- `prop_type` coverage: points, rebounds, assists, steals, blocks, turnovers, three_pt_made, fg_pct, three_pt_pct, ft_pct
- `actual_value` is filled; betting lines/odds remain NULL until collected

Expected outcome: `player_props` table populated with actual results, ready to join with `player_props_odds` once player prop lines are ingested.
```

---

### Step 4: Archive Legacy Files

**Script**: `scripts/archive_legacy.py`

Cleans up after successful migration:

1. Creates `data/archive/` directory
2. Moves historical JSON files → `data/archive/historical/`
3. Moves odds cache → `data/archive/odds_cache/`
4. Moves old `perplexity.db` → `data/archive/cache/`
5. Updates `DATABASE_STORAGE_GUIDE.md` with deprecation notice

```bash
# Dry run to see what would be archived
python scripts/archive_legacy.py --dry-run

# Execute archival (with verification)
python scripts/archive_legacy.py

# Skip verification (not recommended)
python scripts/archive_legacy.py --force
```

**Safety Features**:
- ✅ Verifies migration is complete before archiving
- ✅ Checks database has games and stats
- ✅ Prompts for confirmation if database looks incomplete
- ✅ Creates archive README with restoration instructions

**What Gets Archived**:
```
data/archive/
├── historical/
│   ├── nba_2020_games.json
│   ├── nba_2023_games.json
│   └── nba_2024_games.json
├── odds_cache/
│   └── nba/
│       ├── 2023/ (82 files)
│       └── 2024/ (148 files)
├── cache/
│   └── perplexity.db
└── README.md (restoration guide)
```

---

## 📋 Complete Workflow

Execute all 4 steps in order:

```bash
# Step 1: Check current state
python scripts/audit_state.py --verbose

# Step 2: Migrate legacy data
python scripts/finalize_migration.py

# Verify migration
python scripts/audit_state.py

# Step 3: Enrich missing player stats
python scripts/enrich_stats.py --sport NBA

# Verify enrichment
python scripts/audit_state.py

# Step 4: Archive legacy files (after verification)
python scripts/archive_legacy.py

# Final audit
python scripts/audit_state.py --verbose
```

---

## 🎯 Expected Final State

After completing all steps:

```
📊 OMEGASPORTS DATABASE AUDIT REPORT

💾 Database Size: ~200 MB

🏀 GAMES TABLE
Total Games:      7,770
Player Stats:     7,767 / 7,767 (100%)  ✅
Odds Data:        7,770 / 7,770 (100%)  ✅

💰 ODDS HISTORY TABLE
Total Odds:       25,000+
Unique Games:     7,770

🎯 PLAYER PROPS TABLE
Total Props:      0 (optional for future)

🧠 PERPLEXITY CACHE TABLE
Total Entries:    0 (or migrated count)

📋 SUMMARY
✅ All completed games have player stats
✅ Odds history populated
✅ Legacy files archived
```

---

## 🔧 Troubleshooting

### Migration Fails with "No such table"

The database schema may be outdated. Check table existence:

```bash
sqlite3 data/sports_data.db ".tables"
```

Expected tables: `games`, `odds_history`, `player_props`, `perplexity_cache`

### Player Stats Enrichment Slow

BallDontLie API has rate limits (60 req/min). For faster enrichment:

```bash
# Increase rate limit (if you have higher tier)
python scripts/enrich_stats.py --rate-limit 0.5  # 120/min

# Or enrich in batches
python scripts/enrich_stats.py --limit 500
```

### Archive Fails Verification

If database looks incomplete:

```bash
# Check game count
sqlite3 data/sports_data.db "SELECT COUNT(*) FROM games;"

# Check player stats coverage
sqlite3 data/sports_data.db "SELECT COUNT(*) FROM games WHERE has_player_stats = 1;"

# Force archive (skip verification)
python scripts/archive_legacy.py --force
```

---

## 📚 Related Documentation

- **SQLITE_MIGRATION_COMPLETE.md** - Primary data architecture reference
- **API_USAGE_GUIDE.md** - How to query the unified database
- **DATA_SCHEMA.md** - Table schemas and relationships
- **GETTING_STARTED.md** - Quick start guide

---

## ⚠️ Legacy Systems (DEPRECATED)

**Do not use** after completing migration:

- ❌ `DATABASE_STORAGE_GUIDE.md` (JSON-based system)
- ❌ `data/historical/*.json` (archived)
- ❌ `data/odds_cache/` (archived)
- ❌ `data/cache/perplexity.db` (archived)

**Use instead**: `data/sports_data.db` (unified SQLite database)

---

## 🎉 Benefits of Unified System

**Before** (Legacy):
- Multiple JSON files (50MB+ each)
- Separate odds cache directories
- Standalone perplexity.db
- ❌ Hanging processes
- ❌ No resume capability
- ❌ Memory inefficiency

**After** (Unified):
- Single `sports_data.db` (~200 MB)
- All data in SQL tables
- ✅ Crash-safe writes (WAL mode)
- ✅ Concurrent access
- ✅ Indexed queries (fast backtesting)
- ✅ Resume capability

---

*Migration scripts created: January 3, 2026*
*For questions or issues, check GETTING_STARTED.md*
