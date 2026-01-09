"""
League-Specific Baselines Module

League-specific analytical baselines: NBA Four Factors, NFL EPA interface,
MLB Run Expectancy, NHL xG interface.
"""

from __future__ import annotations
from typing import Dict, Any, Optional


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
    fga = team_stats.get("fga", 1.0)
    fg3m = team_stats.get("fg3m", 0.0)
    fg3a = team_stats.get("fg3a", 0.0)
    tov = team_stats.get("tov", 0.0)
    orb = team_stats.get("orb", 0.0)
    opp_drb = team_stats.get("opp_drb", 1.0)
    ftm = team_stats.get("ftm", 0.0)
    fta = team_stats.get("fta", 0.0)
    
    efg_pct = (fgm + 0.5 * fg3m) / fga if fga > 0 else 0.0
    
    possessions = fga + 0.44 * fta + tov
    tov_pct = tov / possessions if possessions > 0 else 0.0
    
    orb_pct = orb / (orb + opp_drb) if (orb + opp_drb) > 0 else 0.0
    
    ftr = fta / fga if fga > 0 else 0.0
    
    return {
        "efg_pct": efg_pct,
        "tov_pct": tov_pct,
        "orb_pct": orb_pct,
        "ftr": ftr
    }


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
    base_ep = (yardline / 100.0) * 7.0
    
    if down == 1:
        down_mult = 1.0
    elif down == 2:
        down_mult = 0.9
    elif down == 3:
        down_mult = 0.7
    else:
        down_mult = 0.3
    
    distance_penalty = max(0.0, (distance - 3.0) / 10.0)
    
    clock_mult = 1.0
    if clock < 120 and score_diff < 0:
        clock_mult = 0.7
    
    home_bonus = 0.1 if is_home else 0.0
    
    ep = base_ep * down_mult * (1.0 - distance_penalty) * clock_mult + home_bonus
    
    return max(0.0, min(7.0, ep))


MLB_RE_TABLE: Dict[tuple, float] = {
    (0, "000"): 0.50,
    (0, "100"): 0.90,
    (0, "010"): 1.15,
    (0, "001"): 1.40,
    (0, "110"): 1.50,
    (0, "101"): 1.80,
    (0, "011"): 2.00,
    (0, "111"): 2.30,
    
    (1, "000"): 0.27,
    (1, "100"): 0.55,
    (1, "010"): 0.70,
    (1, "001"): 0.95,
    (1, "110"): 0.95,
    (1, "101"): 1.20,
    (1, "011"): 1.40,
    (1, "111"): 1.65,
    
    (2, "000"): 0.10,
    (2, "100"): 0.23,
    (2, "010"): 0.35,
    (2, "001"): 0.50,
    (2, "110"): 0.40,
    (2, "101"): 0.55,
    (2, "011"): 0.65,
    (2, "111"): 0.80,
}


def mlb_run_expectancy(base_out_state: Dict[str, Any]) -> float:
    """
    Returns run expectancy for a given base-out state in MLB.
    
    This uses a simplified hard-coded RE table. Real RE tables:
    - Are derived from millions of historical plate appearances
    - Vary by park, pitcher quality, batter quality
    - Are updated regularly
    
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
    
    bases = ("1" if first else "0") + ("1" if second else "0") + ("1" if third else "0")
    
    key = (outs, bases)
    return MLB_RE_TABLE.get(key, 0.0)


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
    dist = distance if distance > 0 else shot_location
    
    base_xg = 0.3 * pow(0.95, dist)
    
    shot_multipliers = {
        "wrist": 1.0,
        "slap": 0.9,
        "snap": 1.1,
        "backhand": 0.7,
        "tip": 1.2,
        "deflected": 1.1
    }
    shot_mult = shot_multipliers.get(shot_type.lower(), 1.0)
    
    rebound_mult = 1.3 if is_rebound else 1.0
    
    rush_mult = 1.15 if is_rush else 1.0
    
    angle_penalty = 1.0 - (abs(angle) / 180.0) * 0.5
    
    xg = base_xg * shot_mult * rebound_mult * rush_mult * angle_penalty
    
    return max(0.0, min(1.0, xg))
