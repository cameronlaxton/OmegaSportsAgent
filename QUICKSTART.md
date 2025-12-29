# OmegaSports Quick Start for Perplexity Agent

**Last Updated:** December 29, 2025  
**Target:** Perplexity AI Sandbox IDE Mode

This guide provides step-by-step instructions for Perplexity AI to execute the OmegaSports engine in a sandbox environment.

---

## Prerequisites Verification

Before running any analysis, verify that the environment is set up:

```python
# Step 1: Verify Python version
import sys
print(f"Python version: {sys.version}")
# Required: Python 3.10+

# Step 2: Install dependencies
# Run in terminal/bash:
# pip install -r requirements.txt
# playwright install chromium  # Only if scraping with JavaScript rendering

# Step 3: Verify core imports
import omega.schema
from omega.workflows.morning_bets import run_morning_workflow
from omega.simulation.simulation_engine import run_game_simulation
from scraper_engine import fetch_sports_markdown
print("✓ All core modules imported successfully")
```

---

## Quick Start Workflow (No Internet Required)

If running in a sandboxed environment **without internet access**, you can still use the engine with manually provided data.

### Option 1: Use Pre-Structured Game Data

```python
from omega.schema import GameData, BettingLine
from omega.simulation.simulation_engine import run_game_simulation

# Define a game with betting lines
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
    }
)

# Build projection data (can be derived from stats or provided)
projection = {
    "off_rating": {
        "Boston Celtics": 118.5,  # Offensive rating
        "Indiana Pacers": 115.2
    },
    "def_rating": {
        "Boston Celtics": 110.2,  # Defensive rating
        "Indiana Pacers": 112.5
    },
    "pace": {
        "Boston Celtics": 99.5,   # Possessions per game
        "Indiana Pacers": 101.3
    },
    "league": "NBA",
    "variance_scalar": 1.0
}

# Run simulation
result = run_game_simulation(
    projection=projection,
    n_iter=10000,
    league="NBA"
)

print("Simulation Results:")
print(f"Team A (first team) Win Prob: {result['true_prob_a']:.2%}")
print(f"Team B (second team) Win Prob: {result['true_prob_b']:.2%}")
# Note: The simulation engine returns team_a/team_b based on projection dict order
# Team A is typically the first team in your projection dict
```

### Option 2: Generate Daily Bets (Requires Data APIs)

```python
from omega.workflows.morning_bets import run_morning_workflow
import json

# Generate morning bets for NBA games
result = run_morning_workflow(
    leagues=["NBA"],
    n_iter=10000,
    sync_to_github=False  # Disable GitHub sync in sandbox
)

# Display qualified bets
if result.get("qualified_bets"):
    print(f"Found {len(result['qualified_bets'])} qualified bets:")
    for bet in result['qualified_bets']:
        print(f"\n{bet['pick']}")
        print(f"  Odds: {bet['odds']}")
        print(f"  Edge: {bet['edge_pct']:.1f}%")
        print(f"  EV: {bet['ev_pct']:.1f}%")
        print(f"  Confidence: {bet['confidence_tier']}")
else:
    print("No qualified bets found today")

# Results are automatically saved to outputs/morning_bets_*.json
print(f"\nResults saved to: {result.get('output_file')}")
```

---

## Web Scraping (With Internet Access)

If the sandbox environment has internet access:

```python
from scraper_engine import fetch_sports_markdown, parse_to_game_data

# Scrape ESPN NBA schedule
url = "https://www.espn.com/nba/schedule"
result = fetch_sports_markdown(url)

if result["success"]:
    print(f"✓ Scraped {len(result['markdown'])} characters")
    print(f"Method: {result.get('method')}")  # playwright or requests
    print(f"\nFirst 500 characters:\n{result['markdown'][:500]}")
    
    # Parse to game data template
    template = parse_to_game_data(
        markdown=result['markdown'],
        sport="NBA",
        home_team="Boston Celtics",
        away_team="Indiana Pacers",
        source_url=url
    )
    
    print("\n✓ Game data template created")
    print("Note: Fill in betting lines before simulation")
else:
    print(f"✗ Scraping failed: {result.get('error')}")
```

---

## Module Loading Order

The OmegaSports engine follows a strict module dependency chain:

```
1. Foundation Modules (Load First)
   - omega.foundation.model_config      ← Configuration and thresholds
   - omega.foundation.league_config     ← League-specific parameters
   - omega.foundation.core_abstractions ← Core data structures

2. Data Modules
   - omega.data.schedule_api            ← Game schedules
   - omega.data.stats_scraper           ← Team/player statistics
   - omega.data.odds_scraper            ← Betting odds
   - omega.data.injury_api              ← Injury reports

3. Simulation Modules
   - omega.simulation.simulation_engine ← Monte Carlo engine
   - omega.simulation.correlated_simulation ← SGP support

4. Betting Modules
   - omega.betting.odds_eval            ← Edge calculation
   - omega.betting.kelly_staking        ← Stake recommendations
   - omega.betting.parlay_tools         ← Parlay evaluation

5. Utilities
   - omega.utilities.output_formatter   ← Output formatting
   - omega.utilities.data_logging       ← Logging
   - omega.utilities.sandbox_persistence ← Bet tracking
```

### Import Validation Script

```python
# Test all module imports
def validate_modules():
    """Validate that all required modules can be imported."""
    modules = {
        "Foundation": [
            "omega.foundation.model_config",
            "omega.foundation.league_config",
            "omega.foundation.core_abstractions"
        ],
        "Data": [
            "omega.data.schedule_api",
            "omega.data.stats_scraper",
            "omega.data.odds_scraper",
            "omega.data.injury_api"
        ],
        "Simulation": [
            "omega.simulation.simulation_engine",
            "omega.simulation.correlated_simulation"
        ],
        "Betting": [
            "omega.betting.odds_eval",
            "omega.betting.kelly_staking",
            "omega.betting.parlay_tools"
        ],
        "Utilities": [
            "omega.utilities.output_formatter",
            "omega.utilities.data_logging",
            "omega.utilities.sandbox_persistence"
        ]
    }
    
    results = {}
    for category, module_list in modules.items():
        results[category] = []
        for module in module_list:
            try:
                __import__(module)
                results[category].append(f"✓ {module}")
            except ImportError as e:
                results[category].append(f"✗ {module}: {e}")
    
    return results

# Run validation
validation = validate_modules()
for category, status_list in validation.items():
    print(f"\n{category}:")
    for status in status_list:
        print(f"  {status}")
```

---

## CLI Usage Examples

All operations can be executed via command line:

### 1. Generate Morning Bets
```bash
python main.py --morning-bets --leagues NBA NFL
```

### 2. Analyze a Specific Matchup
```bash
python main.py --analyze "Boston Celtics" "Indiana Pacers" --league NBA
```

### 3. Simulate All Games in a League
```bash
python main.py --simulate NBA --iterations 10000
```

### 4. Run Backtest Audit
```bash
python main.py --audit --start-date 2025-01-01 --end-date 2025-01-15
```

### 5. Scrape Sports Data
```bash
python main.py --scrape "https://www.espn.com/nba/schedule"
```

---

## Output Locations

All results are saved to the file system:

| Output Type | Location | Format |
|-------------|----------|--------|
| Morning Bets | `outputs/morning_bets_*.json` | JSON |
| Game Analysis | `outputs/analysis_*.json` | JSON |
| Simulations | `outputs/simulation_*.json` | JSON |
| Audit Reports | `outputs/audit_report_*.json` | JSON |
| Scrape Results | `outputs/scrape_result_*.json` | JSON |
| Logs | `logs/omega_engine.log` | Text |

---

## Error Handling

### Network Errors (No Internet)
```python
from scraper_engine import fetch_sports_markdown

result = fetch_sports_markdown("https://www.espn.com/nba/schedule")

if not result["success"]:
    print(f"Network error: {result.get('error')}")
    print("Solution: Use manual game data or wait for internet access")
    # Proceed with manual data entry
```

### Missing Data
```python
from omega.data.stats_scraper import get_team_stats

stats = get_team_stats("Boston Celtics", "NBA")

if not stats:
    print("Stats not available - using league defaults")
    stats = {
        "off_rating": 110.0,
        "def_rating": 110.0,
        "pace": 100.0
    }
```

### Module Import Errors
```python
try:
    from omega.workflows.morning_bets import run_morning_workflow
except ImportError as e:
    print(f"Module import failed: {e}")
    print("Solution: Verify requirements.txt installed")
    print("Run: pip install -r requirements.txt")
```

---

## Data Schema Reference

All game data must conform to the `omega.schema.GameData` structure:

```python
from omega.schema import GameData, BettingLine, PropBet

# Complete game data example
game = GameData(
    sport="NBA",
    league="NBA",
    game_id="401585001",  # Optional
    home_team="Boston Celtics",
    away_team="Indiana Pacers",
    
    # Moneyline
    moneyline={
        "home": BettingLine(sportsbook="DraftKings", price=-150),
        "away": BettingLine(sportsbook="DraftKings", price=130)
    },
    
    # Spread
    spread={
        "home": BettingLine(sportsbook="DraftKings", price=-110, value=-4.5),
        "away": BettingLine(sportsbook="DraftKings", price=-110, value=4.5)
    },
    
    # Total
    total={
        "over": BettingLine(sportsbook="DraftKings", price=-110, value=220.5),
        "under": BettingLine(sportsbook="DraftKings", price=-110, value=220.5)
    },
    
    # Player Props (optional)
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
    
    # Source tracking (optional)
    source_url="https://www.espn.com/nba/game",
    raw_markdown_source="..." # First 5000 chars of source
)

# Validate the game data
from scraper_engine import validate_game_data
is_valid, result = validate_game_data(game.model_dump())

if is_valid:
    print("✓ Game data is valid")
else:
    print(f"✗ Validation error: {result}")
```

---

## Troubleshooting Checklist

- [ ] Python 3.10+ installed?
- [ ] Dependencies installed? (`pip install -r requirements.txt`)
- [ ] Directories created? (logs/, outputs/, data/logs/, data/outputs/)
- [ ] All omega modules importable?
- [ ] Scraper engine tested?
- [ ] Schema validation working?

---

## Next Steps

1. **Read Full Documentation**: See [AGENT_INSTRUCTIONS.md](./AGENT_INSTRUCTIONS.md) for comprehensive guide
2. **Understand Architecture**: Review [archive/docs/ARCHITECTURE.md](./archive/docs/ARCHITECTURE.md)
3. **Check Module Load Order**: See [archive/MODULE_LOAD_ORDER.md](./archive/MODULE_LOAD_ORDER.md)
4. **Configuration Details**: Review [config/CombinedInstructions.md](./config/CombinedInstructions.md)

---

## Support & Debugging

If encountering issues:

1. Check `logs/omega_engine.log` for error messages
2. Verify all modules are importable using the validation script above
3. Test with a simple simulation example (Option 1 in Quick Start)
4. Review error messages for missing dependencies or data

**Remember:** The engine is designed to work in sandboxed environments. Most features work without internet access when provided with manual game data.
