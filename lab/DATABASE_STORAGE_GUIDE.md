# Database Storage Guide

## Overview

**YES**, the system **automatically stores all historical and future data + stats in a database**. The storage pipeline is fully implemented and ready to use.

## Database Architecture

### Storage System: File-Based JSON Database

The system uses a **file-based JSON database** with automatic organization by sport and year.

**Why JSON?**
- ✅ Human-readable for debugging
- ✅ Easy to version control (with git)
- ✅ No external database server required
- ✅ Simple backup and restoration
- ✅ Fast for research/analysis workloads
- ✅ Easy to migrate to SQL later if needed

### Directory Structure

```
data/
├── cache/                          # Temporary API response cache (30-day retention)
│   ├── hist_NBA_20240101_20240107.json
│   └── hist_NFL_20240108_20240114.json
│
├── historical/                     # PERMANENT DATABASE - All game data stored here
│   ├── nba_2020_games.json        # All NBA games from 2020
│   ├── nba_2021_games.json        # All NBA games from 2021
│   ├── nba_2022_games.json        # All NBA games from 2022
│   ├── nba_2023_games.json        # All NBA games from 2023
│   ├── nba_2024_games.json        # All NBA games from 2024
│   ├── nfl_2020_games.json        # All NFL games from 2020
│   ├── nfl_2021_games.json        # ...and so on
│   ├── nba_2020_props.json        # Player props for NBA 2020
│   └── nfl_2020_props.json        # Player props for NFL 2020
│
├── experiments/                    # Experiment results
│   └── module_01_results.json
│
└── logs/                          # Application logs
    └── load_games.log
```

## How Automatic Storage Works

### 1. Data Fetching & Storage Pipeline

When you run the load script, it **automatically**:

```bash
python scripts/load_and_validate_games.py --sports NBA NFL --start-year 2020 --end-year 2024
```

**What happens:**

```
1. Scraper fetches data from ESPN API (with multi-source enrichment)
   ↓
2. Data validation (ensures real data, not mocked)
   ↓
3. Multi-source enrichment (adds advanced stats)
   ↓
4. Cache storage (temporary, for efficiency)
   ↓
5. DATABASE STORAGE (permanent)
   - Organized by sport and year
   - Stored in data/historical/
   - JSON format for easy access
   ↓
6. Logging and statistics tracking
```

### 2. Automatic Organization

The `HistoricalDatabase` class automatically:

✅ **Creates files** by sport and year:
```python
# Automatically generates these filenames:
data/historical/nba_2024_games.json
data/historical/nfl_2024_games.json
data/historical/ncaab_2024_games.json
```

✅ **Validates data** before storage:
```python
# Only saves valid games
validator = DataValidator()
is_valid, error = validator.validate_game(game)
if is_valid:
    save_to_database(game)
```

✅ **Handles duplicates** (overwrites with latest data)

✅ **Creates directories** if they don't exist

### 3. What Gets Stored

#### Game Data Structure

Each game stored in the database includes:

```json
{
  "game_id": "401584708",
  "date": "2024-01-15",
  "sport": "NBA",
  "league": "NBA",
  "home_team": "Los Angeles Lakers",
  "away_team": "Boston Celtics",
  "home_score": 114,
  "away_score": 105,
  "status": "final",
  
  // Betting lines
  "moneyline": {
    "home": -150,
    "away": 130
  },
  "spread": {
    "line": -3.5,
    "home_odds": -110,
    "away_odds": -110
  },
  "total": {
    "line": 225.5,
    "over_odds": -110,
    "under_odds": -110
  },
  
  // Team statistics
  "home_team_stats": {
    "field_goal_pct": "48.9",
    "three_point_pct": "38.5",
    "free_throw_pct": "82.4",
    "rebounds": "45",
    "assists": "28",
    "turnovers": "12",
    "steals": "8",
    "blocks": "5"
  },
  "away_team_stats": { ... },
  
  // Additional info
  "venue": "Crypto.com Arena",
  "attendance": 18997,
  
  // Multi-source enrichments (when available)
  "advanced_stats": { ... },
  "player_stats": [ ... ],
  "odds_history": { ... }
}
```

#### Player Props Data Structure

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
  "actual_value": 28
}
```

## Using the Database

### 1. Loading Data from Database

```python
from core import DataPipeline

# Initialize pipeline
pipeline = DataPipeline(
    cache_dir="data/cache",
    data_dir="data/historical"
)

# Load all NBA games from 2020-2024
nba_games = pipeline.fetch_historical_games("NBA", 2020, 2024)
print(f"Loaded {len(nba_games)} NBA games")

# Load NFL games for 2024 only
nfl_games = pipeline.fetch_historical_games("NFL", 2024, 2024)

# Load player props
nba_props = pipeline.fetch_historical_props("NBA", 2024, 2024, prop_type="points")
```

### 2. Saving New Data to Database

```python
from core import DataPipeline, HistoricalDataScraper

# Initialize
pipeline = DataPipeline()
scraper = HistoricalDataScraper()

# Fetch new data (automatically fetches with multi-source enrichment)
new_games = scraper.fetch_historical_games("NBA", 2025, 2025)

# Save to database (automatically organized by year)
saved_count = pipeline.save_games(new_games, "NBA", 2025)
print(f"Saved {saved_count} games to database")
```

### 3. Querying Specific Data

```python
# Load data
games = pipeline.fetch_historical_games("NBA", 2024, 2024)

# Filter by team
lakers_games = [g for g in games if g['home_team'] == 'Los Angeles Lakers' 
                                   or g['away_team'] == 'Los Angeles Lakers']

# Filter by date range
import datetime
jan_games = [g for g in games if g['date'].startswith('2024-01')]

# Get games with betting lines
games_with_odds = [g for g in games if 'moneyline' in g]

# Get games with full statistics
games_with_stats = [g for g in games if 'home_team_stats' in g]
```

### 4. Checking Database Status

```python
from core import DataPipeline

pipeline = DataPipeline()

# Check what's stored
for sport in ['NBA', 'NFL', 'NCAAB', 'NCAAF']:
    count = pipeline.get_game_count(sport, 2020, 2024)
    print(f"{sport}: {count} games in database")
```

## Workflow for Continuous Data Updates

### Initial Historical Load

```bash
# One-time: Load all historical data (2020-2024)
python scripts/load_and_validate_games.py \
    --start-year 2020 \
    --end-year 2024 \
    --sports NBA NFL NCAAB NCAAF
```

**Result**: All historical data stored in `data/historical/`

### Future Data Updates

```bash
# Update with 2025 data (run periodically)
python scripts/load_and_validate_games.py \
    --start-year 2025 \
    --end-year 2025 \
    --sports NBA NFL NCAAB NCAAF
```

**Result**: New 2025 data added to database in separate files

### Automated Daily Updates (Optional)

Create a scheduled task to run daily:

```bash
#!/bin/bash
# update_data.sh - Run this daily

# Calculate current year
YEAR=$(date +%Y)

# Update current year's data
python scripts/load_and_validate_games.py \
    --start-year $YEAR \
    --end-year $YEAR \
    --sports NBA NFL NCAAB NCAAF \
    --verbose

echo "Database updated: $(date)" >> data/logs/updates.log
```

**Schedule with cron** (Linux/Mac):
```bash
# Run daily at 6 AM
0 6 * * * /path/to/update_data.sh
```

**Schedule with Task Scheduler** (Windows):
- Create a scheduled task to run `update_data.bat` daily

## Database Management

### Backup Database

```bash
# Backup all historical data
tar -czf backup_$(date +%Y%m%d).tar.gz data/historical/

# Or use git (recommended)
git add data/historical/
git commit -m "Backup: $(date)"
git push
```

### Restore Database

```bash
# From tar backup
tar -xzf backup_20241231.tar.gz

# From git
git checkout main -- data/historical/
```

### Check Database Integrity

```python
from core import DataPipeline, DataValidator
from pathlib import Path
import json

pipeline = DataPipeline()

# Check all files
for file in Path("data/historical").glob("*_games.json"):
    with open(file) as f:
        games = json.load(f)
    
    valid_count = 0
    for game in games:
        is_valid, error = DataValidator.validate_game(game)
        if is_valid:
            valid_count += 1
        else:
            print(f"Invalid game in {file.name}: {error}")
    
    print(f"{file.name}: {valid_count}/{len(games)} valid games")
```

### Clean Up Old Cache

```bash
# Delete cache files older than 30 days
find data/cache -name "*.json" -mtime +30 -delete
```

## Performance & Scalability

### Current Capacity

**File sizes** (approximate):
- NBA season: ~2.5 MB (1,230 games)
- NFL season: ~600 KB (285 games)
- NCAAB season: ~10 MB (5,000 games)
- NCAAF season: ~1.6 MB (800 games)

**Total for 5 years** (2020-2024):
- All 4 sports: ~75 MB total
- Still very manageable for file-based storage

### When to Migrate to SQL

Consider migrating to PostgreSQL/MySQL if:
- ❌ Database exceeds 1 GB
- ❌ Need complex queries across years
- ❌ Multiple concurrent writes
- ❌ Need ACID transactions

For now, **JSON file storage is perfect** for:
- ✅ Research and analysis
- ✅ Single-user access
- ✅ Historical data (mostly read-only)
- ✅ Easy backup and version control
- ✅ Simple to understand and debug

## Integration with Experiments

The database automatically integrates with all experiment modules:

```python
# Module 1: Edge Threshold Calibration
from modules.module_01 import EdgeThresholdCalibration
from core import DataPipeline

pipeline = DataPipeline()

# Automatically loads from database
module = EdgeThresholdCalibration(pipeline)
module.run_experiment(sport="NBA", years=[2020, 2021, 2022, 2023, 2024])
```

## Summary

✅ **Automatic Storage**: Yes, fully implemented and working
✅ **Storage Location**: `data/historical/` (permanent database)
✅ **File Format**: JSON (organized by sport/year)
✅ **What's Stored**: Game results, scores, team stats, betting lines, player stats
✅ **Multi-Source Data**: Automatically enriched and stored
✅ **Validation**: Automatic validation before storage
✅ **Organization**: Auto-organized by sport and year
✅ **Loading**: Simple API to load data for analysis
✅ **Updates**: Can update with new data anytime
✅ **Backup**: Easy with tar or git
✅ **Performance**: Fast for research workloads
✅ **Scalability**: Handles years of data easily

**The database storage pipeline is complete and production-ready!**
