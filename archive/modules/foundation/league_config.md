# League Configuration Module

"""
Module Name: League Configuration
Version: 1.0.0
Description: Centralized league-specific configuration parameters (periods, clock rules, scoring rules, typical possession counts, etc.).
Functions:
    - get_league_config(league: str) -> dict
    - get_periods(league: str) -> int
    - get_period_length(league: str) -> float
    - get_typical_possessions(league: str) -> float
    - get_scoring_rules(league: str) -> dict
    - get_clock_rules(league: str) -> dict
Usage Notes:
    - Same simulation engine can swap league-specific configs
    - All parameters are documented with defaults
    - Used by simulation and projection modules
"""

```python
from __future__ import annotations
from typing import Dict, Any

# League configuration data
LEAGUE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "NBA": {
        "periods": 4,
        "period_length_minutes": 12.0,
        "overtime_length_minutes": 5.0,
        "typical_possessions_per_game": 100.0,
        "typical_seconds_per_possession": 14.0,
        "scoring": {
            "field_goal": 2,
            "three_pointer": 3,
            "free_throw": 1,
            "typical_points_per_possession": 1.1
        },
        "clock_rules": {
            "shot_clock_seconds": 24.0,
            "game_clock_stops": True,
            "overtime_rules": "5_min_periods"
        },
        "key_numbers": [3, 4, 7],  # Common margins
        "home_advantage_points": 2.5
    },
    "NFL": {
        "periods": 4,
        "period_length_minutes": 15.0,
        "overtime_length_minutes": 10.0,  # Regular season
        "typical_drives_per_game": 12.0,  # Per team
        "typical_plays_per_drive": 6.0,
        "typical_seconds_per_play": 30.0,
        "scoring": {
            "touchdown": 6,
            "field_goal": 3,
            "safety": 2,
            "two_point_conversion": 2,
            "extra_point": 1,
            "typical_points_per_drive": 2.0
        },
        "clock_rules": {
            "play_clock_seconds": 40.0,
            "game_clock_stops": True,  # On incomplete passes, out of bounds, etc.
            "two_minute_warning": True,
            "overtime_rules": "sudden_death"
        },
        "key_numbers": [3, 4, 6, 7, 10, 14],  # Common margins
        "home_advantage_points": 2.0
    },
    "MLB": {
        "periods": 9,  # Innings
        "period_length_outs": 3,  # Outs per half-inning
        "overtime_innings": True,  # Extra innings
        "typical_innings_per_game": 9.0,
        "typical_plate_appearances_per_inning": 4.0,
        "scoring": {
            "run": 1,
            "typical_runs_per_inning": 0.5
        },
        "clock_rules": {
            "no_clock": True,
            "pitch_clock_seconds": 15.0,  # Modern rule
            "inning_ends": "three_outs"
        },
        "key_numbers": [1, 2, 3, 4, 5],  # Common margins
        "home_advantage_runs": 0.2
    },
    "NHL": {
        "periods": 3,
        "period_length_minutes": 20.0,
        "overtime_length_minutes": 5.0,
        "typical_shifts_per_game": 50.0,  # Per team
        "typical_shots_per_game": 30.0,  # Per team
        "typical_seconds_per_shift": 45.0,
        "scoring": {
            "goal": 1,
            "typical_goals_per_game": 3.0  # Per team
        },
        "clock_rules": {
            "game_clock_runs": True,
            "stops_on_whistle": True,
            "overtime_rules": "3v3_then_shootout"
        },
        "key_numbers": [1, 2, 3],  # Common margins
        "home_advantage_goals": 0.15
    },
    "NCAAF": {
        "periods": 4,
        "period_length_minutes": 15.0,
        "overtime_length_minutes": 0.0,  # Overtime rules differ
        "typical_drives_per_game": 12.0,  # Per team
        "typical_plays_per_drive": 6.0,
        "typical_seconds_per_play": 25.0,  # Faster than NFL
        "scoring": {
            "touchdown": 6,
            "field_goal": 3,
            "safety": 2,
            "two_point_conversion": 2,
            "extra_point": 1,
            "typical_points_per_drive": 2.5  # Higher than NFL
        },
        "clock_rules": {
            "play_clock_seconds": 40.0,
            "game_clock_stops": True,
            "first_down_clock_stops": True,  # NCAA rule
            "overtime_rules": "alternating_possessions"
        },
        "key_numbers": [3, 4, 6, 7, 10, 14],
        "home_advantage_points": 3.0  # Higher than NFL
    },
    "NCAAB": {
        "periods": 2,  # Halves
        "period_length_minutes": 20.0,
        "overtime_length_minutes": 5.0,
        "typical_possessions_per_game": 70.0,  # Slower than NBA
        "typical_seconds_per_possession": 18.0,
        "scoring": {
            "field_goal": 2,
            "three_pointer": 3,
            "free_throw": 1,
            "typical_points_per_possession": 1.0  # Lower than NBA
        },
        "clock_rules": {
            "shot_clock_seconds": 30.0,  # Longer than NBA
            "game_clock_stops": True,
            "overtime_rules": "5_min_periods"
        },
        "key_numbers": [3, 4, 7],
        "home_advantage_points": 4.0  # Higher than NBA
    }
}

def get_league_config(league: str) -> Dict[str, Any]:
    """
    Returns full configuration for a league.
    
    Args:
        league: League identifier (e.g., "NBA", "NFL", "MLB", "NHL", "NCAAF", "NCAAB")
    
    Returns:
        Dict with all league configuration parameters
    """
    league = league.upper()
    if league not in LEAGUE_CONFIGS:
        # Return a generic fallback config
        return {
            "periods": 4,
            "period_length_minutes": 15.0,
            "typical_possessions_per_game": 50.0,
            "scoring": {"typical_points_per_possession": 1.0},
            "clock_rules": {"game_clock_stops": True},
            "key_numbers": [3, 4, 7],
            "home_advantage_points": 2.0
        }
    return LEAGUE_CONFIGS[league].copy()

def get_periods(league: str) -> int:
    """Returns number of periods for a league."""
    config = get_league_config(league)
    return config.get("periods", 4)

def get_period_length(league: str) -> float:
    """Returns period length in minutes for a league."""
    config = get_league_config(league)
    return config.get("period_length_minutes", 15.0)

def get_typical_possessions(league: str) -> float:
    """
    Returns typical number of possessions/drives/shifts per game for a league.
    League-agnostic function that returns the appropriate metric.
    """
    config = get_league_config(league)
    league = league.upper()
    
    if league == "NBA" or league == "NCAAB":
        return config.get("typical_possessions_per_game", 100.0)
    elif league == "NFL" or league == "NCAAF":
        return config.get("typical_drives_per_game", 12.0) * 2  # Both teams
    elif league == "NHL":
        return config.get("typical_shifts_per_game", 50.0) * 2  # Both teams
    elif league == "MLB":
        return config.get("typical_innings_per_game", 9.0)
    else:
        return config.get("typical_possessions_per_game", 50.0)

def get_scoring_rules(league: str) -> Dict[str, Any]:
    """Returns scoring rules for a league."""
    config = get_league_config(league)
    return config.get("scoring", {})

def get_clock_rules(league: str) -> Dict[str, Any]:
    """Returns clock rules for a league."""
    config = get_league_config(league)
    return config.get("clock_rules", {})

def get_key_numbers(league: str) -> list:
    """Returns key numbers (common margins) for a league."""
    config = get_league_config(league)
    return config.get("key_numbers", [3, 4, 7])

def get_home_advantage(league: str) -> float:
    """Returns typical home advantage in points/runs/goals for a league."""
    config = get_league_config(league)
    return config.get("home_advantage_points", 2.0)

```

