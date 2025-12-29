# Module Execution Order for Perplexity Agent

**Last Updated:** December 29, 2025  
**Purpose:** Step-by-step guide for executing OmegaSports modules in correct order

---

## Overview

The OmegaSports engine follows a strict dependency chain. Modules must be imported and executed in the correct order to ensure data flows properly through the system.

```
Data Sources → Foundation → Analytics → Modeling → Simulation → Betting → Output
```

---

## Execution Workflow

### Stage 1: Environment Setup (Always First)

```python
import os
import sys
import logging

# Step 1.1: Verify Python version
assert sys.version_info >= (3, 10), "Python 3.10+ required"
print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}")

# Step 1.2: Create required directories
for directory in ["logs", "outputs", "data/logs", "data/outputs", "data/cache"]:
    os.makedirs(directory, exist_ok=True)
    print(f"✓ {directory}/ ready")

# Step 1.3: Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("omega")
print("✓ Logging configured")
```

---

### Stage 2: Foundation Modules (Load First)

These modules have no dependencies and provide core functionality.

```python
# Step 2.1: Load schema and data structures
from omega.schema import GameData, BettingLine, PropBet, DailySlate
print("✓ Schema loaded")

# Step 2.2: Load model configuration
from omega.foundation.model_config import (
    get_edge_thresholds,
    get_confidence_tier_caps,
    get_simulation_params
)
print("✓ Model config loaded")

# Step 2.3: Load league configuration  
from omega.foundation.league_config import get_league_config
print("✓ League config loaded")

# Step 2.4: Load core abstractions
from omega.foundation.core_abstractions import Team, Player, Game
print("✓ Core abstractions loaded")

# Verify foundation setup
edge_thresholds = get_edge_thresholds()
league_config = get_league_config("NBA")
print(f"✓ Edge thresholds: {edge_thresholds}")
print(f"✓ NBA config loaded: {league_config['name']}")
```

---

### Stage 3: Data Ingestion Modules

These modules fetch and prepare data for analysis.

#### Option A: Live Data (Requires Internet)

```python
# Step 3A.1: Import data modules
from omega.data.schedule_api import get_todays_games
from omega.data.stats_scraper import get_team_stats, get_player_stats
from omega.data.odds_scraper import get_upcoming_games
from omega.data.injury_api import get_injured_players
print("✓ Data modules loaded")

# Step 3A.2: Fetch today's games
try:
    games = get_todays_games("NBA")
    print(f"✓ Found {len(games)} games today")
except Exception as e:
    print(f"⚠ Could not fetch games: {e}")
    games = []

# Step 3A.3: Fetch team statistics
try:
    team_stats = get_team_stats("Boston Celtics", "NBA")
    print(f"✓ Team stats: {team_stats.get('off_rating', 'N/A')}")
except Exception as e:
    print(f"⚠ Could not fetch stats: {e}")
    team_stats = {"off_rating": 110.0, "def_rating": 110.0}
```

#### Option B: Manual Data (Sandbox Mode)

```python
# Step 3B.1: Import schema
from omega.schema import GameData, BettingLine
print("✓ Schema loaded for manual data")

# Step 3B.2: Construct game data manually
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
print(f"✓ Game data created: {game.home_team} vs {game.away_team}")

# Step 3B.3: Validate game data
from scraper_engine import validate_game_data
is_valid, result = validate_game_data(game.model_dump())
if is_valid:
    print("✓ Game data validated")
else:
    print(f"✗ Validation failed: {result}")
```

---

### Stage 4: Simulation Engine

Run Monte Carlo simulations to generate probabilities.

```python
# Step 4.1: Import simulation engine
from omega.simulation.simulation_engine import run_game_simulation, run_player_simulation
print("✓ Simulation engine loaded")

# Step 4.2: Prepare projection data
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
print("✓ Projection data prepared")

# Step 4.3: Run game simulation
sim_result = run_game_simulation(
    projection=projection,
    n_iter=10000,
    league="NBA"
)
print(f"✓ Simulation complete: {sim_result['home_win_prob']:.2%} home win probability")

# Step 4.4: Extract simulation results
# Note: The simulation returns team_a/team_b based on projection dict order
# The first team in the projection dict is team_a (Boston Celtics in this case)
home_win_prob = sim_result.get("true_prob_a", 0.5)  # Celtics (team_a)
away_win_prob = sim_result.get("true_prob_b", 0.5)  # Pacers (team_b)
predicted_spread = sim_result.get("predicted_spread", 0)
predicted_total = sim_result.get("predicted_total", 220)

print(f"  Home Win (Celtics): {home_win_prob:.2%}")
print(f"  Away Win (Pacers): {away_win_prob:.2%}")
print(f"  Spread: {predicted_spread:.1f}")
print(f"  Total: {predicted_total:.1f}")
```

---

### Stage 5: Betting Analysis

Calculate edges and evaluate bets.

```python
# Step 5.1: Import betting modules
from omega.betting.odds_eval import (
    implied_probability,
    edge_percentage,
    expected_value_percent
)
from omega.betting.kelly_staking import recommend_stake
print("✓ Betting modules loaded")

# Step 5.2: Calculate implied probability from odds
home_ml_odds = -150
home_implied_prob = implied_probability(home_ml_odds)
print(f"✓ Implied probability: {home_implied_prob:.2%}")

# Step 5.3: Calculate edge
edge = edge_percentage(
    model_prob=home_win_prob,
    implied_prob=home_implied_prob
)
print(f"✓ Edge: {edge:.2f}%")

# Step 5.4: Calculate expected value
ev = expected_value_percent(
    model_prob=home_win_prob,
    odds=home_ml_odds
)
print(f"✓ Expected Value: {ev:.2f}%")

# Step 5.5: Calculate Kelly stake (if edge > threshold)
edge_threshold = get_edge_thresholds()["moneyline"]  # e.g., 3%
if edge >= edge_threshold:
    kelly_stake = recommend_stake(
        prob=home_win_prob,
        odds=home_ml_odds,
        bankroll=1000  # Example bankroll
    )
    print(f"✓ Recommended stake: ${kelly_stake['amount']:.2f} ({kelly_stake['pct_bankroll']:.1f}%)")
else:
    print(f"⚠ Edge {edge:.2f}% below threshold {edge_threshold}% - bet declined")
```

---

### Stage 6: Output & Logging

Format and save results.

```python
# Step 6.1: Import output modules
from omega.utilities.output_formatter import format_full_output
from omega.utilities.data_logging import log_bet, log_simulation
print("✓ Output modules loaded")

# Step 6.2: Format bet recommendation
bet_recommendation = {
    "matchup": f"{game.away_team} @ {game.home_team}",
    "pick": f"{game.home_team} ML",
    "odds": home_ml_odds,
    "model_prob": home_win_prob,
    "implied_prob": home_implied_prob,
    "edge_pct": edge,
    "ev_pct": ev,
    "confidence_tier": "A" if edge >= 6 else ("B" if edge >= 3 else "C"),
    "recommended_units": kelly_stake.get("units", 0) if edge >= edge_threshold else 0
}
print("✓ Bet recommendation formatted")

# Step 6.3: Save to file
import json
from datetime import datetime

timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
output_path = f"outputs/bet_analysis_{timestamp}.json"

with open(output_path, "w") as f:
    json.dump({
        "game": game.model_dump(),
        "simulation": sim_result,
        "bet_analysis": bet_recommendation,
        "generated_at": datetime.now().isoformat()
    }, f, indent=2, default=str)

print(f"✓ Results saved to: {output_path}")

# Step 6.4: Log to bet tracking system (optional)
try:
    from omega.utilities.sandbox_persistence import OmegaCacheLogger
    cache_logger = OmegaCacheLogger()
    cache_logger.log_bet(bet_recommendation)
    print("✓ Bet logged to tracking system")
except Exception as e:
    print(f"⚠ Could not log bet: {e}")
```

---

### Stage 7: Complete Workflow Example

Full end-to-end execution in one script:

```python
def run_complete_analysis():
    """Complete analysis workflow from start to finish."""
    
    print("\n=== OmegaSports Analysis Workflow ===\n")
    
    # 1. Setup
    import os
    os.makedirs("outputs", exist_ok=True)
    print("✓ Environment ready\n")
    
    # 2. Load modules
    from omega.schema import GameData, BettingLine
    from omega.simulation.simulation_engine import run_game_simulation
    from omega.betting.odds_eval import edge_percentage, expected_value_percent
    from omega.foundation.model_config import get_edge_thresholds
    print("✓ Modules loaded\n")
    
    # 3. Define game
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
    print(f"✓ Game: {game.away_team} @ {game.home_team}\n")
    
    # 4. Run simulation
    projection = {
        "off_rating": {"Boston Celtics": 118.5, "Indiana Pacers": 115.2},
        "def_rating": {"Boston Celtics": 110.2, "Indiana Pacers": 112.5},
        "pace": {"Boston Celtics": 99.5, "Indiana Pacers": 101.3},
        "league": "NBA",
        "variance_scalar": 1.0
    }
    
    sim = run_game_simulation(projection, n_iter=10000, league="NBA")
    print(f"✓ Simulation: {sim['home_win_prob']:.2%} home win prob\n")
    
    # 5. Analyze bet
    from omega.betting.odds_eval import implied_probability
    home_odds = game.moneyline["home"].price
    implied_prob = implied_probability(home_odds)
    edge = edge_percentage(sim['home_win_prob'], implied_prob)
    ev = expected_value_percent(sim['home_win_prob'], home_odds)
    
    print(f"✓ Edge: {edge:.2f}%")
    print(f"✓ EV: {ev:.2f}%\n")
    
    # 6. Make recommendation
    threshold = get_edge_thresholds()["moneyline"]
    if edge >= threshold:
        print(f"✅ BET RECOMMENDATION: {game.home_team} ML @ {home_odds}")
        print(f"   Edge: {edge:.2f}% | EV: {ev:.2f}%")
    else:
        print(f"❌ NO BET: Edge {edge:.2f}% below {threshold}% threshold")
    
    print("\n=== Analysis Complete ===\n")

# Run the complete workflow
run_complete_analysis()
```

---

## Quick Reference: Import Order

```python
# 1. Foundation (no dependencies)
from omega.schema import GameData, BettingLine
from omega.foundation.model_config import get_edge_thresholds
from omega.foundation.league_config import get_league_config

# 2. Data (depends on foundation)
from omega.data.schedule_api import get_todays_games
from omega.data.stats_scraper import get_team_stats

# 3. Simulation (depends on foundation + data)
from omega.simulation.simulation_engine import run_game_simulation

# 4. Betting (depends on simulation)
from omega.betting.odds_eval import edge_percentage
from omega.betting.kelly_staking import recommend_stake

# 5. Utilities (depends on all above)
from omega.utilities.output_formatter import format_full_output
from omega.utilities.data_logging import log_bet
```

---

## Error Handling Best Practices

```python
def safe_module_import(module_path, name):
    """Safely import a module with error handling."""
    try:
        module = __import__(module_path, fromlist=[name])
        func = getattr(module, name)
        print(f"✓ Loaded: {module_path}.{name}")
        return func
    except ImportError as e:
        print(f"✗ Failed to import {module_path}.{name}: {e}")
        return None
    except AttributeError as e:
        print(f"✗ Function {name} not found in {module_path}: {e}")
        return None

# Example usage
run_game_simulation = safe_module_import(
    "omega.simulation.simulation_engine",
    "run_game_simulation"
)

if run_game_simulation:
    # Proceed with simulation
    pass
else:
    # Handle fallback or error
    print("Cannot proceed without simulation engine")
```

---

## Testing Module Loading

```python
def test_module_loading():
    """Test that all modules can be loaded in correct order."""
    
    test_results = []
    
    # Test 1: Foundation modules
    try:
        from omega.schema import GameData
        from omega.foundation.model_config import get_edge_thresholds
        test_results.append(("✓", "Foundation modules"))
    except Exception as e:
        test_results.append(("✗", f"Foundation modules: {e}"))
    
    # Test 2: Data modules
    try:
        from omega.data.schedule_api import get_todays_games
        test_results.append(("✓", "Data modules"))
    except Exception as e:
        test_results.append(("✗", f"Data modules: {e}"))
    
    # Test 3: Simulation modules
    try:
        from omega.simulation.simulation_engine import run_game_simulation
        test_results.append(("✓", "Simulation modules"))
    except Exception as e:
        test_results.append(("✗", f"Simulation modules: {e}"))
    
    # Test 4: Betting modules
    try:
        from omega.betting.odds_eval import edge_percentage
        test_results.append(("✓", "Betting modules"))
    except Exception as e:
        test_results.append(("✗", f"Betting modules: {e}"))
    
    # Test 5: Utility modules
    try:
        from omega.utilities.output_formatter import format_full_output
        test_results.append(("✓", "Utility modules"))
    except Exception as e:
        test_results.append(("✗", f"Utility modules: {e}"))
    
    # Print results
    print("\n=== Module Loading Test Results ===\n")
    for status, message in test_results:
        print(f"{status} {message}")
    
    failures = [r for r in test_results if r[0] == "✗"]
    if not failures:
        print("\n✓ All modules loaded successfully!")
        return True
    else:
        print(f"\n✗ {len(failures)} module(s) failed to load")
        return False

# Run test
test_module_loading()
```

---

## Next Steps

1. **Start Simple**: Use the Stage 7 complete workflow example
2. **Add Complexity**: Integrate live data sources as needed
3. **Handle Errors**: Use safe import patterns and fallbacks
4. **Save Results**: Always write outputs to files for tracking
5. **Review Logs**: Check `logs/omega_engine.log` for issues

For more details, see:
- [QUICKSTART.md](./QUICKSTART.md) - Quick examples
- [AGENT_INSTRUCTIONS.md](./AGENT_INSTRUCTIONS.md) - Complete API reference
- [README.md](./README.md) - Project overview
