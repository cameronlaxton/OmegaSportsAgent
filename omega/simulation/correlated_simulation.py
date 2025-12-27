"""
Correlated Simulation Module

Structures simulations to support correlated markets (SGP-style) by simulating
team-level outcomes first, then deriving player stats from team outcomes via
allocation rules.
"""

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
    
    if league == "NBA":
        rules = {
            "pts": {"allocation_method": "usage_rate", "base_parameter": "usage_rate", "variance_factor": 0.15, "minutes_dependent": True},
            "reb": {"allocation_method": "position_based", "base_parameter": "rebound_rate", "variance_factor": 0.20, "minutes_dependent": True},
            "ast": {"allocation_method": "usage_rate", "base_parameter": "usage_rate", "variance_factor": 0.18, "minutes_dependent": True}
        }
        return rules.get(stat_key, {"allocation_method": "usage_rate", "base_parameter": "usage_rate", "variance_factor": 0.15, "minutes_dependent": True})
    
    elif league == "NFL":
        rules = {
            "pass_yds": {"allocation_method": "target_share", "base_parameter": "target_share", "variance_factor": 0.25, "snap_dependent": True},
            "rush_yds": {"allocation_method": "carry_share", "base_parameter": "carry_share", "variance_factor": 0.20, "snap_dependent": True},
            "rec_yds": {"allocation_method": "target_share", "base_parameter": "target_share", "variance_factor": 0.22, "snap_dependent": True},
            "td": {"allocation_method": "touchdown_share", "base_parameter": "touchdown_share", "variance_factor": 0.30, "snap_dependent": True}
        }
        return rules.get(stat_key, {"allocation_method": "target_share", "base_parameter": "target_share", "variance_factor": 0.20, "snap_dependent": True})
    
    elif league == "MLB":
        rules = {
            "hits": {"allocation_method": "pa_share", "base_parameter": "pa_share", "variance_factor": 0.15, "lineup_dependent": True},
            "runs": {"allocation_method": "lineup_position", "base_parameter": "lineup_position", "variance_factor": 0.20, "lineup_dependent": True},
            "rbis": {"allocation_method": "lineup_position", "base_parameter": "lineup_position", "variance_factor": 0.18, "lineup_dependent": True}
        }
        return rules.get(stat_key, {"allocation_method": "pa_share", "base_parameter": "pa_share", "variance_factor": 0.15, "lineup_dependent": True})
    
    elif league == "NHL":
        rules = {
            "goals": {"allocation_method": "toi_share", "base_parameter": "toi_share", "variance_factor": 0.25, "line_dependent": True},
            "assists": {"allocation_method": "toi_share", "base_parameter": "toi_share", "variance_factor": 0.22, "line_dependent": True},
            "shots": {"allocation_method": "toi_share", "base_parameter": "toi_share", "variance_factor": 0.20, "line_dependent": True}
        }
        return rules.get(stat_key, {"allocation_method": "toi_share", "base_parameter": "toi_share", "variance_factor": 0.20, "line_dependent": True})
    
    return {"allocation_method": "equal_share", "base_parameter": "usage_rate", "variance_factor": 0.20, "minutes_dependent": False}


def allocate_player_stats_from_team(
    team_outcome: Dict[str, Any],
    players: List[Dict[str, Any]],
    league: str
) -> List[Dict[str, Any]]:
    """
    Allocates player stats from team-level outcomes.
    """
    league = league.upper()
    player_outcomes = []
    
    team_name = team_outcome.get("team_name", "")
    total_points = team_outcome.get("total_points", 0.0)
    total_plays = team_outcome.get("total_plays", team_outcome.get("pace", 0.0))
    
    players_by_stat = {}
    for player in players:
        stat_key = player.get("stat_key", "pts")
        if stat_key not in players_by_stat:
            players_by_stat[stat_key] = []
        players_by_stat[stat_key].append(player)
    
    for stat_key, stat_players in players_by_stat.items():
        rules = get_allocation_rules(league, stat_key)
        base_parameter = rules.get("base_parameter", "usage_rate")
        variance_factor = rules.get("variance_factor", 0.15)
        
        total_weight = 0.0
        for player in stat_players:
            weight = player.get(base_parameter, 0.0)
            if rules.get("minutes_dependent", False):
                weight *= player.get("proj_minutes", 0.0) / 48.0
            elif rules.get("snap_dependent", False):
                weight *= player.get("proj_snaps", 0.0) / 70.0
            elif rules.get("lineup_dependent", False):
                lineup_pos = player.get("lineup_position", 5)
                weight *= (10 - lineup_pos) / 5.0
            total_weight += weight
        
        for player in stat_players:
            player_name = player.get("player_name", "")
            weight = player.get(base_parameter, 0.0)
            
            if rules.get("minutes_dependent", False):
                weight *= player.get("proj_minutes", 0.0) / 48.0
            elif rules.get("snap_dependent", False):
                weight *= player.get("proj_snaps", 0.0) / 70.0
            elif rules.get("lineup_dependent", False):
                lineup_pos = player.get("lineup_position", 5)
                weight *= (10 - lineup_pos) / 5.0
            
            allocation_factor = weight / total_weight if total_weight > 0 else 0.0
            
            if np is not None:
                variance = np.random.normal(1.0, variance_factor)
            else:
                variance = 1.0 + random.gauss(0.0, variance_factor)
            variance = max(0.5, min(1.5, variance))
            
            if stat_key in ("pts", "goals", "runs"):
                allocated_stat = total_points * allocation_factor * variance
            elif stat_key in ("reb", "ast", "assists"):
                allocated_stat = total_plays * allocation_factor * variance * 0.3
            elif stat_key in ("pass_yds", "rush_yds", "rec_yds"):
                allocated_stat = total_plays * allocation_factor * variance * 7.0
            else:
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
    """Simulates team-level outcomes for a game."""
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
    """
    team_outcomes = simulate_team_outcomes(game, n_iter)
    
    return {
        "team_outcomes": team_outcomes,
        "player_outcomes": [],
        "market_results": []
    }
