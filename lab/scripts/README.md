# Scripts Directory

This directory contains utility scripts for the OmegaSports Validation Lab.

## 🎯 Recommended Scripts (Use These)

### ✅ collect_historical_sqlite.py (PRIMARY COLLECTION SCRIPT)

**Modern SQLite-based historical data collection.**

Loads and validates historical game data (2020-2024) for sports betting analysis with SQLite storage.

**Features:**
- SQLite database storage (robust, concurrent-safe)
- Multi-threaded data collection
- Resume capability (won't lose progress)
- Comprehensive error handling
- Progress tracking and logging
- Supports multiple sports: NBA, NFL, NCAAB, NCAAF
- Includes player statistics and team metrics
- Retry logic for failed requests

**Usage Examples:**
```bash
# Collect NBA and NFL data (recommended starting point)
python scripts/collect_historical_sqlite.py \
    --sports NBA NFL \
    --start-year 2022 \
    --end-year 2024 \
    --workers 2

# Collect all 4 sports with 5-year history
python scripts/collect_historical_sqlite.py \
    --sports NBA NFL NCAAB NCAAF \
    --start-year 2020 \
    --end-year 2024 \
    --workers 4

# Resume interrupted collection
python scripts/collect_historical_sqlite.py \
    --sports NBA \
    --start-year 2023 \
    --end-year 2024 \
    --resume

# Check status of collection
python scripts/collect_historical_sqlite.py --status
```

**Output:**
- Saves to `data/sports_data.db` (SQLite database)
- Logs to `data/logs/collection_sqlite.log`
- Progress tracking in console

---

### ✅ check_status.py

**Check database status and data completeness.**

**Usage:**
```bash
python scripts/check_status.py
```

**Shows:**
- Number of games collected per sport/season
- Data completeness statistics
- Missing data gaps
- Database size and health

---

### ✅ load_and_validate_games.py (LEGACY JSON SUPPORT)

**Legacy JSON-based data loading for backward compatibility.**

Use this if you need JSON file output instead of SQLite database.

**Usage Examples:**
```bash
# Load specific sports to JSON
python scripts/load_and_validate_games.py --sports NBA NFL

# Custom year range
python scripts/load_and_validate_games.py \
    --start-year 2022 \
    --end-year 2024

# Verbose output
python scripts/load_and_validate_games.py --verbose
```

**Output:**
- Saves to `data/historical/{sport}_{year}_games.json`
- Logs to `data/logs/load_games.log`

---

### ✅ test_data_collection.py (NEW - VALIDATION)

**Comprehensive validation test suite for data collection.**

Tests that historical data collection endpoints return correct data, format matches schema, and data is properly stored.

**Features:**
- Database schema validation
- Data validation logic testing
- API endpoint verification
- Data integrity checks
- End-to-end pipeline testing

**Usage Examples:**
```bash
# Run all validation tests
python scripts/test_data_collection.py

# Test specific sport
python scripts/test_data_collection.py --sport NBA

# Verbose output
python scripts/test_data_collection.py --verbose
```

**What it validates:**
1. ✅ Database schema exists and is correct
2. ✅ Data validation logic works properly
3. ✅ Data in database meets schema requirements
4. ✅ API endpoints return data in correct format
5. ✅ Data collection pipeline is configured

**Output:**
- Pass/fail results for each test
- Detailed error messages for failures
- Summary statistics
- Recommendations for fixes

**Related:**
- See [DATA_SCHEMA.md](../DATA_SCHEMA.md) for complete schema documentation
- See [DATABASE_STORAGE_GUIDE.md](../DATABASE_STORAGE_GUIDE.md) for storage details

---

### ✅ test_api_integration.py

**Test API connections and validate configuration.**

**Usage:**
```bash
python scripts/test_api_integration.py
```

**Tests:**
- API key validity
- Network connectivity
- Data source availability
- Rate limiting compliance

---

## ⚠️ Deprecated Scripts (Archived)

**These scripts have been moved to `/archive/deprecated/` and should NOT be used.**

All deprecated scripts have been superseded by `collect_historical_sqlite.py` which provides:
- ✅ Unified SQLite storage (not fragmented JSON)
- ✅ Multi-threading support with `--workers` flag
- ✅ Crash recovery and resume capability
- ✅ Comprehensive error handling and validation
- ✅ Single script instead of 5+ overlapping scripts

### Archived Scripts:
- ❌ `bulk_collect.py` → Moved to archive
- ❌ `collect_games_only.py` → Moved to archive
- ❌ `collect_historical_5years.py` → Moved to archive
- ❌ `collect_historical_odds.py` → Moved to archive
- ❌ `collect_all_seasons.py` → Moved to archive
- ❌ `collect_data.py` → Moved to archive
- ❌ `run_collection_*.sh` → Moved to archive
- ❌ `monitor_collection.sh` → Moved to archive
- ❌ `check_collection_status.sh` → Moved to archive

**See:** `/archive/deprecated/README.md` for full details and rollback instructions if needed.

---

## 🧪 Experimental Scripts (Use With Caution)

### ⚠️ enrich_odds.py
**Status:** Experimental  
**Purpose:** Backfill odds for games missing betting lines  
**Note:** May not work reliably, use main collection script instead

### ⚠️ enrich_player_stats.py
**Status:** Experimental  
**Purpose:** Backfill player statistics  
**Note:** May not work reliably, use main collection script instead

---

## 📋 Migration Guide

### From Old Scripts to New

**Old approach:**
```bash
# DON'T DO THIS ANYMORE
python scripts/collect_historical_5years.py --sport NBA
python scripts/collect_historical_odds.py --sport NBA
python scripts/enrich_player_stats.py --sport NBA
```

**New approach:**
```bash
# DO THIS INSTEAD - Single unified script
python scripts/collect_historical_sqlite.py \
    --sports NBA NFL \
    --start-year 2020 \
    --end-year 2024 \
    --workers 2
```

**Benefits:**
- ✅ One script does everything
- ✅ Better error handling
- ✅ Resume capability
- ✅ Multi-threading support
- ✅ SQLite database (not fragmented JSON files)
- ✅ Better progress tracking

---

## 🗂️ Data Storage

### SQLite Database (Recommended)
```bash
data/sports_data.db          # Main database (36 MB)
├── games                    # Game results and statistics
├── player_props             # Player prop bets
├── odds_history             # Historical betting lines
├── player_props_odds        # Player prop odds
└── perplexity_cache         # API cache
```

### JSON Files (Legacy)
```bash
data/historical/
├── nba_2020_games.json     # Legacy JSON format
├── nba_2021_games.json
└── ...
```

---

## 🔧 Common Tasks

### Task 1: Initial Data Collection
```bash
# Start fresh with recommended sports and timeframe
python scripts/collect_historical_sqlite.py \
    --sports NBA NFL \
    --start-year 2022 \
    --end-year 2024 \
    --workers 2
```

### Task 2: Check What You Have
```bash
# Quick status check
python scripts/check_status.py

# Or query database directly
sqlite3 data/sports_data.db "
SELECT sport, COUNT(*) as game_count 
FROM games 
GROUP BY sport;
"
```

### Task 3: Resume Interrupted Collection
```bash
# Resume where you left off
python scripts/collect_historical_sqlite.py \
    --sports NBA \
    --resume
```

### Task 4: Backfill Specific Year
```bash
# Collect just 2023 data
python scripts/collect_historical_sqlite.py \
    --sports NBA NFL \
    --start-year 2023 \
    --end-year 2023
```

---

## 🆘 Troubleshooting

### "Script hangs or times out"
**Solution:** Use multi-threading with `--workers 2` or `--workers 4`

### "Database is locked"
**Solution:** Only run one collection script at a time, or check for stale `.pid` files

### "API rate limit exceeded"
**Solution:** Collection script has built-in rate limiting, just wait and resume

### "Missing data for specific games"
**Solution:** Use `check_status.py` to identify gaps, then re-run collection for that year

---

## 📚 Related Documentation

- **[START_HERE.md](../START_HERE.md)** - Repository navigation guide
- **[DATABASE_STORAGE_GUIDE.md](../DATABASE_STORAGE_GUIDE.md)** - Database architecture
- **[DATA_COLLECTION_GUIDE.md](../DATA_COLLECTION_GUIDE.md)** - Data collection details
- **[SQLITE_MIGRATION_COMPLETE.md](../SQLITE_MIGRATION_COMPLETE.md)** - Migration details

---

## 🔄 Quick Reference

| Task | Command |
|------|---------|
| **Collect data** | `python scripts/collect_historical_sqlite.py --sports NBA NFL` |
| **Check status** | `python scripts/check_status.py` |
| **Test APIs** | `python scripts/test_api_integration.py` |
| **Resume collection** | `python scripts/collect_historical_sqlite.py --resume` |
| **Query database** | `sqlite3 data/sports_data.db "SELECT * FROM games LIMIT 10;"` |

---

**Last Updated:** January 2, 2026  
**Recommended Script:** `collect_historical_sqlite.py`  
**Database:** SQLite at `data/sports_data.db`
