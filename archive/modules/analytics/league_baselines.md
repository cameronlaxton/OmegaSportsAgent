# League-Specific Baselines Module

"""
Module Name: League-Specific Baselines
Version: 1.0.0
Description: League-specific analytical baselines: NBA Four Factors, NFL EPA interface, MLB Run Expectancy, NHL xG interface.
Functions:
    - dean_oliver_four_factors(team_stats: dict) -> dict
    - nfl_epa_interface(down: int, distance: float, yardline: float, clock: float, ...) -> float
    - mlb_run_expectancy(base_out_state: dict) -> float
    - nhl_xg_per_shot(shot_location: float, shot_type: str, ...) -> float
Usage Notes:
    - Four Factors: eFG%, TOV%, ORB%, FTR
    - EPA interface: function signatures with heuristic approximations (TODOs for real EPA)
    - RE table: hard-coded or simplified approximations (TODOs for regression-based)
    - xG interface: simple formula with placeholders (TODOs for real coefficients)
"""

```python
from __future__ import annotations
from typing import Dict, Any, Optional

# ============================================================================
# NBA: DEAN OLIVER FOUR FACTORS
# ============================================================================

def dean_oliver_four_factors(team_stats: Dict[str, float]) -> Dict[str, float]:
    """
    Calculates Dean Oliver's Four Factors for NBA team analysis.
    
    Four Factors:
    1. Effective Field Goal Percentage (eFG%)
    2. Turnover Percentage (TOV%)
    3. Offensive Rebound Percentage (ORB%)
    4. Free Throw Rate (FTR)
    
    Args:
        team_stats: Dict with keys:
            - "fgm": Field goals made
            - "fga": Field goal attempts
            - "fg3m": Three-pointers made
            - "fg3a": Three-pointers attempted
            - "tov": Turnovers
            - "orb": Offensive rebounds
            - "opp_drb": Opponent defensive rebounds
            - "ftm": Free throws made
            - "fta": Free throw attempts
    
    Returns:
        Dict with keys: "efg_pct", "tov_pct", "orb_pct", "ftr"
    """
    fgm = team_stats.get("fgm", 0.0)
    fga = team_stats.get("fga", 1.0)  # Avoid division by zero
    fg3m = team_stats.get("fg3m", 0.0)
    fg3a = team_stats.get("fg3a", 0.0)
    tov = team_stats.get("tov", 0.0)
    orb = team_stats.get("orb", 0.0)
    opp_drb = team_stats.get("opp_drb", 1.0)  # Avoid division by zero
    ftm = team_stats.get("ftm", 0.0)
    fta = team_stats.get("fta", 0.0)
    
    # 1. Effective Field Goal Percentage
    # eFG% = (FGM + 0.5 * 3PM) / FGA
    efg_pct = (fgm + 0.5 * fg3m) / fga if fga > 0 else 0.0
    
    # 2. Turnover Percentage
    # TOV% = TOV / (FGA + 0.44 * FTA + TOV)
    possessions = fga + 0.44 * fta + tov
    tov_pct = tov / possessions if possessions > 0 else 0.0
    
    # 3. Offensive Rebound Percentage
    # ORB% = ORB / (ORB + Opponent DRB)
    orb_pct = orb / (orb + opp_drb) if (orb + opp_drb) > 0 else 0.0
    
    # 4. Free Throw Rate
    # FTR = FTA / FGA
    ftr = fta / fga if fga > 0 else 0.0
    
    return {
        "efg_pct": efg_pct,
        "tov_pct": tov_pct,
        "orb_pct": orb_pct,
        "ftr": ftr
    }

# ============================================================================
# NFL: EXPECTED POINTS ADDED (EPA) INTERFACE
# ============================================================================

def nfl_epa_interface(
    down: int,
    distance: float,
    yardline: float,
    clock: float,
    score_diff: float = 0.0,
    timeout_remaining: int = 3,
    is_home: bool = False
) -> float:
    """
    Expected Points Added (EPA) interface for NFL.
    
    This is a simplified heuristic approximation. Real EPA requires:
    - Historical play-by-play data
    - Regression models trained on millions of plays
    - Context-specific adjustments
    
    TODO: Replace with regression-based EPA model when data is available.
    
    Args:
        down: Down number (1-4)
        distance: Yards to first down
        yardline: Yard line (0-100, where 0 is own goal, 100 is opponent goal)
        clock: Time remaining in seconds
        score_diff: Score differential (positive = leading, negative = trailing)
        timeout_remaining: Timeouts remaining
        is_home: Whether team is at home
    
    Returns:
        Expected points for this situation (heuristic approximation)
    """
    # Simplified heuristic EPA calculation
    # Real EPA would use a lookup table or regression model
    
    # Base expected points from field position
    # Approximate: closer to endzone = higher expected points
    base_ep = (yardline / 100.0) * 7.0  # Rough approximation: 0 yards = 0 EP, 100 yards = 7 EP
    
    # Down and distance adjustments
    if down == 1:
        down_mult = 1.0
    elif down == 2:
        down_mult = 0.9
    elif down == 3:
        down_mult = 0.7
    else:  # 4th down
        down_mult = 0.3
    
    # Distance penalty
    distance_penalty = max(0.0, (distance - 3.0) / 10.0)  # Penalty for long distances
    
    # Clock adjustment (less time = less expected points, especially if trailing)
    clock_mult = 1.0
    if clock < 120 and score_diff < 0:  # Less than 2 minutes, trailing
        clock_mult = 0.7
    
    # Home advantage
    home_bonus = 0.1 if is_home else 0.0
    
    ep = base_ep * down_mult * (1.0 - distance_penalty) * clock_mult + home_bonus
    
    # Cap at reasonable values
    return max(0.0, min(7.0, ep))

# ============================================================================
# MLB: RUN EXPECTANCY (RE) TABLE
# ============================================================================

# Simplified Run Expectancy table
# Real RE tables are derived from millions of historical plate appearances
# TODO: Replace with regression-based RE table when data is available

MLB_RE_TABLE = {
    # Format: (outs, bases): expected_runs
    # Bases: "000" = empty, "100" = first, "110" = first and second, etc.
    (0, "000"): 0.50,  # 0 outs, bases empty
    (0, "100"): 0.90,  # 0 outs, runner on first
    (0, "010"): 1.15,  # 0 outs, runner on second
    (0, "001"): 1.40,  # 0 outs, runner on third
    (0, "110"): 1.50,  # 0 outs, runners on first and second
    (0, "101"): 1.80,  # 0 outs, runners on first and third
    (0, "011"): 2.00,  # 0 outs, runners on second and third
    (0, "111"): 2.30,  # 0 outs, bases loaded
    
    (1, "000"): 0.27,  # 1 out, bases empty
    (1, "100"): 0.55,  # 1 out, runner on first
    (1, "010"): 0.70,  # 1 out, runner on second
    (1, "001"): 0.95,  # 1 out, runner on third
    (1, "110"): 0.95,  # 1 out, runners on first and second
    (1, "101"): 1.20,  # 1 out, runners on first and third
    (1, "011"): 1.40,  # 1 out, runners on second and third
    (1, "111"): 1.65,  # 1 out, bases loaded
    
    (2, "000"): 0.10,  # 2 outs, bases empty
    (2, "100"): 0.23,  # 2 outs, runner on first
    (2, "010"): 0.35,  # 2 outs, runner on second
    (2, "001"): 0.50,  # 2 outs, runner on third
    (2, "110"): 0.40,  # 2 outs, runners on first and second
    (2, "101"): 0.55,  # 2 outs, runners on first and third
    (2, "011"): 0.65,  # 2 outs, runners on second and third
    (2, "111"): 0.80,  # 2 outs, bases loaded
}

def mlb_run_expectancy(base_out_state: Dict[str, Any]) -> float:
    """
    Returns run expectancy for a given base-out state in MLB.
    
    This uses a simplified hard-coded RE table. Real RE tables:
    - Are derived from millions of historical plate appearances
    - Vary by park, pitcher quality, batter quality
    - Are updated regularly
    
    TODO: Replace with regression-based RE table when data is available.
    
    Args:
        base_out_state: Dict with keys:
            - "outs": int (0, 1, or 2)
            - "first": bool (runner on first)
            - "second": bool (runner on second)
            - "third": bool (runner on third)
    
    Returns:
        Expected runs from this state until end of inning
    """
    outs = base_out_state.get("outs", 0)
    first = base_out_state.get("first", False)
    second = base_out_state.get("second", False)
    third = base_out_state.get("third", False)
    
    # Convert to string format for lookup
    bases = ("1" if first else "0") + ("1" if second else "0") + ("1" if third else "0")
    
    key = (outs, bases)
    return MLB_RE_TABLE.get(key, 0.0)

# ============================================================================
# NHL: EXPECTED GOALS (xG) INTERFACE
# ============================================================================

def nhl_xg_per_shot(
    shot_location: float,
    shot_type: str,
    is_rebound: bool = False,
    is_rush: bool = False,
    angle: float = 0.0,
    distance: float = 0.0
) -> float:
    """
    Expected Goals (xG) per shot interface for NHL.
    
    This is a simplified heuristic approximation. Real xG requires:
    - Shot location data (x, y coordinates)
    - Shot type classification
    - Historical shot conversion rates by location/type
    - Regression models trained on thousands of shots
    
    TODO: Replace with regression-based xG model when data is available.
    
    Args:
        shot_location: Distance from goal in feet (0-89 feet, where 0 is goal line)
        shot_type: Type of shot ("wrist", "slap", "snap", "backhand", "tip", "deflected")
        is_rebound: Whether shot is a rebound
        is_rush: Whether shot is on a rush
        angle: Shot angle in degrees (0 = straight on, 90 = from side)
        distance: Distance from goal center in feet (alternative to shot_location)
    
    Returns:
        Expected goals for this shot (0.0 to 1.0)
    """
    # Use distance if provided, otherwise use shot_location
    dist = distance if distance > 0 else shot_location
    
    # Base xG from distance (closer = higher xG)
    # Simplified: exponential decay with distance
    base_xg = 0.3 * pow(0.95, dist)  # Rough approximation
    
    # Shot type multipliers
    shot_multipliers = {
        "wrist": 1.0,
        "slap": 0.9,
        "snap": 1.1,
        "backhand": 0.7,
        "tip": 1.2,
        "deflected": 1.1
    }
    shot_mult = shot_multipliers.get(shot_type.lower(), 1.0)
    
    # Rebound bonus (rebounds are more dangerous)
    rebound_mult = 1.3 if is_rebound else 1.0
    
    # Rush bonus (rush shots are more dangerous)
    rush_mult = 1.2 if is_rush else 1.0
    
    # Angle penalty (shots from wide angles are less dangerous)
    angle_penalty = 1.0 - (abs(angle) / 90.0) * 0.3  # Up to 30% penalty for wide angles
    
    xg = base_xg * shot_mult * rebound_mult * rush_mult * angle_penalty
    
    # Cap at reasonable values
    return max(0.0, min(1.0, xg))

```

