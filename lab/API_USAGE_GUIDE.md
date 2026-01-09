# API Usage Guide

Quick reference for using The Odds API and BallDontLie API in the OmegaSports Validation Lab.

---

## Quick Start

### 1. Check API Connectivity

```python
from omega.odds_api_client import TheOddsAPIClient
from omega.balldontlie_client import BallDontLieClient

# Test The Odds API
odds_client = TheOddsAPIClient()
usage = odds_client.check_usage()
print(f"Requests remaining: {usage['requests_remaining']}")

# Test BallDontLie API  
bdl_client = BallDontLieClient()
games = bdl_client.get_games("2024-03-15", "2024-03-15")
print(f"Fetched {len(games)} games")
```

### 2. Fetch Current Betting Odds

```python
from omega.odds_api_client import TheOddsAPIClient

client = TheOddsAPIClient()

# Get current NBA odds (upcoming games)
odds = client.get_historical_odds(
    sport="NBA",
    date="2024-12-31",  # Today's date for current odds
    markets=["h2h", "spreads", "totals"],
    regions="us"
)

for game in odds:
    print(f"{game['away_team']} @ {game['home_team']}")
    print(f"  Spread: {game['spread']}")
    print(f"  Total: {game['total']}")
    print(f"  Moneyline: {game['moneyline']}")
```

### 3. Fetch Game Statistics

```python
from omega.balldontlie_client import BallDontLieClient

client = BallDontLieClient()

# Get games for a date range
games = client.get_games("2024-03-01", "2024-03-15", sport="NBA")

for game in games:
    print(f"Game {game['id']}: {game['away_team']} @ {game['home_team']}")
    print(f"  Score: {game['away_score']} - {game['home_score']}")
    
    # Get detailed stats
    stats = client.get_game_stats(game['id'])
    if stats:
        print(f"  Home FG%: {stats.get('home_fg_pct', 'N/A')}")
```

### 4. Enrich ESPN Data with Odds

```python
from omega.espn_historical_scraper import ESPNHistoricalScraper
from omega.api_enrichment import APIDataEnrichment

# Fetch ESPN games
scraper = ESPNHistoricalScraper()
games = scraper.fetch_nba_games("2024-03-15", "2024-03-17")

print(f"Before enrichment: {len(games)} games")
print(f"Games with odds: {sum(1 for g in games if g.get('moneyline'))}")

# Enrich with betting lines
enrichment = APIDataEnrichment()
enriched_games = enrichment.enrich_games(games)

print(f"After enrichment: {len(enriched_games)} games")  
print(f"Games with odds: {sum(1 for g in enriched_games if (g.get('moneyline') or {}).get('home'))}")
```

---

## API Methods Reference

### TheOddsAPIClient

#### `get_historical_odds(sport, date, markets=None, regions="us")`
Fetch betting odds for a specific date.

**Parameters:**
- `sport` (str): "NBA", "NFL", "NCAAB", "NCAAF", "NHL", "MLB"
- `date` (str): Date in "YYYY-MM-DD" format
- `markets` (list): ["h2h", "spreads", "totals"] - Default: all three
- `regions` (str): "us", "uk", "eu", "au" - Default: "us"

**Returns:** List of game dictionaries with odds

**Note:** Historical dates require paid plan. Falls back to current odds on free tier.

#### `enrich_game_with_odds(game, odds_cache=None)`
Add betting odds to an ESPN game dictionary.

**Parameters:**
- `game` (dict): Game from ESPN with home_team, away_team, date, sport
- `odds_cache` (dict): Optional cache {date: odds_list} to avoid repeated API calls

**Returns:** Game dictionary with added fields: moneyline, spread, total, num_bookmakers

#### `check_usage()`
Check remaining API quota.

**Returns:** Dictionary with requests_remaining, requests_used, status

---

### BallDontLieClient

#### `get_games(start_date, end_date, sport="NBA")`
Fetch games for a date range.

**Parameters:**
- `start_date` (str): "YYYY-MM-DD"
- `end_date` (str): "YYYY-MM-DD"  
- `sport` (str): "NBA" or "NFL"

**Returns:** List of game dictionaries

**Game fields:**
- `id`: BallDontLie game ID
- `date`: Game date
- `home_team`, `away_team`: Team names
- `home_score`, `away_score`: Final scores
- `status`: Game status
- `season`: Season year

#### `get_game_stats(game_id)`
Fetch detailed statistics for a specific game.

**Parameters:**
- `game_id` (int): BallDontLie game ID

**Returns:** Dictionary with team/player statistics or None

**Stats include:**
- Field goal percentages
- Three-point percentages
- Rebounds, assists, turnovers
- Minutes played
- Plus/minus

#### `get_team_stats(team_id, season)`
Fetch season statistics for a team.

**Parameters:**
- `team_id` (int): BallDontLie team ID
- `season` (int): Season year (e.g., 2024)

**Returns:** Team statistics dictionary

---

### APIDataEnrichment

#### `enrich_games(games, enrich_with_odds=True, enrich_with_stats=False)`
Orchestrate enrichment of game list with betting lines and stats.

**Parameters:**
- `games` (list): List of game dictionaries from ESPN
- `enrich_with_odds` (bool): Add betting lines from The Odds API - Default: True
- `enrich_with_stats` (bool): Add enhanced stats from BallDontLie - Default: False

**Returns:** List of enriched game dictionaries

**Enrichment adds:**
- `moneyline`: {"home": odds, "away": odds}
- `spread`: {"line": points, "home_odds": odds, "away_odds": odds}
- `total`: {"line": points, "over_odds": odds, "under_odds": odds}
- `num_bookmakers`: Number of bookmakers averaged

**Performance:** ~1 second per unique date (cached)

---

## Data Formats

### Odds Dictionary Structure

```python
{
    "moneyline": {
        "home": -150,  # American odds (negative = favorite)
        "away": 130    # American odds (positive = underdog)
    },
    "spread": {
        "line": -5.5,      # Points (negative = home favored)
        "home_odds": -110,  # Odds on home covering spread
        "away_odds": -110   # Odds on away covering spread
    },
    "total": {
        "line": 225.5,     # Total points line
        "over_odds": -105,  # Odds on over
        "under_odds": -115  # Odds on under
    },
    "num_bookmakers": 6  # Number of bookmakers averaged
}
```

### ESPN Game Structure

```python
{
    "game_id": "401584876",
    "sport": "NBA",
    "date": "2024-03-15",
    "home_team": "Charlotte Hornets",
    "away_team": "Phoenix Suns",
    "home_score": 96,
    "away_score": 107,
    "status": "completed",
    "venue": "Spectrum Center",
    
    # After enrichment:
    "moneyline": {...},
    "spread": {...},
    "total": {...},
    "num_bookmakers": 6
}
```

### BallDontLie Game Structure

```python
{
    "id": 1038553,
    "date": "2024-03-15",
    "season": 2024,
    "status": "Final",
    "home_team": "Charlotte Hornets",
    "away_team": "Phoenix Suns",
    "home_score": 96,
    "away_score": 107,
    "home_team_id": 5,
    "away_team_id": 21
}
```

---

## Rate Limits & Quotas

### The Odds API
- **Free Tier**: 500 requests/month
- **Rate Limit**: None specified (we use 1 req/sec)
- **Current Usage**: 36/500 used (7.2%)
- **Tracking**: Check with `client.check_usage()`

### BallDontLie API  
- **ALL-STAR Plan**: Unlimited requests
- **Rate Limit**: Respectful usage (we use 1 req/sec)
- **No quota restrictions**

---

## Best Practices

### 1. Use Caching for Odds

```python
from omega.odds_api_client import TheOddsAPIClient

client = TheOddsAPIClient()
odds_cache = {}  # Cache by date

# Enrich multiple games for same date
for game in games:
    enriched = client.enrich_game_with_odds(game, odds_cache)
    # Only fetches odds once per unique date
```

### 2. Batch Requests by Date

```python
# Group games by date first
from collections import defaultdict

games_by_date = defaultdict(list)
for game in all_games:
    games_by_date[game['date']].append(game)

# Fetch odds once per date
for date, date_games in games_by_date.items():
    odds = client.get_historical_odds("NBA", date)
    # Process all games for this date
```

### 3. Handle API Failures Gracefully

```python
from omega.api_enrichment import APIDataEnrichment

enrichment = APIDataEnrichment()

try:
    enriched_games = enrichment.enrich_games(games)
except Exception as e:
    print(f"Enrichment failed: {e}")
    # Games still usable without odds
    enriched_games = games
```

### 4. Monitor API Usage

```python
# Check usage before large batches
usage = odds_client.check_usage()
remaining = int(usage.get('requests_remaining', 0))

if remaining < 50:
    print("⚠️ Low API quota - consider batch sizing")
```

---

## Troubleshooting

### "Authentication failed" with The Odds API
- Verify API key in `.env`: `THE_ODDS_API_KEY=your_key_here`
- Check key is not expired at https://the-odds-api.com
- Ensure no extra spaces or quotes in `.env`

### No odds returned for historical dates
- **Free tier limitation**: Historical odds require paid plan
- Current workaround: Falls back to current/upcoming games
- Solution: Upgrade to historical data plan

### BallDontLie returns empty list
- Check date format is "YYYY-MM-DD"
- Verify date is within available range (2020-current for NBA)
- Check API key in `.env`: `BALLDONTLIE_API_KEY=your_key_here`

### Team names don't match between sources
- ESPN: "Charlotte Hornets"
- The Odds API: "Charlotte Hornets"
- BallDontLie: "Hornets"
- Built-in fuzzy matching handles most variations
- Check logs for "teams_match" debug messages

---

## Examples

### Example 1: Today's NBA Odds

```python
from datetime import date
from omega.odds_api_client import TheOddsAPIClient

client = TheOddsAPIClient()
today = date.today().strftime("%Y-%m-%d")

odds = client.get_historical_odds("NBA", today)

print(f"Found {len(odds)} games today")
for game in odds:
    home = game['home_team']
    away = game['away_team']
    spread = game['spread']
    
    print(f"\n{away} @ {home}")
    print(f"  Spread: {home} {spread['line']} ({spread['home_odds']})")
    print(f"  Total: {game['total']['line']}")
```

### Example 2: Historical Data with Stats

```python
from omega.espn_historical_scraper import ESPNHistoricalScraper  
from omega.balldontlie_client import BallDontLieClient

# Get ESPN games
espn = ESPNHistoricalScraper()
espn_games = espn.fetch_nba_games("2024-03-15", "2024-03-15")

# Get BallDontLie games
bdl = BallDontLieClient()
bdl_games = bdl.get_games("2024-03-15", "2024-03-15")

print(f"ESPN: {len(espn_games)} games")
print(f"BallDontLie: {len(bdl_games)} games")

# Match by teams and add stats
for espn_game in espn_games:
    for bdl_game in bdl_games:
        if (espn_game['home_team'] in bdl_game['home_team'] and
            espn_game['away_team'] in bdl_game['away_team']):
            
            stats = bdl.get_game_stats(bdl_game['id'])
            if stats:
                espn_game['detailed_stats'] = stats
                print(f"✓ Added stats for {espn_game['home_team']}")
```

### Example 3: Full Pipeline

```python
from core.data_pipeline import DataPipeline

# Initialize pipeline with enrichment enabled
pipeline = DataPipeline()

# Fetch and cache games with betting odds
games = pipeline.fetch_and_cache_games(
    sport="NBA",
    start_date="2024-03-15",
    end_date="2024-03-17",
    force_refresh=False,
    enrich_with_odds=True  # Enable enrichment
)

# Check results
games_with_odds = [g for g in games if (g.get('moneyline') or {}).get('home')]
print(f"Total games: {len(games)}")
print(f"Games with odds: {len(games_with_odds)}")
```

---

## Configuration

### Environment Variables (.env)

```bash
# The Odds API (Required)
THE_ODDS_API_KEY=f6e098cb773a5bc2972a55ac85bb01ef

# BallDontLie API (Required)  
BALLDONTLIE_API_KEY=d2e5f371-e817-4cac-8506-56c9df9d98b4

# Optional: Override base URLs
ODDS_API_BASE_URL=https://api.the-odds-api.com/v4
BALLDONTLIE_BASE_URL=https://api.balldontlie.io/v1
```

### Pipeline Configuration

```python
# In core/data_pipeline.py
pipeline = DataPipeline(
    cache_enabled=True,
    use_api_enrichment=True  # Enable betting odds enrichment
)
```

---

## API Documentation Links

- **The Odds API**: https://the-odds-api.com/liveapi/guides/v4/
- **BallDontLie API**: https://docs.balldontlie.io
- **ESPN API**: https://site.api.espn.com/apis/site/v2/sports/ (undocumented)

---

Last Updated: December 31, 2024
