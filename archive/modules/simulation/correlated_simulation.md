# Correlated Simulation Module

"""
Module Name: Correlated Simulation
Version: 1.0.0
Description: Structures simulations to support correlated markets (SGP-style) by simulating team-level outcomes first, then deriving player stats from team outcomes via allocation rules.
Functions:
    - simulate_team_outcomes(game: dict, n_iter: int = 10000) -> dict
    - allocate_player_stats_from_team(team_outcome: dict, players: list, league: str) -> list
    - simulate_correlated_markets(game: dict, markets: list, n_iter: int = 10000) -> dict
    - get_allocation_rules(league: str, stat_key: str) -> dict
Usage Notes:
    - Simulates team-level outcomes first (pace, possessions, scoring, total plays)
    - Derives player stats from team outcomes via allocation rules
    - Supports NBA (minutes + usage), NFL (target share, carry share), MLB (lineup position, PA share), NHL (TOI, line combinations)
    - Configurable usage/allocation helpers with parameters
"""

```python
from __future__ import annotations
from typing import Dict, List, Any, Optional
import random

try:
    import numpy as np
except ImportError:
    np = None

def get_allocation_rules(league: str, stat_key: str) -> Dict[str, Any]:
    """
    Returns allocation rules for deriving player stats from team outcomes.
    
    Args:
        league: League identifier
        stat_key: Stat identifier (e.g., "pts", "pass_yds", "hits")
    
    Returns:
        Dict with allocation parameters and rules
    """
    league = league.upper()
    stat_key = stat_key.lower()
    
    # NBA allocation rules
    if league == "NBA":
        rules = {
            "pts": {
                "allocation_method": "usage_rate",
                "base_parameter": "usage_rate",
                "variance_factor": 0.15,  # 15% variance in allocation
                "minutes_dependent": True
            },
            "reb": {
                "allocation_method": "position_based",
                "base_parameter": "rebound_rate",
                "variance_factor": 0.20,
                "minutes_dependent": True
            },
            "ast": {
                "allocation_method": "usage_rate",
                "base_parameter": "usage_rate",
                "variance_factor": 0.18,
                "minutes_dependent": True
            }
        }
        return rules.get(stat_key, {
            "allocation_method": "usage_rate",
            "base_parameter": "usage_rate",
            "variance_factor": 0.15,
            "minutes_dependent": True
        })
    
    # NFL allocation rules
    elif league == "NFL":
        rules = {
            "pass_yds": {
                "allocation_method": "target_share",
                "base_parameter": "target_share",
                "variance_factor": 0.25,
                "snap_dependent": True
            },
            "rush_yds": {
                "allocation_method": "carry_share",
                "base_parameter": "carry_share",
                "variance_factor": 0.20,
                "snap_dependent": True
            },
            "rec_yds": {
                "allocation_method": "target_share",
                "base_parameter": "target_share",
                "variance_factor": 0.22,
                "snap_dependent": True
            },
            "td": {
                "allocation_method": "touchdown_share",
                "base_parameter": "touchdown_share",
                "variance_factor": 0.30,
                "snap_dependent": True
            }
        }
        return rules.get(stat_key, {
            "allocation_method": "target_share",
            "base_parameter": "target_share",
            "variance_factor": 0.20,
            "snap_dependent": True
        })
    
    # MLB allocation rules
    elif league == "MLB":
        rules = {
            "hits": {
                "allocation_method": "pa_share",
                "base_parameter": "pa_share",
                "variance_factor": 0.15,
                "lineup_dependent": True
            },
            "runs": {
                "allocation_method": "lineup_position",
                "base_parameter": "lineup_position",
                "variance_factor": 0.20,
                "lineup_dependent": True
            },
            "rbis": {
                "allocation_method": "lineup_position",
                "base_parameter": "lineup_position",
                "variance_factor": 0.18,
                "lineup_dependent": True
            }
        }
        return rules.get(stat_key, {
            "allocation_method": "pa_share",
            "base_parameter": "pa_share",
            "variance_factor": 0.15,
            "lineup_dependent": True
        })
    
    # NHL allocation rules
    elif league == "NHL":
        rules = {
            "goals": {
                "allocation_method": "toi_share",
                "base_parameter": "toi_share",
                "variance_factor": 0.25,
                "line_dependent": True
            },
            "assists": {
                "allocation_method": "toi_share",
                "base_parameter": "toi_share",
                "variance_factor": 0.22,
                "line_dependent": True
            },
            "shots": {
                "allocation_method": "toi_share",
                "base_parameter": "toi_share",
                "variance_factor": 0.20,
                "line_dependent": True
            }
        }
        return rules.get(stat_key, {
            "allocation_method": "toi_share",
            "base_parameter": "toi_share",
            "variance_factor": 0.20,
            "line_dependent": True
        })
    
    # Fallback
    else:
        return {
            "allocation_method": "equal_share",
            "base_parameter": "usage_rate",
            "variance_factor": 0.20,
            "minutes_dependent": False
        }

def allocate_player_stats_from_team(
    team_outcome: Dict[str, Any],
    players: List[Dict[str, Any]],
    league: str
) -> List[Dict[str, Any]]:
    """
    Allocates player stats from team-level outcomes.
    
    This function takes team-level simulation results (pace, possessions, scoring, etc.)
    and allocates individual player statistics based on usage rates, minutes, and other factors.
    
    Args:
        team_outcome: Dict with team-level outcomes:
            - "team_name": str
            - "pace": float (possessions/drives/shifts)
            - "total_points": float (team scoring)
            - "total_plays": float (total plays/possessions)
            - Other team-level metrics
        players: List of player dicts, each with:
            - "player_name": str
            - "usage_rate": float (or target_share, carry_share, etc.)
            - "proj_minutes": float (or proj_snaps, proj_toi)
            - "stat_key": str (stat to allocate)
            - Other player metadata
        league: League identifier
    
    Returns:
        List of player outcome dicts, each with:
            - "player_name": str
            - "stat_key": str
            - "allocated_stat": float
            - "allocation_factor": float
    """
    league = league.upper()
    player_outcomes = []
    
    # Get team totals
    team_name = team_outcome.get("team_name", "")
    total_points = team_outcome.get("total_points", 0.0)
    total_plays = team_outcome.get("total_plays", team_outcome.get("pace", 0.0))
    
    # Group players by stat_key
    players_by_stat = {}
    for player in players:
        stat_key = player.get("stat_key", "pts")
        if stat_key not in players_by_stat:
            players_by_stat[stat_key] = []
        players_by_stat[stat_key].append(player)
    
    # Allocate stats for each stat type
    for stat_key, stat_players in players_by_stat.items():
        # Get allocation rules
        rules = get_allocation_rules(league, stat_key)
        allocation_method = rules.get("allocation_method", "usage_rate")
        base_parameter = rules.get("base_parameter", "usage_rate")
        variance_factor = rules.get("variance_factor", 0.15)
        
        # Calculate total allocation weight
        total_weight = 0.0
        for player in stat_players:
            weight = player.get(base_parameter, 0.0)
            # Adjust for minutes/snaps/TOI if applicable
            if rules.get("minutes_dependent", False):
                weight *= player.get("proj_minutes", 0.0) / 48.0  # Normalize to 48 min game
            elif rules.get("snap_dependent", False):
                weight *= player.get("proj_snaps", 0.0) / 70.0  # Normalize to 70 snap game
            elif rules.get("lineup_dependent", False):
                # Lineup position affects allocation (higher in lineup = more opportunities)
                lineup_pos = player.get("lineup_position", 5)
                weight *= (10 - lineup_pos) / 5.0  # Higher position = more weight
            total_weight += weight
        
        # Allocate stats to players
        for player in stat_players:
            player_name = player.get("player_name", "")
            weight = player.get(base_parameter, 0.0)
            
            # Apply minutes/snaps/TOI adjustment
            if rules.get("minutes_dependent", False):
                weight *= player.get("proj_minutes", 0.0) / 48.0
            elif rules.get("snap_dependent", False):
                weight *= player.get("proj_snaps", 0.0) / 70.0
            elif rules.get("lineup_dependent", False):
                lineup_pos = player.get("lineup_position", 5)
                weight *= (10 - lineup_pos) / 5.0
            
            # Calculate allocation factor
            allocation_factor = weight / total_weight if total_weight > 0 else 0.0
            
            # Add variance
            if np is not None:
                variance = np.random.normal(1.0, variance_factor)
            else:
                variance = 1.0 + random.gauss(0.0, variance_factor)
            variance = max(0.5, min(1.5, variance))  # Cap variance
            
            # Allocate stat based on stat type
            if stat_key in ("pts", "goals", "runs"):
                # Points/goals/runs: allocate from total_points
                allocated_stat = total_points * allocation_factor * variance
            elif stat_key in ("reb", "ast", "assists"):
                # Rebounds/assists: allocate from total_plays
                allocated_stat = total_plays * allocation_factor * variance * 0.3  # Rough estimate
            elif stat_key in ("pass_yds", "rush_yds", "rec_yds"):
                # Yards: allocate from total_plays with yardage multiplier
                allocated_stat = total_plays * allocation_factor * variance * 7.0  # Rough estimate
            else:
                # Default: allocate from total_plays
                allocated_stat = total_plays * allocation_factor * variance
            
            player_outcomes.append({
                "player_name": player_name,
                "team": team_name,
                "stat_key": stat_key,
                "allocated_stat": max(0.0, allocated_stat),
                "allocation_factor": allocation_factor,
                "variance_applied": variance
            })
    
    return player_outcomes

def simulate_team_outcomes(game: Dict[str, Any], n_iter: int = 10000) -> Dict[str, Any]:
    """
    Simulates team-level outcomes for a game.
    
    This is the first step in correlated simulation: simulate team-level metrics
    (pace, possessions, scoring, total plays) that will be used to allocate player stats.
    
    Args:
        game: Game dict with:
            - "home_team": dict with team data
            - "away_team": dict with team data
            - "league": str
            - Other game context
        n_iter: Number of simulation iterations
    
    Returns:
        Dict with team-level outcomes:
            - "home_outcomes": list of outcome dicts
            - "away_outcomes": list of outcome dicts
            - "game_outcomes": list of game-level outcome dicts
    """
    # This is a simplified version; in practice, this would call
    # the main simulation_engine functions
    # TODO: Integrate with simulation_engine.run_game_simulation
    
    # For now, return structure that can be used by allocation functions
    return {
        "home_outcomes": [],
        "away_outcomes": [],
        "game_outcomes": []
    }

def simulate_correlated_markets(
    game: Dict[str, Any],
    markets: List[Dict[str, Any]],
    n_iter: int = 10000
) -> Dict[str, Any]:
    """
    Simulates correlated markets (SGP-style) by first simulating team outcomes,
    then deriving player stats from team outcomes.
    
    This ensures that player props are correlated with team outcomes
    (e.g., if team scores more, players score more).
    
    Args:
        game: Game dict
        markets: List of market dicts to simulate:
            - Team markets: {"type": "spread", "team": "...", "line": ...}
            - Player props: {"type": "prop", "player": "...", "stat": "...", "line": ...}
        n_iter: Number of simulation iterations
    
    Returns:
        Dict with simulation results for all markets, maintaining correlations
    """
    # Step 1: Simulate team-level outcomes
    team_outcomes = simulate_team_outcomes(game, n_iter)
    
    # Step 2: For each iteration, allocate player stats from team outcomes
    # This maintains correlation between team and player outcomes
    
    # TODO: Full implementation would:
    # 1. Run team simulation for n_iter iterations
    # 2. For each iteration, allocate player stats
    # 3. Calculate probabilities for all markets
    # 4. Return correlated results
    
    return {
        "team_outcomes": team_outcomes,
        "player_outcomes": [],
        "market_results": []
    }

```

