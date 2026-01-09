# Historical Data Collection Guide

## ✅ IMPLEMENTED: Multi-Source Historical Data Scraping

The Validation Lab now includes **REAL historical data scraping** from Sports Reference sites. NO MOCK OR SAMPLE DATA is used.

### Automatic Data Sources

The system automatically scrapes real historical game data from:

✅ **Basketball Reference** (NBA)
- URL: https://www.basketball-reference.com/
- Provides: Game results, scores, dates (2000-present)
- Implementation: `omega/historical_scrapers.py` - `BasketballReferenceScraper`

✅ **Pro Football Reference** (NFL)
- URL: https://www.pro-football-reference.com/
- Provides: Game results, scores, dates (2000-present)
- Implementation: `omega/historical_scrapers.py` - `ProFootballReferenceScraper`

🚧 **Coming Soon**: NCAAB, NCAAF, NHL, MLB scrapers

### How It Works

When you run the data loading script, the system:

1. **Checks cache first** - Avoids re-scraping if data exists
2. **Scrapes from Sports Reference** - Fetches REAL historical games
3. **Respects rate limits** - 1 request per 2 seconds (ethical scraping)
4. **Caches results** - 24-hour cache to minimize requests
5. **Saves to database** - Persistent storage in `data/historical/`

### Usage

```bash
# Load NBA historical data (2020-2024)
python scripts/load_and_validate_games.py \
    --sports NBA \
    --start-year 2020 \
    --end-year 2024

# Load NFL historical data
python scripts/load_and_validate_games.py \
    --sports NFL \
    --start-year 2020 \
    --end-year 2024

# Load multiple sports
python scripts/load_and_validate_games.py \
    --sports NBA NFL \
    --start-year 2020 \
    --end-year 2024
```

### What Data Is Scraped

For each game, the scrapers collect:

- ✅ Game ID (unique identifier)
- ✅ Date (YYYY-MM-DD format)
- ✅ Home Team
- ✅ Away Team  
- ✅ Home Score (final)
- ✅ Away Score (final)
- ✅ Sport/League
- ✅ Source attribution

**Note**: Betting lines (moneyline, spread, total) are not available from free Sports Reference sites. For betting data, see "Adding Betting Lines" section below.

### Rate Limiting & Ethics

The scrapers follow ethical web scraping practices:

- **Rate Limited**: 1 request per 2 seconds (0.5 req/sec)
- **User-Agent**: Identifies as a browser
- **Caching**: 24-hour cache to minimize requests
- **Respectful**: Delays between seasons
- **Attribution**: Source is recorded in each game

### Performance

Expected scraping times:

- **NBA Season**: ~5-10 minutes (82 games/team × 30 teams = ~1,230 games)
- **NFL Season**: ~2-3 minutes (272 regular season games)
- **Full 5 years NBA**: ~50 minutes (with rate limiting)
- **Full 5 years NFL**: ~15 minutes (with rate limiting)

**First run takes longer. Subsequent runs use cache and are instant.**

1. **The Odds API** (Historical Odds)
   ```python
   # Requires API key in .env: THE_ODDS_API_KEY=your_key
   # Documentation: https://the-odds-api.com/
   ```

2. **BallDontLie API** (NBA Historical Stats)
   ```python
   # Requires API key in .env: BALLDONTLIE_API_KEY=your_key
   # Documentation: https://www.balldontlie.io/
   ```

3. **SportsData.io**
   - Comprehensive sports data
   - Multiple sports supported
   - Historical data available

### Option 4: Web Scraping (Advanced)

The OmegaSportsAgent includes a `scraper_engine.py` for web scraping:

```python
from omega.scraper_engine import ScraperEngine

scraper = ScraperEngine()
# Note: Requires additional implementation for historical data
```

## Recommended Approach for Phase 2

### Short-term (Testing)

1. **Use sample data** for initial module testing
2. **Collect recent data** (last 7-30 days) using ESPN API
3. **Test algorithms** with limited dataset

```bash
# Get today's games for testing
python -c "
from omega.scraper_engine import ScraperEngine
scraper = ScraperEngine()
games = scraper.fetch_games('NBA')
print(f'Fetched {len(games)} current games')
"
```

### Medium-term (Production)

1. **Implement data aggregation** from multiple free sources
2. **Create data collection scripts** to build historical database
3. **Cache and store** in local database

```python
# Example: Collect data over time
# Run daily to build historical database
from core.data_pipeline import DataPipeline

pipeline = DataPipeline()
# Fetch and cache today's games
games = pipeline.fetch_and_cache_games('NBA', 2024, 2024)
```

### Long-term (Scale)

1. **Subscribe to paid APIs** for reliable historical data
2. **Implement automated data pipelines**
3. **Build comprehensive historical database**

## Current Testing Workaround

For immediate testing of Phase 2 modules:

```python
# Create synthetic test data based on sample games
from core.data_pipeline import DataPipeline
import json

pipeline = DataPipeline()

# Load sample games
with open('data/historical/sample_nba_2024_games.json') as f:
    sample_games = json.load(f)

# Replicate for testing (not real data, but structure is correct)
print(f"Using {len(sample_games)} sample games for testing")

# Test Module 1 with sample data
# python -m modules.01_edge_threshold.run_experiment
```

## API Integration Status

| Data Source | Status | Historical Data | Cost |
|-------------|--------|----------------|------|
| ESPN API (via OmegaSportsAgent) | ✅ Active | ❌ No (7 days max) | Free |
| Basketball Reference | 📝 Manual | ✅ Yes (20+ years) | Free |
| The Odds API | 🔑 Requires Key | ✅ Yes (varies) | Paid |
| BallDontLie API | 🔑 Requires Key | ✅ Yes | Free Tier |

## Next Steps

1. **For immediate Phase 2 start**: Use sample data and current games
2. **For production validation**: Implement data collection from Sports Reference sites
3. **For scale**: Subscribe to commercial APIs with historical data

---

## Questions?

See:
- [PHASE_2_PLANNING.md](PHASE_2_PLANNING.md) for experiment details
- [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- [DATABASE_STORAGE_GUIDE.md](DATABASE_STORAGE_GUIDE.md) for storage information
