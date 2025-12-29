# OmegaSports Complete Guide

**Last Updated:** December 29, 2025  
**For:** Perplexity AI and External Agents

This comprehensive guide covers everything you need to use the OmegaSports engine: setup, data fetching, simulation, and analysis.

---

## Table of Contents

1. [Quick Setup](#quick-setup)
2. [Web Scraping for Live Data](#web-scraping-for-live-data)
3. [Running Simulations](#running-simulations)
4. [Betting Analysis](#betting-analysis)
5. [CLI Commands](#cli-commands)
6. [Module Reference](#module-reference)
7. [Troubleshooting](#troubleshooting)

---

## Quick Setup

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (for JavaScript-rendered scraping)
playwright install chromium
```

### Verify Installation

```bash
# Run test suite
python test_engine.py

# Expected output: ✅ All tests passed! Engine is ready for use.
```

### Run Example Workflow

```bash
# See complete workflow in action
python example_complete_workflow.py

# Generates analysis and saves to outputs/
```

---

## Web Scraping for Live Data

**PRIMARY DATA SOURCE:** Use `scraper_engine.py` to fetch live sports data from the internet.

### Basic Scraping

```python
from scraper_engine import fetch_sports_markdown

# Scrape ESPN NBA schedule with live data
result = fetch_sports_markdown("https://www.espn.com/nba/schedule")

if result["success"]:
    markdown_content = result["markdown"]
    print(f"✓ Fetched {len(markdown_content)} characters")
    print(f"Method: {result['method']}")  # playwright or requests
    
    # Parse the markdown to extract game data, odds, stats, etc.
    # (Perplexity should extract relevant data from markdown)
else:
    print(f"✗ Error: {result.get('error')}")
```

### Parse Scraped Data

```python
from scraper_engine import parse_to_game_data

# Create game data template from scraped content
template = parse_to_game_data(
    markdown=result['markdown'],
    sport="NBA",
    home_team="Boston Celtics",
    away_team="Indiana Pacers",
    source_url="https://www.espn.com/nba/schedule"
)

# Now fill in betting lines extracted from the markdown
```

### Validate Data

```python
from scraper_engine import validate_game_data

# Validate before simulation
is_valid, result = validate_game_data(template)

if is_valid:
    print("✓ Data validated - ready for simulation")
else:
    print(f"✗ Validation error: {result}")
```

### Scraper Features

- **JavaScript Rendering** - Uses Playwright for dynamic content
- **Automatic Fallback** - Falls back to requests for simple pages
- **Markdown Conversion** - Clean, parseable output
- **Error Handling** - Graceful handling of network failures

---

## Running Simulations

### Complete Analysis Example

```python
from omega.schema import GameData, BettingLine
from omega.simulation.simulation_engine import run_game_simulation
from omega.betting.odds_eval import edge_percentage, implied_probability

# 1. Create game data (from scraped data or manual entry)
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

# 2. Define team projections (from stats or analysis)
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

# 3. Run simulation (10,000 iterations)
sim = run_game_simulation(projection, n_iter=10000, league="NBA")

# 4. Calculate edge
home_prob = sim["true_prob_a"]  # Boston (first team in projection)
implied_prob = implied_probability(-150)
edge = edge_percentage(home_prob, implied_prob)

print(f"Home Win Probability: {home_prob:.2%}")
print(f"Implied Probability: {implied_prob:.2%}")
print(f"Edge: {edge:.2f}%")
```

### Automated Morning Workflow

```python
from omega.workflows.morning_bets import run_morning_workflow

# Generate picks for NBA games
result = run_morning_workflow(
    leagues=["NBA"],
    n_iter=10000,
    sync_to_github=False  # Disable GitHub sync
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

# Results saved to outputs/morning_bets_*.json
```

---

## Markov Play-by-Play Simulation

The Markov simulation engine models games at the **play-by-play level**, tracking individual player involvement and stat accumulation throughout the game. This is particularly powerful for **player props** where traditional Monte Carlo simulations may not capture the dynamics of possession-by-possession play.

### Key Features

- **Play-by-Play Modeling**: Simulates each possession/play with state transitions
- **Player Usage Tracking**: Models individual player involvement based on usage rates
- **Team Context Integration**: Adjusts probabilities based on offensive/defensive ratings and pace
- **Multi-Sport Support**: NBA, NFL, MLB, NHL with league-specific transitions
- **Statistical Accuracy**: Produces realistic stat distributions over 10,000+ iterations

### When to Use Markov vs Monte Carlo

**Use Markov Simulation for:**
- Player props (points, rebounds, assists, receiving yards, etc.)
- Games where play-by-play dynamics matter
- Understanding individual player involvement patterns
- Correlated player performances on the same team

**Use Monte Carlo for:**
- Game outcomes (moneyline, spread, total)
- Team-level analysis
- Faster computation when play-level detail isn't needed

### Analyze Player Prop with Markov

```python
from omega.api.markov_analysis import analyze_player_prop_markov

# Define player with usage rates and stats
player = {
    "name": "Jayson Tatum",
    "team": "Boston Celtics",
    "usage_rate": 0.32,  # 32% of possessions when on court
    "pts_mean": 27.5,
    "reb_mean": 8.2,
    "ast_mean": 4.8
}

# Define teammates (for realistic game flow)
teammates = [
    {"name": "Jaylen Brown", "team": "Boston Celtics", "usage_rate": 0.28, "pts_mean": 23.1},
    {"name": "Kristaps Porzingis", "team": "Boston Celtics", "usage_rate": 0.20, "pts_mean": 19.8}
]

# Define opponents
opponents = [
    {"name": "Tyrese Haliburton", "team": "Indiana Pacers", "usage_rate": 0.25, "pts_mean": 22.4},
    {"name": "Pascal Siakam", "team": "Indiana Pacers", "usage_rate": 0.23, "pts_mean": 20.8}
]

# Optional: Team context for more accurate simulation
home_context = {
    "name": "Boston Celtics",
    "off_rating": 118.5,
    "def_rating": 110.2,
    "pace": 99.5
}

away_context = {
    "name": "Indiana Pacers",
    "off_rating": 120.1,
    "def_rating": 112.5,
    "pace": 101.3
}

# Run Markov simulation
result = analyze_player_prop_markov(
    player=player,
    teammates=teammates,
    opponents=opponents,
    prop_type="pts",  # Points prop
    market_line=27.5,
    over_odds=-110,
    under_odds=-110,
    league="NBA",
    n_iter=10000,
    home_context=home_context,
    away_context=away_context
)

# Display results
print(f"Projected Mean: {result['projected_mean']:.2f}")
print(f"Over Probability: {result['over_prob']:.2%}")
print(f"Over Edge: {result['over_edge_pct']:.2f}%")
print(f"Recommendation: {result['recommended_bet'].upper()}")
print(f"Confidence: Tier {result['confidence_tier']}")
```

### Analyze Multiple Props

```python
from omega.api.markov_analysis import analyze_multiple_props

# Define multiple props to analyze
props = [
    {
        "player": {"name": "Jayson Tatum", "team": "Boston Celtics", "usage_rate": 0.32, "pts_mean": 27.5},
        "teammates": teammates,
        "opponents": opponents,
        "prop_type": "pts",
        "market_line": 27.5,
        "over_odds": -110,
        "under_odds": -110,
        "league": "NBA"
    },
    {
        "player": {"name": "Tyrese Haliburton", "team": "Indiana Pacers", "usage_rate": 0.25, "ast_mean": 10.8},
        "teammates": opponents,  # Swap for Pacers
        "opponents": teammates,
        "prop_type": "ast",
        "market_line": 10.5,
        "over_odds": -115,
        "under_odds": -105,
        "league": "NBA"
    }
]

# Analyze all props
results = analyze_multiple_props(
    props=props,
    league="NBA",
    n_iter=10000,
    min_edge=5.0
)

# Display qualified bets
print(f"Qualified Bets: {results['qualified_bets_count']}")
for bet in results['qualified_bets']:
    print(f"\n{bet['player_name']} {bet['prop_type'].upper()} {bet['recommended_bet'].upper()}")
    print(f"  Line: {bet['market_line']}")
    print(f"  Edge: {bet['best_edge_pct']:.2f}%")
    print(f"  Tier: {bet['confidence_tier']}")
```

### Markov Transition Probabilities

The engine uses league-specific transition matrices:

**NBA Transitions:**
- Two-point make: 35%
- Two-point miss: 20%
- Three-point make: 12%
- Three-point miss: 18%
- Free throws: 8%
- Turnover: 7%

These are **dynamically adjusted** based on team offensive/defensive ratings.

**NFL Transitions:**
- Pass: 58%
- Rush: 38%
- Sack: 4%

Each with sub-outcomes (complete, incomplete, yards gained, etc.)

### Example Workflow

See `example_markov_simulation.py` for a complete working example.

```bash
python example_markov_simulation.py
```

This demonstrates:
1. Setting up player and team data
2. Running Markov simulations
3. Analyzing results and edges
4. Making betting recommendations
5. Saving outputs

---

## Betting Analysis

### Calculate Edge

```python
from omega.betting.odds_eval import (
    implied_probability,
    edge_percentage,
    expected_value_percent
)

# Get model probability from simulation
model_prob = 0.62

# Calculate implied probability from odds
odds = -150
implied_prob = implied_probability(odds)

# Calculate edge
edge = edge_percentage(model_prob, implied_prob)
print(f"Edge: {edge:.2f}%")

# Calculate expected value
ev = expected_value_percent(model_prob, odds)
print(f"Expected Value: {ev:.2f}%")
```

### Kelly Staking

```python
from omega.betting.kelly_staking import recommend_stake
from omega.foundation.model_config import get_edge_thresholds

# Check if bet qualifies
threshold = get_edge_thresholds()["moneyline"]  # e.g., 3%

if edge >= threshold:
    # Calculate recommended stake
    stake = recommend_stake(
        prob=model_prob,
        odds=odds,
        bankroll=1000  # Your bankroll
    )
    
    print(f"✅ BET RECOMMENDED")
    print(f"Stake: ${stake['amount']:.2f}")
    print(f"Percentage: {stake['pct_bankroll']:.1f}% of bankroll")
else:
    print(f"❌ NO BET: Edge {edge:.2f}% below threshold {threshold}%")
```

---

## CLI Commands

### Generate Daily Bets

```bash
python main.py --morning-bets --leagues NBA NFL
```

Output: `outputs/morning_bets_*.json`

### Analyze Specific Matchup

```bash
python main.py --analyze "Boston Celtics" "Indiana Pacers" --league NBA
```

Output: `outputs/analysis_*.json`

### Simulate League Games

```bash
python main.py --simulate NBA --iterations 10000
```

Output: `outputs/simulation_*.json`

### Markov Player Props Analysis

```bash
python main.py --markov-props --league NBA --min-edge 5.0
```

Output: `outputs/markov_props_*.json`

Analyzes player props using play-by-play Markov simulation for detailed stat projections.

### Markov Game Simulation

```bash
python main.py --markov-game "Boston Celtics" "Indiana Pacers" --league NBA
```

Output: `outputs/markov_game_*.json`

Simulates game with Markov play-by-play chains, tracking individual player stats.

### Scrape Live Data

```bash
python main.py --scrape "https://www.espn.com/nba/schedule"
```

Output: `outputs/scrape_result_*.json`

### Run Backtest Audit

```bash
python main.py --audit --start-date 2025-01-01 --end-date 2025-01-15
```

Output: `outputs/audit_report_*.json`

### Run Tests

```bash
python test_engine.py
```

---

## Module Reference

### Core Modules

```python
# Foundation (load first)
from omega.schema import GameData, BettingLine, PropBet
from omega.foundation.model_config import get_edge_thresholds
from omega.foundation.league_config import get_league_config

# Data Ingestion
from omega.data.schedule_api import get_todays_games
from omega.data.stats_scraper import get_team_stats
from omega.data.odds_scraper import get_upcoming_games
from omega.data.injury_api import get_injured_players

# Simulation
from omega.simulation.simulation_engine import run_game_simulation
from omega.simulation.correlated_simulation import run_correlated_simulation
from omega.simulation.markov_engine import (
    MarkovSimulator,
    MarkovState,
    run_markov_player_prop_simulation
)

# Markov Analysis API
from omega.api.markov_analysis import (
    analyze_player_prop_markov,
    analyze_multiple_props,
    simulate_game_with_markov
)

# Betting Analysis
from omega.betting.odds_eval import edge_percentage, expected_value_percent
from omega.betting.kelly_staking import recommend_stake
from omega.betting.parlay_tools import calculate_parlay_odds

# Utilities
from omega.utilities.output_formatter import format_full_output
from omega.utilities.data_logging import log_bet
from omega.utilities.sandbox_persistence import OmegaCacheLogger

# Workflows
from omega.workflows.morning_bets import run_morning_workflow
```

### Data Schema

```python
from omega.schema import GameData, BettingLine, PropBet

# Create structured game data
game = GameData(
    sport="NBA",
    league="NBA",
    home_team="Boston Celtics",
    away_team="Indiana Pacers",
    moneyline={
        "home": BettingLine(sportsbook="DraftKings", price=-150),
        "away": BettingLine(sportsbook="DraftKings", price=130)
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
    ]
)
```

### Module Loading Order

```
1. Foundation (no dependencies)
   - omega.schema
   - omega.foundation.model_config
   - omega.foundation.league_config

2. Data (depends on foundation)
   - omega.data.*

3. Simulation (depends on foundation + data)
   - omega.simulation.*

4. Betting (depends on simulation)
   - omega.betting.*

5. Utilities (depends on all above)
   - omega.utilities.*
```

---

## Troubleshooting

### Installation Issues

```bash
# Problem: Module import fails
# Solution: Install dependencies
pip install -r requirements.txt

# Problem: Playwright not working
# Solution: Install browsers
playwright install chromium
```

### Network Errors

```python
from scraper_engine import fetch_sports_markdown

result = fetch_sports_markdown("https://www.espn.com/nba/schedule")

if not result["success"]:
    print(f"Network error: {result.get('error')}")
    print("Check internet connection or try alternative URL")
    # As last resort, use manual data entry
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

### Directory Creation

```python
import os

# Ensure directories exist
for directory in ["logs", "outputs", "data/logs", "data/outputs"]:
    os.makedirs(directory, exist_ok=True)
    print(f"✓ {directory}/ ready")
```

### Validation Checklist

```python
def validate_environment():
    """Validate OmegaSports environment."""
    import sys
    
    checks = []
    
    # Python version
    if sys.version_info >= (3, 10):
        checks.append("✓ Python 3.10+")
    else:
        checks.append("✗ Python version too old")
    
    # Core imports
    try:
        from omega.schema import GameData
        from omega.simulation.simulation_engine import run_game_simulation
        checks.append("✓ Core modules")
    except ImportError as e:
        checks.append(f"✗ Import failed: {e}")
    
    # Directories
    import os
    for d in ["logs", "outputs"]:
        if os.path.exists(d):
            checks.append(f"✓ {d}/")
        else:
            checks.append(f"✗ {d}/ missing")
    
    # Print results
    for check in checks:
        print(check)
    
    return all("✓" in c for c in checks)

validate_environment()
```

---

## Output Locations

| Output Type | Location | Format |
|-------------|----------|--------|
| Morning Bets | `outputs/morning_bets_*.json` | JSON |
| Game Analysis | `outputs/analysis_*.json` | JSON |
| League Simulations | `outputs/simulation_*.json` | JSON |
| Audit Reports | `outputs/audit_report_*.json` | JSON |
| Scrape Results | `outputs/scrape_result_*.json` | JSON |
| Execution Logs | `logs/omega_engine.log` | Text |

---

## Supported Leagues

| League | Sport | Status |
|--------|-------|--------|
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
| `PERPLEXITY_API_KEY` | Data enrichment | Optional |
| `BALLDONTLIE_API_KEY` | NBA statistics API | Optional |
| `THE_ODDS_API_KEY` | Odds API | Optional |

---

## Best Practices

### Data Collection

1. **Use scraper_engine.py** for live data from websites
2. **Validate data** with `scraper_engine.validate_game_data()` before simulation
3. **Parse carefully** - Extract odds, stats, and schedules accurately
4. **Handle errors** - Implement fallbacks for network failures

### Simulation

1. **Use 10,000 iterations** for accurate probabilities
2. **Provide complete projections** - Off rating, def rating, pace
3. **Check league config** - Each league has specific parameters
4. **Validate results** - Ensure probabilities make sense

### Betting Analysis

1. **Check edge thresholds** - Each bet type has minimum edge
2. **Use Kelly staking** - Proper bankroll management
3. **Consider confidence** - Tier A/B/C recommendations
4. **Track performance** - Log bets for analysis

### File Management

1. **Review outputs** - Check `outputs/` for results
2. **Monitor logs** - Check `logs/omega_engine.log` for errors
3. **Clean up** - Periodically archive old outputs
4. **Version control** - Don't commit `outputs/` or `logs/`

---

## Example: Complete Workflow

```python
# 1. Import modules
from scraper_engine import fetch_sports_markdown
from omega.schema import GameData, BettingLine
from omega.simulation.simulation_engine import run_game_simulation
from omega.betting.odds_eval import edge_percentage, implied_probability
from omega.foundation.model_config import get_edge_thresholds

# 2. Scrape live data
result = fetch_sports_markdown("https://www.espn.com/nba/schedule")
print(f"✓ Scraped {len(result['markdown'])} chars")

# 3. Parse data (extract from markdown)
game = GameData(
    sport="NBA",
    league="NBA",
    home_team="Boston Celtics",
    away_team="Indiana Pacers",
    moneyline={
        "home": BettingLine(sportsbook="DraftKings", price=-150),
        "away": BettingLine(sportsbook="DraftKings", price=130)
    }
)

# 4. Prepare projection
projection = {
    "off_rating": {"Boston Celtics": 118.5, "Indiana Pacers": 115.2},
    "def_rating": {"Boston Celtics": 110.2, "Indiana Pacers": 112.5},
    "pace": {"Boston Celtics": 99.5, "Indiana Pacers": 101.3},
    "league": "NBA",
    "variance_scalar": 1.0
}

# 5. Run simulation
sim = run_game_simulation(projection, n_iter=10000, league="NBA")
print(f"✓ Home win prob: {sim['true_prob_a']:.2%}")

# 6. Analyze bet
home_prob = sim["true_prob_a"]
implied_prob = implied_probability(-150)
edge = edge_percentage(home_prob, implied_prob)

# 7. Make recommendation
threshold = get_edge_thresholds()["moneyline"]
if edge >= threshold:
    print(f"✅ BET: Boston Celtics ML @ -150")
    print(f"Edge: {edge:.2f}%")
else:
    print(f"❌ NO BET: Edge {edge:.2f}% below threshold")
```

---

## Additional Resources

- **README.md** - Project overview and features
- **test_engine.py** - Test suite for validation
- **example_complete_workflow.py** - Working example
- **scraper_engine.py** - Web scraping implementation
- **main.py** - CLI entry point

---

**Ready to start?** Run `python test_engine.py` to verify your setup, then try `python example_complete_workflow.py` to see a complete analysis!
