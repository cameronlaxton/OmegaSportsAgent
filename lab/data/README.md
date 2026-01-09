# Data Directory

This directory stores all data used by the OmegaSports Validation Lab, including historical games, cached responses, experiment results, and logs.

## Directory Structure

```
data/
├── cache/              # Cached API responses for efficiency
├── historical/         # Historical game data (2020-2024)
├── experiments/        # Experiment results and analysis
└── logs/              # Application and script logs
```

## Subdirectories

### cache/

Stores cached API responses to minimize redundant network requests and improve performance.

- **Format**: JSON files
- **Naming**: `hist_{sport}_{startdate}_{enddate}.json`
- **Retention**: 30 days (automatically expired)
- **Purpose**: Speed up repeated data fetches

**Note**: This directory is git-ignored and regenerates automatically.

### historical/

Contains historical game data with comprehensive statistics for multiple sports.

- **Format**: JSON files
- **Naming**: `{sport}_{year}_games.json` (e.g., `nba_2024_games.json`)
- **Sports**: NBA, NFL, NCAAB, NCAAF
- **Years**: 2020-2024
- **Contents**: Game results, scores, team stats, player stats, betting lines

**Data Structure** (per game):
```json
{
  "game_id": "unique_id",
  "date": "YYYY-MM-DD",
  "sport": "NBA|NFL|NCAAB|NCAAF",
  "league": "NBA|NFL|NCAAB|NCAAF",
  "home_team": "Team Name",
  "away_team": "Team Name",
  "home_score": 114,
  "away_score": 105,
  "status": "final",
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
  "home_team_stats": {
    "field_goal_pct": "48.9",
    "three_point_pct": "38.5",
    "rebounds": "45",
    "assists": "28"
  },
  "away_team_stats": { ... },
  "venue": "Venue Name",
  "attendance": 18997
}
```

**Example Files**:
- `nba_2024_games.json` - All NBA games from 2024 season
- `nfl_2023_games.json` - All NFL games from 2023 season
- `sample_nba_2024_games.json` - Sample data demonstrating format

### experiments/

Stores results from experimental modules (edge threshold testing, iteration optimization, etc.).

- **Format**: JSON files
- **Naming**: `module_{number}_results.json`
- **Contents**: Experiment parameters, results, analysis, recommendations

**Example**:
- `module_01_results.json` - Edge threshold calibration results

### logs/

Application and script execution logs for debugging and monitoring.

- **Format**: Log files (`.log`)
- **Key files**:
  - `load_games.log` - Historical data loading activity
  - `experiments.log` - Experiment execution logs
  - `pipeline.log` - Data pipeline operations

**Note**: Log files are git-ignored and rotate automatically.

## Data Fetching

Historical game data is fetched using the `scripts/load_and_validate_games.py` script:

```bash
# Fetch all sports for 2020-2024
python scripts/load_and_validate_games.py

# Fetch specific sport
python scripts/load_and_validate_games.py --sports NBA

# Custom date range
python scripts/load_and_validate_games.py --start-year 2022 --end-year 2024
```

## Data Sources

The validation lab fetches data from multiple sources to ensure comprehensive coverage:

1. **ESPN API** - Primary source for:
   - Game schedules and results
   - Final scores
   - Basic team statistics
   - Venue and attendance information

2. **Historical Statistics** - Enhanced data including:
   - Detailed team performance metrics
   - Player statistics (when available)
   - Advanced analytics
   - Box score data

3. **Betting Lines** - Odds and lines data:
   - Moneyline odds
   - Point spreads
   - Totals (over/under)
   - Line movements (when available)

**Note**: The scraper goes beyond ESPN's scheduler API to fetch comprehensive historical data with statistics, not just upcoming game schedules.

## Data Quality

All data is validated before storage using `core.data_pipeline.DataValidator`:

- Required fields present
- Valid date formats
- Valid sport types
- Non-empty team names
- Reasonable score ranges
- Proper bet line formats

## Storage Limits

To manage disk space:
- Historical data: Keep all (archived annually)
- Cache: 30-day retention
- Logs: 90-day retention (configurable)
- Experiments: Keep all

## Git Ignore Patterns

The following files are git-ignored:
```
data/historical/*.json      # Historical data (except sample files)
data/experiments/*.json
data/logs/*.log
data/cache/
```

Sample files (e.g., `sample_*.json`) are tracked in git to demonstrate format.

## Maintenance

Regular maintenance tasks:

1. **Clear expired cache**: 
   ```bash
   find data/cache -name "*.json" -mtime +30 -delete
   ```

2. **Rotate logs**:
   ```bash
   find data/logs -name "*.log" -mtime +90 -delete
   ```

3. **Backup historical data**:
   ```bash
   tar -czf backup_historical_$(date +%Y%m%d).tar.gz data/historical/
   ```

## Support

For issues with data loading or validation:
1. Check `data/logs/load_games.log` for errors
2. Verify network connectivity
3. Ensure sufficient disk space
4. Review API rate limits
