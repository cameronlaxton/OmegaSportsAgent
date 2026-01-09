# Data Schema Documentation

This document defines the complete data schema for the OmegaSports Validation Lab, ensuring consistency and stability across all data collection, storage, and analysis processes.

## Overview

The system uses SQLite for storage with 5 main tables:
1. `games` - Core game results and betting lines
2. `player_props` - Player performance betting lines
3. `odds_history` - Historical odds tracking
4. `player_props_odds` - Player prop odds history
5. `perplexity_cache` - LLM enrichment cache

## Table Schemas

### 1. Games Table

**Purpose:** Store game results, scores, and betting lines

**Schema:**
```sql
CREATE TABLE games (
    -- Identity
    game_id TEXT PRIMARY KEY,
    date TEXT NOT NULL,              -- Format: YYYY-MM-DD
    sport TEXT NOT NULL,             -- NBA, NFL, NCAAB, NCAAF
    league TEXT,
    season INTEGER,
    
    -- Teams and Scores
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    home_score INTEGER,              -- NULL for future games
    away_score INTEGER,              -- NULL for future games
    status TEXT,                     -- 'scheduled', 'in_progress', 'final'
    
    -- Betting Lines (Game Level)
    moneyline_home INTEGER,          -- e.g., -150
    moneyline_away INTEGER,          -- e.g., +130
    spread_line REAL,                -- e.g., -3.5 (negative = home favored)
    spread_home_odds INTEGER,        -- e.g., -110
    spread_away_odds INTEGER,        -- e.g., -110
    total_line REAL,                 -- e.g., 225.5
    total_over_odds INTEGER,         -- e.g., -110
    total_under_odds INTEGER,        -- e.g., -110
    
    -- Metadata
    venue TEXT,
    attendance INTEGER,
    
    -- Complex data (JSON)
    home_team_stats TEXT,            -- JSON: {"field_goal_pct": 48.9, ...}
    away_team_stats TEXT,            -- JSON: {...}
    player_stats TEXT,               -- JSON: [{"player": "Name", "points": 28, ...}, ...]
    
    -- Tracking
    created_at INTEGER,              -- Unix timestamp
    updated_at INTEGER,              -- Unix timestamp
    has_player_stats INTEGER DEFAULT 0,
    has_odds INTEGER DEFAULT 0,
    has_perplexity INTEGER DEFAULT 0
);
```

**Indexes:**
```sql
CREATE INDEX idx_games_date ON games(date);
CREATE INDEX idx_games_sport ON games(sport);
CREATE INDEX idx_games_sport_date ON games(sport, date);
CREATE INDEX idx_games_sport_season ON games(sport, season);
CREATE INDEX idx_games_status ON games(sport, status);
```

**Example Data:**
```json
{
    "game_id": "401584708",
    "date": "2024-01-15",
    "sport": "NBA",
    "league": "NBA",
    "season": 2024,
    "home_team": "Los Angeles Lakers",
    "away_team": "Boston Celtics",
    "home_score": 114,
    "away_score": 105,
    "status": "final",
    "moneyline_home": -150,
    "moneyline_away": 130,
    "spread_line": -3.5,
    "spread_home_odds": -110,
    "spread_away_odds": -110,
    "total_line": 225.5,
    "total_over_odds": -110,
    "total_under_odds": -110,
    "venue": "Crypto.com Arena",
    "attendance": 18997,
    "has_player_stats": 1,
    "has_odds": 1
}
```

### 2. Player Props Table

**Purpose:** Store player performance betting lines and results

**Schema:**
```sql
CREATE TABLE player_props (
    -- Identity
    prop_id TEXT PRIMARY KEY,
    game_id TEXT NOT NULL,
    date TEXT NOT NULL,              -- Format: YYYY-MM-DD
    sport TEXT NOT NULL,
    
    -- Player Info
    player_name TEXT NOT NULL,
    player_id TEXT,
    player_team TEXT NOT NULL,
    opponent_team TEXT NOT NULL,
    
    -- Prop Details
    prop_type TEXT NOT NULL,         -- See prop types by sport below
    over_line REAL,                  -- e.g., 27.5 points
    under_line REAL,                 -- Usually same as over_line
    over_odds INTEGER,               -- e.g., -110
    under_odds INTEGER,              -- e.g., -110
    actual_value REAL,               -- Actual player performance (NULL if game not played)
    
    -- Metadata
    bookmaker TEXT,
    created_at INTEGER,
    updated_at INTEGER,
    
    FOREIGN KEY (game_id) REFERENCES games(game_id)
);
```

**Indexes:**
```sql
CREATE INDEX idx_props_game ON player_props(game_id);
CREATE INDEX idx_props_player ON player_props(player_name);
CREATE INDEX idx_props_type ON player_props(prop_type);
CREATE INDEX idx_props_sport_date ON player_props(sport, date);
CREATE INDEX idx_props_player_date ON player_props(player_name, date);
CREATE INDEX idx_props_player_type ON player_props(player_name, prop_type);
```

**Example Data:**
```json
{
    "prop_id": "nba_prop_12345",
    "game_id": "401584708",
    "date": "2024-01-15",
    "sport": "NBA",
    "player_name": "LeBron James",
    "player_team": "Los Angeles Lakers",
    "opponent_team": "Boston Celtics",
    "prop_type": "points",
    "over_line": 27.5,
    "under_line": 27.5,
    "over_odds": -110,
    "under_odds": -110,
    "actual_value": 28.0,
    "bookmaker": "DraftKings"
}
```

### 3. Odds History Table

**Purpose:** Track historical betting line movements

**Schema:**
```sql
CREATE TABLE odds_history (
    game_id TEXT NOT NULL,
    bookmaker TEXT NOT NULL,
    market_type TEXT NOT NULL,       -- 'moneyline', 'spread', 'total'
    timestamp INTEGER NOT NULL,       -- Unix timestamp
    
    -- Odds values
    home_odds INTEGER,
    away_odds INTEGER,
    line REAL,                       -- For spread/total
    
    PRIMARY KEY (game_id, bookmaker, market_type, timestamp),
    FOREIGN KEY (game_id) REFERENCES games(game_id)
);
```

**Indexes:**
```sql
CREATE INDEX idx_odds_game ON odds_history(game_id);
CREATE INDEX idx_odds_bookmaker ON odds_history(bookmaker);
CREATE INDEX idx_odds_timestamp ON odds_history(timestamp);
```

## Data Validation Rules

### Game Data Validation

**Required Fields:**
- `game_id` (non-empty string)
- `date` (YYYY-MM-DD format)
- `sport` (must be: NBA, NFL, NCAAB, NCAAF, MLB, NHL)
- `league` (non-empty string)
- `home_team` (non-empty string)
- `away_team` (non-empty string)

**Validation Rules:**
1. Date must be valid YYYY-MM-DD format
2. Sport must be from valid sports list
3. Teams must be different (home_team ≠ away_team)
4. If scores present, must be non-negative integers
5. Odds values must be integers (e.g., -110, +150)
6. Lines must be floats (e.g., -3.5, 225.5)

**Python Validation:**
```python
from core.data_pipeline import DataValidator

validator = DataValidator()
is_valid, error = validator.validate_game(game_dict)
```

### Player Prop Data Validation

**Required Fields:**
- `prop_id` (non-empty string)
- `game_id` (non-empty string)
- `date` (YYYY-MM-DD format)
- `sport` (must be from valid sports)
- `player_name` (non-empty string)
- `player_team` (non-empty string)
- `opponent_team` (non-empty string)
- `prop_type` (must be valid for sport - see below)

**Validation Rules:**
1. All game validation rules apply for shared fields
2. prop_type must be valid for the sport
3. Lines must be positive floats
4. Odds must be integers
5. actual_value (if present) must be non-negative float

**Python Validation:**
```python
from core.data_pipeline import DataValidator

validator = DataValidator()
is_valid, error = validator.validate_prop(prop_dict)
```

## Prop Types by Sport

### Basketball (NBA, NCAAB)
```python
BASKETBALL_PROPS = [
    "points",
    "rebounds",
    "assists",
    "three_pointers",
    "threes_made",         # Legacy alias
    "steals",
    "blocks",
    "points_rebounds",     # Combo props
    "points_assists",
    "rebounds_assists"
]
```

### Football (NFL, NCAAF)
```python
FOOTBALL_PROPS = [
    "passing_yards",
    "rushing_yards",
    "receiving_yards",
    "receptions",
    "rushing_attempts",
    "passing_attempts",
    "passing_completions",
    "touchdowns",          # Any touchdown
    "passing_tds",
    "rushing_tds",
    "receiving_tds",
    "interceptions",
    "completion_pct",
    "sacks"
]
```

## Data Sources and Endpoints

### 1. BallDontLie API (NBA Games)
**Endpoint:** `https://api.balldontlie.io/v1/games`

**Returns:**
```json
{
    "id": 12345,
    "date": "2024-01-15T00:00:00.000Z",
    "home_team": {
        "id": 13,
        "full_name": "Los Angeles Lakers",
        "abbreviation": "LAL"
    },
    "visitor_team": {
        "id": 2,
        "full_name": "Boston Celtics",
        "abbreviation": "BOS"
    },
    "home_team_score": 114,
    "visitor_team_score": 105
}
```

**Mapping to Schema:**
- `id` → `game_id` (convert to string, prefix with "bdl_")
- `date` → `date` (convert to YYYY-MM-DD)
- `home_team.full_name` → `home_team`
- `visitor_team.full_name` → `away_team`
- `home_team_score` → `home_score`
- `visitor_team_score` → `away_score`

### 2. The Odds API (Betting Lines)
**Endpoint:** `https://api.the-odds-api.com/v4/sports/{sport}/odds`

**Returns:**
```json
{
    "id": "abc123",
    "sport_key": "basketball_nba",
    "commence_time": "2024-01-15T19:30:00Z",
    "home_team": "Los Angeles Lakers",
    "away_team": "Boston Celtics",
    "bookmakers": [
        {
            "key": "draftkings",
            "markets": [
                {
                    "key": "h2h",
                    "outcomes": [
                        {"name": "Los Angeles Lakers", "price": -150},
                        {"name": "Boston Celtics", "price": 130}
                    ]
                },
                {
                    "key": "spreads",
                    "outcomes": [
                        {"name": "Los Angeles Lakers", "price": -110, "point": -3.5},
                        {"name": "Boston Celtics", "price": -110, "point": 3.5}
                    ]
                },
                {
                    "key": "totals",
                    "outcomes": [
                        {"name": "Over", "price": -110, "point": 225.5},
                        {"name": "Under", "price": -110, "point": 225.5}
                    ]
                }
            ]
        }
    ]
}
```

**Mapping to Schema:**
- Find home team in h2h outcomes → `moneyline_home`
- Find away team in h2h outcomes → `moneyline_away`
- Find home team in spreads → `spread_line` (negative for home favorite)
- Get spread prices → `spread_home_odds`, `spread_away_odds`
- Get totals → `total_line`, `total_over_odds`, `total_under_odds`

### 3. ESPN API (Historical Games)
**Endpoint:** `https://site.api.espn.com/apis/site/v2/sports/{sport}/scoreboard`

**Returns:** Similar structure to BallDontLie but includes more metadata

## Testing Data Collection

### Run Validation Tests
```bash
# Test all components
python scripts/test_data_collection.py

# Test specific sport
python scripts/test_data_collection.py --sport NBA

# Verbose output
python scripts/test_data_collection.py --verbose
```

### What Gets Tested
1. ✅ Database schema exists and is correct
2. ✅ Data validation logic works
3. ✅ Data in database meets schema requirements
4. ✅ API endpoints return data in correct format
5. ✅ Data collection pipeline is configured

### Verify Collected Data
```bash
# Check database contents
sqlite3 data/sports_data.db "
SELECT sport, COUNT(*) as games, 
       SUM(CASE WHEN has_odds = 1 THEN 1 ELSE 0 END) as with_odds
FROM games 
GROUP BY sport;
"

# Validate specific game
sqlite3 data/sports_data.db "
SELECT game_id, date, home_team, away_team, home_score, away_score,
       moneyline_home, spread_line, total_line
FROM games 
WHERE game_id = '401584708';
"
```

## Consistency Guarantees

### Data Integrity
1. **Primary Keys:** All tables use appropriate primary keys to prevent duplicates
2. **Foreign Keys:** Relationships enforced via foreign key constraints
3. **NOT NULL:** Critical fields marked NOT NULL
4. **Indexes:** Fast queries via strategic indexing
5. **Validation:** All data validated before storage

### Thread Safety
1. **WAL Mode:** Write-Ahead Logging enabled for concurrent access
2. **Connection Pooling:** Thread-local connections prevent conflicts
3. **Transaction Support:** ACID properties maintained

### Schema Stability
1. **Versioned Schema:** Schema changes tracked via migration scripts
2. **Backward Compatibility:** New fields added as nullable or with defaults
3. **Validation Tests:** Schema validated on every test run

## Common Issues and Solutions

### Issue: "Missing required field: sport"
**Cause:** Data source didn't include sport field
**Solution:** Ensure sport is explicitly set in data collection code

### Issue: "Invalid date format"
**Cause:** Date not in YYYY-MM-DD format
**Solution:** Convert dates using `datetime.strftime("%Y-%m-%d")`

### Issue: "Invalid prop type for NBA: touchdowns"
**Cause:** Using wrong prop type for sport
**Solution:** Check BASKETBALL_PROPS or FOOTBALL_PROPS lists

### Issue: "Database is locked"
**Cause:** Multiple writers without WAL mode
**Solution:** Ensure DatabaseManager uses WAL mode (automatic)

## Reference Implementation

See these files for complete implementation:
- **Schema:** `core/db_manager.py` (lines 79-250)
- **Validation:** `core/data_pipeline.py` (lines 68-210)
- **Collection:** `scripts/collect_historical_sqlite.py`
- **Testing:** `scripts/test_data_collection.py`

## Version History

- **v1.0** (2026-01-02): Initial schema definition with 5 tables
- **v1.1** (2026-01-02): Added comprehensive validation and testing suite

---

**Last Updated:** January 2, 2026  
**Schema Version:** 1.1  
**Status:** Production-ready
