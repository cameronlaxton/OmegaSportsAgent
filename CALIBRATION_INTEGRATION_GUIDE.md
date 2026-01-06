# Continual Calibration Integration Guide

This guide shows how to integrate the new BetRecorder and CalibrationLoader modules into your betting workflows for Validation Lab interoperability.

## Overview

The continual calibration integration provides two key modules:

1. **BetRecorder** (`outputs/bet_recorder.py`) - Records daily bet recommendations to structured JSON files
2. **CalibrationLoader** (`config/calibration_loader.py`) - Loads league-specific calibration packs with probability transforms

These modules enable:
- Standardized bet output format for Validation Lab consumption
- Dynamic calibration parameter loading per league
- Probability adjustments (Platt scaling, shrinkage) before edge calculation
- Seamless coexistence with existing logging utilities

## Quick Start

### Recording Bets

```python
from outputs.bet_recorder import BetRecorder

# Record a bet recommendation
BetRecorder.record_bet(
    date="2026-01-05",
    league="NBA",
    bet_id="game123_ml_home",
    game_id="401234567",
    game_date="2026-01-05",
    market_type="moneyline",
    recommendation="HOME",
    edge=0.055,
    model_probability=0.625,
    market_probability=0.570,
    stake=10.0,
    odds=-150,
    calibration_version="nba_v1.0",
    confidence="medium"
)
```

Output: `outputs/recommendations_20260105.json`

### Loading Calibration

```python
from config.calibration_loader import CalibrationLoader

# Load NBA calibration pack
cal = CalibrationLoader("NBA")

# Get parameters
edge_threshold = cal.get_edge_threshold("moneyline")
kelly_fraction = cal.get_kelly_fraction()

# Apply probability transform
transform = cal.get_probability_transform("moneyline")
if transform:
    adjusted_prob = transform(raw_model_prob)
```

## Integration Examples

### Example 1: Integrate into Morning Workflow

Modify `omega/workflows/morning_bets.py` to use calibration and record bets:

```python
from outputs.bet_recorder import BetRecorder
from config.calibration_loader import CalibrationLoader

def evaluate_game(game: Dict[str, Any], league: str, n_iter: int = 10000) -> Dict[str, Any]:
    """
    Evaluate a single game for betting opportunities.
    Now uses CalibrationLoader for dynamic thresholds and transforms.
    """
    # Load calibration pack for this league
    cal = CalibrationLoader(league)
    calibration_version = cal.get_version()
    
    game_id = game.get("game_id", "unknown")
    home_team = game.get("home_team", {})
    away_team = game.get("away_team", {})
    
    # ... run simulation (existing code) ...
    sim_results = run_game_simulation(projection, n_iter=n_iter, league=league)
    
    home_win_prob = sim_results.get("true_prob_a", 0.5)
    away_win_prob = sim_results.get("true_prob_b", 0.5)
    
    # Apply probability transforms
    ml_transform = cal.get_probability_transform("moneyline")
    if ml_transform:
        home_win_prob = ml_transform(home_win_prob)
        away_win_prob = ml_transform(away_win_prob)
    
    qualified_bets = []
    date = datetime.now().strftime("%Y-%m-%d")
    
    # Evaluate home moneyline
    home_ml_odds = game.get("home_ml_odds", -110)
    if isinstance(home_ml_odds, (int, float)):
        market_prob = implied_probability(home_ml_odds)
        edge = home_win_prob - market_prob
        edge_threshold = cal.get_edge_threshold("moneyline")
        
        if edge >= edge_threshold:
            # Calculate stake using calibrated Kelly
            kelly_frac = cal.get_kelly_fraction()
            stake_info = recommend_stake(
                home_win_prob, 
                home_ml_odds, 
                bankroll=1000.0,
                confidence_tier="B"  # Or calculate from edge
            )
            
            # Record bet to Validation Lab format
            bet_id = f"{game_id}_ml_home"
            BetRecorder.record_bet(
                date=date,
                league=league,
                bet_id=bet_id,
                game_id=game_id,
                game_date=date,
                market_type="moneyline",
                recommendation="HOME",
                edge=edge,
                model_probability=home_win_prob,
                market_probability=market_prob,
                stake=stake_info["stake_amount"],
                odds=home_ml_odds,
                edge_threshold=edge_threshold,
                kelly_fraction=kelly_frac,
                confidence="medium",
                calibration_version=calibration_version,
                metadata={
                    "home_team": home_team_name,
                    "away_team": away_team_name
                }
            )
            
            qualified_bets.append({
                "bet_id": bet_id,
                "edge": edge,
                "stake": stake_info["stake_amount"],
                # ... other fields ...
            })
    
    # ... similar logic for away ML, spreads, totals ...
    
    return {
        "game_id": game_id,
        "qualified_bets": qualified_bets,
        "calibration_version": calibration_version
    }
```

### Example 2: Player Props with Markov Simulation

Integrate into `omega/api/markov_analysis.py`:

```python
from outputs.bet_recorder import BetRecorder
from config.calibration_loader import CalibrationLoader

def analyze_player_props(player_name: str, league: str, game_date: str):
    """
    Analyze player props using Markov chains with calibration.
    """
    cal = CalibrationLoader(league)
    
    # Run Markov simulation for player
    props = run_markov_player_simulation(player_name, league)
    
    for prop in props:
        prop_type = prop["prop_type"]  # e.g., "points", "rebounds"
        market_type = f"player_prop_{prop_type}"
        
        model_prob = prop["model_probability"]
        market_odds = prop["odds"]
        
        # Apply probability transform
        transform = cal.get_probability_transform(market_type)
        if transform:
            adjusted_prob = transform(model_prob)
        else:
            adjusted_prob = model_prob
        
        market_prob = implied_probability(market_odds)
        edge = adjusted_prob - market_prob
        edge_threshold = cal.get_edge_threshold(market_type)
        
        if edge >= edge_threshold:
            bet_id = f"{prop['game_id']}_prop_{player_name}_{prop_type}"
            
            BetRecorder.record_bet(
                date=game_date,
                league=league,
                bet_id=bet_id,
                game_id=prop["game_id"],
                game_date=game_date,
                market_type=market_type,
                recommendation="OVER" if prop["pick"] == "over" else "UNDER",
                edge=edge,
                model_probability=adjusted_prob,
                market_probability=market_prob,
                stake=5.0,  # Calculate from Kelly
                odds=market_odds,
                line=prop["line"],
                edge_threshold=edge_threshold,
                kelly_fraction=cal.get_kelly_fraction(),
                confidence="medium",
                player_name=player_name,
                prop_type=prop_type,
                calibration_version=cal.get_version()
            )
```

### Example 3: Batch Processing Today's Slate

```python
from outputs.bet_recorder import BetRecorder
from config.calibration_loader import CalibrationLoader
from omega.data.schedule_api import get_todays_games
from datetime import datetime

def process_daily_slate(leagues=["NBA", "NFL"]):
    """
    Process all games for specified leagues and record qualified bets.
    """
    date = datetime.now().strftime("%Y-%m-%d")
    
    for league in leagues:
        # Load calibration for this league
        cal = CalibrationLoader(league)
        print(f"Processing {league} with calibration {cal.get_version()}")
        
        # Get today's games
        games = get_todays_games(league)
        
        for game in games:
            # Analyze game and extract betting opportunities
            opportunities = analyze_game(game, league, cal)
            
            # Record all qualified bets
            for opp in opportunities:
                BetRecorder.record_bet(
                    date=date,
                    league=league,
                    **opp  # Spread all bet parameters
                )
        
        print(f"Completed {league}: {len(games)} games processed")
```

### Example 4: Retrieving Recorded Bets

```python
from outputs.bet_recorder import BetRecorder

# Get all bets for a date
date = "2026-01-05"
bets = BetRecorder.get_bets_for_date(date)
print(f"Found {len(bets)} bets for {date}")

# Get full file structure
full_data = BetRecorder.get_file_for_date(date)
if full_data:
    print(f"League: {full_data['league']}")
    print(f"Calibration: {full_data['calibration_version']}")
    print(f"Bets: {len(full_data['bets'])}")
```

## File Schema Reference

### Recommendations File Format

`outputs/recommendations_YYYYMMDD.json`:

```json
{
  "date": "2026-01-05",
  "league": "NBA",
  "calibration_version": "v1.0",
  "bets": [
    {
      "bet_id": "unique_bet_id",
      "game_id": "401234567",
      "game_date": "2026-01-05",
      "market_type": "moneyline",
      "recommendation": "HOME",
      "edge": 0.055,
      "model_probability": 0.625,
      "market_probability": 0.570,
      "stake": 10.0,
      "odds": -150,
      "line": null,
      "edge_threshold": 0.04,
      "kelly_fraction": 0.25,
      "confidence": "medium",
      "player_name": null,
      "prop_type": null,
      "metadata": {}
    }
  ]
}
```

### Field Descriptions

**File-level:**
- `date`: ISO date (YYYY-MM-DD) for this recommendations file
- `league`: League identifier (NBA, NFL, NCAAB, NCAAF)
- `calibration_version`: Version of calibration pack used
- `bets`: Array of bet entries

**Bet-level:**
- `bet_id`: Unique identifier for this bet (e.g., "game123_ml_home")
- `game_id`: ESPN/OddsAPI game identifier
- `game_date`: Game date in YYYY-MM-DD
- `market_type`: Market type (moneyline, spread, total, player_prop_points, etc.)
- `recommendation`: Bet side (HOME, AWAY, OVER, UNDER, etc.)
- `edge`: Edge percentage (model_probability - market_probability)
- `model_probability`: Model's calculated probability (0.0 to 1.0)
- `market_probability`: Market-implied probability (0.0 to 1.0)
- `stake`: Stake amount in units
- `odds`: American odds
- `line`: Line value for spread/total (null for moneyline)
- `edge_threshold`: Edge threshold applied (from calibration pack)
- `kelly_fraction`: Kelly fraction used for staking
- `confidence`: Confidence tier (high, medium, low)
- `player_name`: Player name for props (null for game markets)
- `prop_type`: Prop type descriptor (null for game markets)
- `metadata`: Additional metadata (dict)

## Calibration Pack Reference

### Directory Structure

```
config/calibration/
├── nba_latest.json
├── nfl_latest.json
├── ncaab_latest.json
└── ncaaf_latest.json
```

### Loading Calibration

```python
# Default: loads {league}_latest.json
cal = CalibrationLoader("NBA")

# Specific pack:
cal = CalibrationLoader("NBA", pack_name="nba_v1.2.json")

# Check if using defaults (pack not found)
if cal.is_using_defaults():
    print("Warning: Using fallback defaults")
```

### Accessing Parameters

```python
# Edge thresholds
edge_ml = cal.get_edge_threshold("moneyline")        # Default: 0.04
edge_spread = cal.get_edge_threshold("spread")       # Default: 0.04
edge_prop = cal.get_edge_threshold("player_prop_points")  # Default: 0.05

# Kelly parameters
kelly = cal.get_kelly_fraction()  # Default: 0.25
policy = cal.get_kelly_policy()   # Default: "quarter_kelly"

# Probability transforms
transform = cal.get_probability_transform("moneyline")
if transform:
    adjusted_prob = transform(0.65)  # Returns adjusted probability

# All transforms
all_transforms = cal.get_probability_transforms()
```

### Probability Transforms

**Shrinkage** (move toward 0.5):
```python
# Shrinks probability toward 0.5 by factor
# adjusted = 0.5 + (prob - 0.5) * factor
transform = cal.get_probability_transform("moneyline")
adjusted = transform(0.70)  # With factor=0.625: 0.70 → 0.625
```

**Platt Scaling** (logistic calibration):
```python
# Applies Platt scaling coefficients A and B
# adjusted = 1 / (1 + exp(-(A * logit(prob) + B)))
transform = cal.get_probability_transform("spread")
adjusted = transform(0.60)
```

## Validation Lab Integration

### Export Format

The BetRecorder automatically creates files in the Validation Lab format:

1. **Filename**: `outputs/recommendations_YYYYMMDD.json`
2. **One file per date**: All bets for a date in single file
3. **Append mode**: Multiple calls append to same file
4. **Schema compliance**: Matches Validation Lab requirements

### Workflow

```
1. Morning: Generate recommendations
   └─> BetRecorder creates recommendations_YYYYMMDD.json

2. During day: Track bet placements
   └─> Optional: Add result field to bet entries

3. Evening: Collect outcomes
   └─> Validation Lab ingests recommendations file
   └─> Matches outcomes to predictions

4. Weekly: Generate new calibration
   └─> Validation Lab produces updated calibration pack
   └─> Deploy to config/calibration/{league}_latest.json

5. Next cycle: Use updated calibration
   └─> CalibrationLoader automatically picks up latest pack
```

## Migration Guide

### From Existing Logging

If using `omega.utilities.data_logging`:

**Before:**
```python
from omega.utilities.data_logging import log_bet_recommendation

log_bet_recommendation(
    date="2026-01-05",
    bet_data={"game_id": "123", "pick": "HOME", ...}
)
```

**After (both work, choose based on need):**
```python
from outputs.bet_recorder import BetRecorder

# Validation Lab format (structured)
BetRecorder.record_bet(
    date="2026-01-05",
    league="NBA",
    bet_id="game123_ml_home",
    game_id="123",
    ...
)

# Original format still works
from omega.utilities.data_logging import log_bet_recommendation
log_bet_recommendation(...)  # Still functional
```

**Both systems coexist** - choose based on downstream consumer:
- Use BetRecorder for Validation Lab integration
- Keep data_logging for internal analysis/CSV export

### From Static Thresholds

If using `omega.foundation.model_config`:

**Before:**
```python
from omega.foundation.model_config import get_edge_thresholds

thresholds = get_edge_thresholds()
edge_threshold = thresholds["min_edge_pct"] / 100.0  # 3% → 0.03
```

**After:**
```python
from config.calibration_loader import CalibrationLoader

cal = CalibrationLoader("NBA")
edge_threshold = cal.get_edge_threshold("moneyline")  # Dynamic per league/market
```

**Benefits:**
- League-specific thresholds
- Market-type granularity
- Dynamic updates without code changes
- Probability transforms included

## Best Practices

### 1. Always Load Calibration Early

```python
def analyze_game(game, league):
    # Load once per league
    cal = CalibrationLoader(league)
    calibration_version = cal.get_version()
    
    # Use throughout analysis
    edge_threshold = cal.get_edge_threshold("moneyline")
    # ...
```

### 2. Apply Transforms Before Edge Calculation

```python
# CORRECT order:
model_prob = 0.65
transform = cal.get_probability_transform("moneyline")
if transform:
    model_prob = transform(model_prob)  # Apply BEFORE edge calc
market_prob = implied_probability(odds)
edge = model_prob - market_prob

# WRONG order:
# edge = model_prob - market_prob
# if transform:
#     edge = transform(edge)  # DON'T transform edge!
```

### 3. Include Calibration Version in Records

```python
BetRecorder.record_bet(
    # ...
    calibration_version=cal.get_version(),  # Track which calibration used
    # ...
)
```

### 4. Generate Unique Bet IDs

```python
# Pattern: {game_id}_{market}_{side}_{detail}
bet_id = f"{game_id}_ml_home"
bet_id = f"{game_id}_spread_away"
bet_id = f"{game_id}_total_over"
bet_id = f"{game_id}_prop_{player_name}_points_over"
```

### 5. Handle Missing Calibration Packs

```python
cal = CalibrationLoader("MLB")  # Pack might not exist

if cal.is_using_defaults():
    print(f"Warning: No calibration pack for MLB, using defaults")
    # Option 1: Continue with defaults
    # Option 2: Skip this league
    # Option 3: Use different league's pack as fallback
```

## Troubleshooting

### BetRecorder Issues

**Problem:** File not created
```python
# Check outputs directory exists
import os
os.makedirs("outputs", exist_ok=True)
```

**Problem:** Bets not appending
```python
# Ensure same date format
date = "2026-01-05"  # YYYY-MM-DD
# NOT: "01-05-2026" or "2026/01/05"
```

**Problem:** Edge validation fails
```python
# Ensure edge = model_prob - market_prob
# BetRecorder auto-corrects small differences (<0.001)
```

### CalibrationLoader Issues

**Problem:** Pack not loading
```python
cal = CalibrationLoader("NBA")
if cal.is_using_defaults():
    print("Pack not found - check filename and path")
    # Expected: config/calibration/nba_latest.json
```

**Problem:** Transform not working
```python
transform = cal.get_probability_transform("moneyline")
if transform is None:
    print("No transform defined for this market type")
else:
    result = transform(0.65)
    print(f"Transformed: {result}")
```

**Problem:** Wrong version loaded
```python
print(f"Loaded: {cal.pack_filepath}")
print(f"Version: {cal.get_version()}")
# Verify correct file is being read
```

## Testing

Run the integration test suite:

```bash
python test_calibration_integration.py
```

Expected output:
```
=== Test: BetRecorder ===
✓ Bet recorded to: outputs/recommendations_20260105.json
✓ File exists
✓ File content validated
✅ BetRecorder passed

=== Test: CalibrationLoader ===
✓ Loaded version: v1.0
✓ Using calibration pack: nba_latest.json
✅ CalibrationLoader passed

Test Results: 4 passed, 0 failed
✅ All tests passed!
```

## Support

For questions or issues:
1. Check this guide first
2. Review `config/calibration/README.md` for pack format details
3. Run `python test_calibration_integration.py` to diagnose issues
4. Check module docstrings for API details
