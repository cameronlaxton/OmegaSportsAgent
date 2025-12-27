# Projection Model Module

"""
Module Name: Projection Model
Version: 2.0.0
Description: Generates baseline strengths and context adjustments for both team-level and player-level projections.
Functions:
    - compute_baseline(matchup_data: dict, league: str) -> dict
    - compute_context(baseline: dict, context_modifiers: dict, league: str) -> dict
    - final_projection(injury_adjusted: dict, contextualized: dict, market_info: dict) -> dict
    - compute_player_baseline(player_data: dict, league: str) -> float
    - compute_player_context_multiplier(player_data: dict, context_modifiers: dict, league: str) -> float
    - compute_player_projections(players: list[dict], context_modifiers: dict, injury_adjusted_usage: dict, league: str) -> list[dict]
Usage Notes:
    - Always feed injury-adjusted metrics.
    - Provides per-league branches (NFL, NBA, MLB, NHL, fallback).
    - Team layer: compute_baseline → compute_context → final_projection
    - Player layer: compute_player_projections (uses compute_player_baseline and compute_player_context_multiplier internally)
"""

## Deep Analysis Model Weighting Logic (Reference)

The projection model follows a weighted average approach that combines baseline performance with context adjustments. This section documents the conceptual logic for weighting decisions.

### MODEL CONFIGURATION & WEIGHTS

The model uses a 60/40 split between baseline performance and context adjustments as a stable, well-tested starting point:

```python
MODEL_WEIGHTS = {
    'baseline_performance': 0.60,  # Based on player's/team's recent averages
    'context_adjustment': 0.40     # Based on opponent/game factors
}
```

### FEATURE ENGINEERING LOGIC

**Baseline Performance Calculation:**
- For player props: Use 10-game rolling average for the stat, adjusted for minutes/snap-share trends
  1. Find the player's last 10 game logs
  2. Extract the stat (e.g., 'pts', 'reb') and 'minutes' (or 'snap_share')
  3. Calculate the per-minute average of the stat
  4. Use the player's projected minutes for today's game
  5. Return: (per_minute_avg * projected_minutes) as the 'baseline_performance'
- For team projections: Use recent team efficiency metrics (off_rating, def_rating, pace, etc.)

**Context Adjustment Calculation:**
- Quantify the matchup and return a single multiplier
  1. Find the opponent's defensive rank vs. player position/team for the relevant stat
  2. Find the game pace factor (e.g., league average, +5% fast, -3% slow)
  3. Convert to numerical adjustment:
     - Start at 1.0 (no adjustment)
     - For each matchup rank from the median, apply a +/- 1% adjustment
       (e.g., Opponent is 30th vs. PGs = worst defense. Median is ~15. 
        (30 - 15) * 0.01 = +15% boost. Multiplier = 1.15)
     - Apply the pace adjustment (e.g., Game is 5% faster. Multiplier = 1.15 * 1.05)
     - Return the final multiplier (e.g., 1.2075)

### FINAL PROJECTION FORMULA

The final projection blends baseline and context-adjusted components:

```python
# The baseline's contribution (60% weight)
baseline_component = baseline_performance * 0.60

# The context-adjusted contribution (40% weight)
adjusted_performance = baseline_performance * context_multiplier
context_component = adjusted_performance * 0.40

# The final, blended projection
final_projection = baseline_component + context_component
```

This formula provides stability (from the baseline) while reacting to specific game context. The 60/40 weighting ensures recent form is prioritized while still incorporating matchup and situational factors.

```python
from __future__ import annotations
from typing import Dict, List

# Import model_config for blend weights and variance scalars
try:
    from model_config import get_blend_weights, get_variance_scalars
except ImportError:
    # Fallback if model_config not loaded
    def get_blend_weights():
        return {"baseline_weight": 0.60, "context_weight": 0.40}
    def get_variance_scalars(league: str, stat_key: str = "default") -> float:
        return 0.50

def compute_baseline(matchup_data: Dict, league: str) -> Dict:
    league = league.upper()
    baseline = {}
    if league == "NFL":
        pace = (matchup_data["team_a"]["plays_per_game"] + matchup_data["team_b"]["plays_per_game"]) / 2
        baseline["pace"] = pace
        baseline["off_rating"] = {
            "team_a": matchup_data["team_a"]["off_epa"],
            "team_b": matchup_data["team_b"]["off_epa"],
        }
        baseline["def_rating"] = {
            "team_a": matchup_data["team_a"]["def_epa"],
            "team_b": matchup_data["team_b"]["def_epa"],
        }
    elif league == "NBA":
        baseline["pace"] = (matchup_data["team_a"]["pace"] + matchup_data["team_b"]["pace"]) / 2
        baseline["off_rating"] = {team: data["off_rating"] for team, data in matchup_data.items()}
        baseline["def_rating"] = {team: data["def_rating"] for team, data in matchup_data.items()}
    elif league == "MLB":
        baseline["run_rate"] = {
            "team_a": matchup_data["team_a"]["runs_per_game"],
            "team_b": matchup_data["team_b"]["runs_per_game"],
        }
    elif league == "NHL":
        baseline["goal_rate"] = {
            "team_a": matchup_data["team_a"]["goals_per_game"],
            "team_b": matchup_data["team_b"]["goals_per_game"],
        }
    else:
        baseline["efficiency"] = {team: data.get("efficiency", 1.0) for team, data in matchup_data.items()}
    return baseline

def compute_context(baseline: Dict, context_modifiers: Dict[str, float], league: str) -> Dict:
    league = league.upper()
    contextualized = baseline.copy()
    if "pace" in contextualized:
        contextualized["pace"] *= context_modifiers.get("pace", 1.0)
    if league in {"NFL", "NBA"}:
        contextualized["off_rating"] = {
            team: rating * context_modifiers.get("efficiency", 1.0)
            for team, rating in baseline.get("off_rating", {}).items()
        }
        contextualized["def_rating"] = {
            team: rating / max(0.7, context_modifiers.get("efficiency", 1.0))
            for team, rating in baseline.get("def_rating", {}).items()
        }
    if league == "MLB":
        contextualized["run_rate"] = {
            team: max(0.4, rate * context_modifiers.get("efficiency", 1.0))
            for team, rate in baseline.get("run_rate", {}).items()
        }
    if league == "NHL":
        contextualized["goal_rate"] = {
            team: max(1.0, rate * context_modifiers.get("efficiency", 1.0))
            for team, rate in baseline.get("goal_rate", {}).items()
        }
    contextualized["variance_scalar"] = context_modifiers.get("scoring_variance", 1.0)
    return contextualized

def final_projection(injury_adjusted: Dict, contextualized: Dict, market_info: Dict) -> Dict:
    projection = {**contextualized}
    projection["injury_penalty"] = injury_adjusted.get("injury_penalty", 0.0)
    projection["market_line"] = market_info
    projection["true_strength"] = {}
    if "off_rating" in contextualized:
        for team in contextualized["off_rating"]:
            projection["true_strength"][team] = contextualized["off_rating"][team] - contextualized["def_rating"].get(team, 0)
    if "run_rate" in contextualized:
        projection["expected_total"] = sum(contextualized["run_rate"].values())
    elif "goal_rate" in contextualized:
        projection["expected_total"] = sum(contextualized["goal_rate"].values())
    else:
        projection["expected_total"] = None
    return projection

# ============================================================================
# PLAYER PROJECTION LAYER
# ============================================================================

def compute_player_baseline(player_data: Dict, league: str) -> float:
    """
    Computes baseline projection for a player stat.
    
    Args:
        player_data: Dict with keys:
            - "baseline_per_min": float (rolling per-minute average for the stat)
            - "proj_minutes": float (projected minutes for the game)
            - OR for NFL: "baseline_per_snap" and "proj_snaps"
        league: League identifier
    
    Returns:
        float: Baseline projection (baseline_per_min * proj_minutes)
    """
    league = league.upper()
    
    if league == "NFL":
        # NFL uses snap share instead of minutes
        baseline_per_snap = player_data.get("baseline_per_snap", 0.0)
        proj_snaps = player_data.get("proj_snaps", 0.0)
        return baseline_per_snap * proj_snaps
    else:
        # NBA and other leagues use minutes
        baseline_per_min = player_data.get("baseline_per_min", 0.0)
        proj_minutes = player_data.get("proj_minutes", 0.0)
        return baseline_per_min * proj_minutes

def compute_player_context_multiplier(player_data: Dict, context_modifiers: Dict[str, float], league: str) -> float:
    """
    Computes context multiplier for a player stat based on matchup and pace.
    
    Args:
        player_data: Dict with keys:
            - "matchup_multiplier": float (opponent defense adjustment, e.g., 1.15 for weak defense)
            - May also include position-specific matchup data
        context_modifiers: Dict from realtime_context.context_multipliers with keys:
            - "pace": float (pace multiplier, e.g., 1.05 for fast pace)
            - "efficiency": float (efficiency multiplier)
        league: League identifier
    
    Returns:
        float: Combined context multiplier
    """
    matchup_mult = player_data.get("matchup_multiplier", 1.0)
    pace_mult = context_modifiers.get("pace", 1.0)
    
    # Combine matchup and pace effects
    # For most stats, both matter; for some (like rebounds), pace matters more
    stat_key = player_data.get("stat_key", "default").lower()
    
    if stat_key in {"reb", "rebounds"}:
        # Rebounds are more pace-dependent
        context_mult = 0.3 * matchup_mult + 0.7 * pace_mult
    elif stat_key in {"ast", "assists"}:
        # Assists benefit from both pace and matchup
        context_mult = 0.5 * matchup_mult + 0.5 * pace_mult
    else:
        # Default: balanced between matchup and pace
        context_mult = 0.6 * matchup_mult + 0.4 * pace_mult
    
    return context_mult

def compute_player_projections(players: List[Dict], context_modifiers: Dict[str, float], injury_adjusted_usage: Dict[str, float], league: str) -> List[Dict]:
    """
    Computes full player projections with baseline, context, and variance.
    
    This is the main entry point for player-level projections. It:
    1. Computes baseline from per-minute/snap rates and projected playing time
    2. Applies context multipliers (matchup, pace)
    3. Blends baseline and context using configured weights
    4. Computes variance using league/stat-specific scalars
    5. Incorporates injury-adjusted usage rates
    
    Args:
        players: List of player dicts, each with keys:
            - "player_name": str
            - "team": str
            - "opp_team": str
            - "stat_key": str (e.g., "pts", "reb", "pass_yds")
            - "baseline_per_min": float (or "baseline_per_snap" for NFL)
            - "proj_minutes": float (or "proj_snaps" for NFL)
            - "matchup_multiplier": float
            - "usage_rate": float (baseline usage, will be adjusted by injury_adjusted_usage)
        context_modifiers: Dict from realtime_context.context_multipliers
        injury_adjusted_usage: Dict mapping player names to adjusted usage rates (from injury_adjustments)
        league: League identifier
    
    Returns:
        List[Dict]: List of player projection dicts, each with keys:
            - "league": str
            - "player_name": str
            - "team": str
            - "opp_team": str
            - "stat_key": str
            - "mean": float (final projected mean)
            - "variance": float (projected variance)
            - "baseline": float (baseline projection)
            - "context_multiplier": float
            - "usage_rate": float (injury-adjusted)
    """
    league = league.upper()
    blend_weights = get_blend_weights()
    baseline_weight = blend_weights["baseline_weight"]
    context_weight = blend_weights["context_weight"]
    
    projections = []
    
    for player in players:
        player_name = player.get("player_name", "")
        
        # Get injury-adjusted usage (default to original if not in injury dict)
        original_usage = player.get("usage_rate", 1.0)
        adjusted_usage = injury_adjusted_usage.get(player_name, original_usage)
        
        # Compute baseline
        baseline = compute_player_baseline(player, league)
        
        # Apply usage adjustment to baseline
        # Usage affects volume stats (points, shots, touches) more than efficiency stats
        stat_key = player.get("stat_key", "pts").lower()
        usage_sensitive_stats = {"pts", "fgm", "fga", "3pm", "3pa", "ftm", "fta", "ast", "touches", "pass_att", "rush_att", "targets"}
        if stat_key in usage_sensitive_stats:
            baseline = baseline * (adjusted_usage / max(0.1, original_usage))
        
        # Compute context multiplier
        context_mult = compute_player_context_multiplier(player, context_modifiers, league)
        
        # Blend baseline and context-adjusted projection
        # Formula: final = baseline * (baseline_weight + context_weight * context_mult)
        # This is equivalent to: baseline * baseline_weight + (baseline * context_mult) * context_weight
        player_mean = baseline * (baseline_weight + context_weight * context_mult)
        
        # Ensure non-negative
        player_mean = max(0.0, player_mean)
        
        # Compute variance using league/stat-specific scalar
        variance_scalar = get_variance_scalars(league, stat_key)
        variance = player_mean * variance_scalar
        
        # Build projection dict
        proj = {
            "league": league,
            "player_name": player_name,
            "team": player.get("team", ""),
            "opp_team": player.get("opp_team", ""),
            "stat_key": stat_key,
            "mean": player_mean,
            "variance": variance,
            "baseline": baseline,
            "context_multiplier": context_mult,
            "usage_rate": adjusted_usage,
        }
        
        projections.append(proj)
    
    return projections
```

