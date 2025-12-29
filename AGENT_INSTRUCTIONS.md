# OmegaSports Agent Instructions

This document explains how an external AI agent (such as Perplexity) can use this repository to fetch live sports data, run simulations, and generate betting recommendations.

## 🚀 QUICK START FOR PERPLEXITY

**New users:** Start with [QUICKSTART.md](./QUICKSTART.md) for sandbox-ready examples and step-by-step execution guide.

## Important: Sandbox Execution Mode

This engine is designed to run in **sandboxed environments** including:
- Perplexity AI Sandbox IDE
- Isolated Python environments
- Environments with limited/no internet access

### Sandbox Compatibility Features:
✅ **No external services required** - All core functionality works offline  
✅ **File-based outputs** - Results saved to local filesystem  
✅ **Manual data input** - Can operate without live data APIs  
✅ **Graceful degradation** - Handles missing data/network failures  
✅ **Pre-validated modules** - All imports tested and working  

### Prerequisites:
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Verify installation
python -c "from omega.workflows.morning_bets import run_morning_workflow; print('✓ Ready')"
```

## Repository Overview

OmegaSports is a **headless simulation engine** for sports analytics. It has no web interface - all operations are performed via Python scripts that output results as JSON or Markdown files.

### Key Entry Points

| File | Purpose |
|------|---------|
| `main.py` | Primary CLI entry point for all simulation tasks |
| `scraper_engine.py` | Web scraper for fetching live sports data |
| `omega/workflows/morning_bets.py` | Automated bet generation workflow |
| `omega/simulation/simulation_engine.py` | Core Monte Carlo simulation engine |

---

## Quick Start

### 1. Fetch Live Sports Data

Use `scraper_engine.py` to scrape sports websites and convert content to Markdown:

```python
from scraper_engine import fetch_sports_markdown

# Fetch ESPN NBA schedule
result = fetch_sports_markdown("https://www.espn.com/nba/schedule")

if result["success"]:
    markdown_content = result["markdown"]
    # Parse and use the data...
else:
    print(f"Error: {result['error']}")
```

**CLI Usage:**
```bash
python main.py --scrape "https://www.espn.com/nba/schedule"
```

### 2. Generate Morning Bet Recommendations

Run the full morning workflow to analyze all games and generate qualified bets:

```python
from omega.workflows.morning_bets import run_morning_workflow

result = run_morning_workflow(
    leagues=["NBA", "NFL"],  # Specify leagues
    n_iter=10000,            # Simulation iterations
    sync_to_github=False     # Don't sync (headless mode)
)

# Result contains:
# - qualified_bets: List of +EV bets
# - all_games: All analyzed games
# - output_file: Path to saved JSON
```

**CLI Usage:**
```bash
python main.py --morning-bets --leagues NBA NFL
```

### 3. Analyze a Specific Matchup

```python
from omega.simulation.simulation_engine import run_game_simulation
from omega.data.stats_scraper import get_team_stats

# Get team statistics
celtics_stats = get_team_stats("Boston Celtics", "NBA")
pacers_stats = get_team_stats("Indiana Pacers", "NBA")

# Build projection
projection = {
    "off_rating": {
        "Boston Celtics": celtics_stats.get("off_rating", 115.0),
        "Indiana Pacers": pacers_stats.get("off_rating", 112.0)
    },
    "league": "NBA",
    "variance_scalar": 1.0
}

# Run simulation
sim_results = run_game_simulation(projection, n_iter=10000, league="NBA")
# Returns: true_prob_a, true_prob_b (win probabilities for team_a and team_b)
# Note: team_a is the first team in the projection dict order
```

**CLI Usage:**
```bash
python main.py --analyze "Boston Celtics" "Indiana Pacers" --league NBA
```

### 4. Run Backtest Audit

Evaluate historical bet performance:

```bash
python main.py --audit --start-date 2025-01-01 --end-date 2025-01-15
```

---

## Directory Structure

```
OmegaSports/
├── main.py                    # CLI entry point
├── scraper_engine.py          # Web scraping with Crawl4AI
├── omega/                     # Core simulation modules
│   ├── simulation/            # Monte Carlo engines
│   ├── data/                  # Data ingestion & APIs
│   ├── betting/               # Odds evaluation & staking
│   ├── analytics/             # League baselines
│   ├── modeling/              # Probability calibration
│   ├── workflows/             # Automated workflows
│   └── utilities/             # Logging & persistence
├── logs/                      # Execution logs (auto-created)
├── outputs/                   # Simulation outputs (auto-created)
├── data/
│   ├── cache/                 # Cached API responses
│   ├── logs/                  # Bet & simulation logs
│   └── outputs/               # Historical picks
├── config/                    # Agent configuration
└── archive/                   # Documentation & module specs
```

---

## Output Locations

All simulation results are automatically saved:

| Output Type | Location | Format |
|-------------|----------|--------|
| Morning Bets | `outputs/morning_bets_*.json` | JSON |
| Game Analysis | `outputs/analysis_*.json` | JSON |
| League Simulations | `outputs/simulation_*.json` | JSON |
| Audit Reports | `outputs/audit_report_*.json` | JSON |
| Scrape Results | `outputs/scrape_result_*.json` | JSON |
| Execution Logs | `logs/omega_engine.log` | Text |

---

## Data Flow for Perplexity Agent

### Recommended Workflow

1. **Fetch Live Data**
   ```bash
   python main.py --scrape "https://www.espn.com/nba/schedule"
   ```
   Output: `outputs/scrape_result_*.json`

2. **Run Simulations**
   ```bash
   python main.py --morning-bets --leagues NBA
   ```
   Output: `outputs/morning_bets_*.json`

3. **Read Results**
   Parse the JSON output files to extract qualified bets, probabilities, and recommendations.

4. **Log Bets** (Optional)
   Bets are automatically logged to `data/logs/bet_log.json`

---

## Data Feeding Protocol (CRITICAL)

When scraping external data, you **MUST** follow this protocol to ensure data quality:

### 1. Schema Location
The universal data schema is defined in `omega/schema.py`. It uses Pydantic models:
- `GameData` - Primary game structure with betting lines
- `BettingLine` - Individual betting line from a sportsbook
- `PropBet` - Player prop bet structure
- `DailySlate` - Collection of games for a day

### 2. Extraction Rules
After scraping, you MUST map the raw text into the structure defined in `omega/schema.py`:

```python
from omega.schema import GameData, BettingLine, PropBet

game = GameData(
    sport="NBA",
    league="NBA",
    home_team="Boston Celtics",
    away_team="Indiana Pacers",
    moneyline={
        "home": BettingLine(sportsbook="DraftKings", price=-150),
        "away": BettingLine(sportsbook="DraftKings", price=130)
    },
    spread={
        "home": BettingLine(sportsbook="DraftKings", price=-110, value=-4.5),
        "away": BettingLine(sportsbook="DraftKings", price=-110, value=4.5)
    },
    total={
        "over": BettingLine(sportsbook="DraftKings", price=-110, value=220.5),
        "under": BettingLine(sportsbook="DraftKings", price=-110, value=220.5)
    },
    player_props=[
        PropBet(
            player_name="Jayson Tatum",
            team="Boston Celtics",
            prop_type="Points",
            line=28.5,
            over_price=-110,
            under_price=-110
        )
    ],
    raw_markdown_source=scraped_markdown[:5000]
)
```

### 3. Strictness Rules
- **Do NOT guess** betting lines. If a spread is missing from the scrape, set the value to `null`
- **Prop Handling**: Look specifically for player names, stat categories (Points, Rebounds, Assists, etc.), and associated Over/Under odds
- **Validation**: Use `validate_game_data()` from scraper_engine.py to verify data before simulation

### 4. Validation Helper
```python
from scraper_engine import fetch_sports_markdown, validate_game_data

# Fetch and validate
result = fetch_sports_markdown("https://espn.com/nba/game")
is_valid, validated = validate_game_data({
    "sport": "NBA",
    "league": "NBA",
    "home_team": "Celtics",
    "away_team": "Pacers",
    # ... fill in extracted data
})

if is_valid:
    # Proceed to simulation
    pass
```

### 5. Final Delivery
Format your final analysis as a JSON object matching the `GameData` class before running the Omega simulation. The simulation engine expects properly structured data

---

## Key Modules Reference

### Simulation Engine
- `omega.simulation.simulation_engine.run_game_simulation(projection, n_iter, league)`
- `omega.simulation.simulation_engine.run_player_simulation(player_data, n_iter)`
- `omega.simulation.correlated_simulation` - SGP-style correlated markets

### Data Ingestion
- `omega.data.schedule_api.get_todays_games(league)` - Today's schedule
- `omega.data.stats_scraper.get_team_stats(team_name, league)` - Team statistics
- `omega.data.odds_scraper.get_upcoming_games(league)` - Current odds
- `omega.data.injury_api.get_injured_players(team, league)` - Injury status

### Betting Logic
- `omega.betting.odds_eval.edge_percentage(model_prob, implied_prob)`
- `omega.betting.odds_eval.expected_value_percent(model_prob, odds)`
- `omega.betting.kelly_staking.recommend_stake(prob, odds, bankroll)`

---

## Supported Leagues

| League | Sports Type | Status |
|--------|-------------|--------|
| NBA | Basketball | Full Support |
| NFL | Football | Full Support |
| MLB | Baseball | Partial Support |
| NHL | Hockey | Partial Support |
| NCAAB | College Basketball | Full Support |
| NCAAF | College Football | Full Support |

---

## Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `PERPLEXITY_API_KEY` | Perplexity API for data enrichment | Optional |
| `BALLDONTLIE_API_KEY` | NBA statistics API | Optional |
| `THE_ODDS_API_KEY` | Odds API for market data | Optional |

---

## Troubleshooting

### Common Issues in Sandbox Environments

#### 1. Network/Internet Access Issues
```python
# Problem: Cannot connect to external APIs
# Solution: Use manual data entry or cached data

from scraper_engine import fetch_sports_markdown

result = fetch_sports_markdown("https://www.espn.com/nba/schedule")
if not result["success"]:
    print(f"Network unavailable: {result.get('error')}")
    print("Proceeding with manual game data...")
    # Use manual GameData construction instead
```

#### 2. Missing Data APIs
```python
# Problem: API returns None or empty data
# Solution: Use league defaults or manual input

from omega.data.stats_scraper import get_team_stats

stats = get_team_stats("Boston Celtics", "NBA")
if not stats:
    print("Using league defaults")
    stats = {
        "off_rating": 110.0,  # League average
        "def_rating": 110.0,
        "pace": 100.0
    }
```

#### 3. Module Import Errors
```python
# Problem: ImportError when loading modules
# Solution: Verify requirements.txt installed

try:
    from omega.workflows.morning_bets import run_morning_workflow
    print("✓ Module loaded successfully")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    print("Run: pip install -r requirements.txt")
    raise
```

#### 4. Directory Creation Failures
```python
# Problem: Permission errors or missing directories
# Solution: Ensure directories exist before operations

import os
for dir_path in ["logs", "outputs", "data/logs", "data/outputs"]:
    os.makedirs(dir_path, exist_ok=True)
    print(f"✓ Directory ready: {dir_path}")
```

#### 5. Playwright/Chromium Not Available
```bash
# Problem: Scraper cannot render JavaScript
# Solution: Install Playwright browsers or use fallback

pip install playwright
playwright install chromium

# Or use requests-only mode (no JS rendering)
# The scraper automatically falls back to requests
```

### Validation Checklist

Run this validation script to verify sandbox readiness:

```python
def validate_sandbox_environment():
    """Validate that the OmegaSports engine is ready to run."""
    import sys
    import os
    
    checks = []
    
    # Check Python version
    py_version = sys.version_info
    if py_version >= (3, 10):
        checks.append(("✓", f"Python {py_version.major}.{py_version.minor}"))
    else:
        checks.append(("✗", f"Python {py_version.major}.{py_version.minor} (need 3.10+)"))
    
    # Check directories
    for dir_path in ["logs", "outputs", "data/logs", "data/outputs"]:
        if os.path.exists(dir_path):
            checks.append(("✓", f"Directory: {dir_path}"))
        else:
            os.makedirs(dir_path, exist_ok=True)
            checks.append(("⚠", f"Created: {dir_path}"))
    
    # Check core imports
    core_modules = [
        "omega.schema",
        "omega.simulation.simulation_engine",
        "omega.workflows.morning_bets",
        "scraper_engine"
    ]
    
    for module in core_modules:
        try:
            __import__(module)
            checks.append(("✓", f"Module: {module}"))
        except ImportError as e:
            checks.append(("✗", f"Module: {module} - {e}"))
    
    # Print results
    print("\n=== OmegaSports Sandbox Validation ===\n")
    for status, message in checks:
        print(f"{status} {message}")
    
    # Summary
    failures = [c for c in checks if c[0] == "✗"]
    if not failures:
        print("\n✓ All checks passed - Ready to run!")
        return True
    else:
        print(f"\n✗ {len(failures)} check(s) failed - See errors above")
        return False

# Run validation
validate_sandbox_environment()
```

### Crawl4AI Not Working
```bash
pip install crawl4ai
playwright install
```

### Missing Dependencies
```bash
pip install -r requirements.txt
```

### No Games Found
- Check that the league has games scheduled for today
- Verify ESPN API is accessible
- Check `data/cache/` for cached responses
- Use manual GameData construction as fallback

### Output Files Not Created
- Verify write permissions for `outputs/` and `logs/` directories
- Check `logs/omega_engine.log` for error messages
- Ensure `os.makedirs()` calls succeed

---

## GitHub Integration

This repository is designed to sync with GitHub for Perplexity Spaces integration:

1. Results are saved to `outputs/` and `data/` directories
2. All Python modules are self-contained
3. No web server required - purely headless execution
4. Logs capture execution history for debugging

---

## Example: Full Analysis Session

```python
# 1. Import required modules
from omega.workflows.morning_bets import generate_daily_picks
from omega.utilities.output_formatter import format_full_output

# 2. Generate picks for NBA
picks = generate_daily_picks(leagues=["NBA"], n_iter=10000)

# 3. Get qualified bets
for bet in picks["qualified_bets"]:
    print(f"{bet['pick']} @ {bet['odds']}")
    print(f"  Edge: {bet['edge_pct']:.1f}%")
    print(f"  EV: {bet['ev_pct']:.1f}%")
    print(f"  Confidence: Tier {bet['confidence_tier']}")
    print()

# 4. Results automatically saved to outputs/
print(f"Full results: outputs/picks_{picks['date']}.json")
```

---

For detailed module documentation, see `archive/docs/ARCHITECTURE.md`.
