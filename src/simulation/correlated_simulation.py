"""
Correlated Simulation Module

Structures simulations to support correlated markets (SGP-style) by simulating
team-level outcomes first, then deriving player stats from team outcomes via
allocation rules.

Supports all 9 sport archetypes:
  basketball, american_football, baseball, hockey, soccer,
  tennis, golf, fighting, esports
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional
import random

try:
    import numpy as np
except ImportError:
    np = None


# ---------------------------------------------------------------------------
# Per-archetype allocation rule sets
# ---------------------------------------------------------------------------

_BASKETBALL_RULES = {
    "pts": {"allocation_method": "usage_rate", "base_parameter": "usage_rate", "variance_factor": 0.15, "minutes_dependent": True},
    "reb": {"allocation_method": "position_based", "base_parameter": "rebound_rate", "variance_factor": 0.20, "minutes_dependent": True},
    "ast": {"allocation_method": "usage_rate", "base_parameter": "usage_rate", "variance_factor": 0.18, "minutes_dependent": True},
    "3pm": {"allocation_method": "usage_rate", "base_parameter": "usage_rate", "variance_factor": 0.22, "minutes_dependent": True},
    "stl": {"allocation_method": "usage_rate", "base_parameter": "usage_rate", "variance_factor": 0.25, "minutes_dependent": True},
    "blk": {"allocation_method": "position_based", "base_parameter": "rebound_rate", "variance_factor": 0.25, "minutes_dependent": True},
    "pra": {"allocation_method": "usage_rate", "base_parameter": "usage_rate", "variance_factor": 0.12, "minutes_dependent": True},
}
_BASKETBALL_DEFAULT = {"allocation_method": "usage_rate", "base_parameter": "usage_rate", "variance_factor": 0.15, "minutes_dependent": True}

_FOOTBALL_RULES = {
    "pass_yds": {"allocation_method": "target_share", "base_parameter": "target_share", "variance_factor": 0.25, "snap_dependent": True},
    "rush_yds": {"allocation_method": "carry_share", "base_parameter": "carry_share", "variance_factor": 0.20, "snap_dependent": True},
    "rec_yds": {"allocation_method": "target_share", "base_parameter": "target_share", "variance_factor": 0.22, "snap_dependent": True},
    "receptions": {"allocation_method": "target_share", "base_parameter": "target_share", "variance_factor": 0.20, "snap_dependent": True},
    "pass_td": {"allocation_method": "touchdown_share", "base_parameter": "touchdown_share", "variance_factor": 0.30, "snap_dependent": True},
    "rush_td": {"allocation_method": "carry_share", "base_parameter": "carry_share", "variance_factor": 0.30, "snap_dependent": True},
    "rec_td": {"allocation_method": "target_share", "base_parameter": "target_share", "variance_factor": 0.30, "snap_dependent": True},
    "completions": {"allocation_method": "target_share", "base_parameter": "target_share", "variance_factor": 0.20, "snap_dependent": True},
}
_FOOTBALL_DEFAULT = {"allocation_method": "target_share", "base_parameter": "target_share", "variance_factor": 0.20, "snap_dependent": True}

_BASEBALL_RULES = {
    "hits": {"allocation_method": "pa_share", "base_parameter": "pa_share", "variance_factor": 0.15, "lineup_dependent": True},
    "total_bases": {"allocation_method": "pa_share", "base_parameter": "pa_share", "variance_factor": 0.18, "lineup_dependent": True},
    "runs": {"allocation_method": "lineup_position", "base_parameter": "lineup_position", "variance_factor": 0.20, "lineup_dependent": True},
    "rbis": {"allocation_method": "lineup_position", "base_parameter": "lineup_position", "variance_factor": 0.18, "lineup_dependent": True},
    "hrs": {"allocation_method": "pa_share", "base_parameter": "pa_share", "variance_factor": 0.30, "lineup_dependent": True},
    "stolen_bases": {"allocation_method": "pa_share", "base_parameter": "speed_rating", "variance_factor": 0.35, "lineup_dependent": False},
    "strikeouts_pitched": {"allocation_method": "innings_share", "base_parameter": "k_rate", "variance_factor": 0.20, "lineup_dependent": False},
    "outs_recorded": {"allocation_method": "innings_share", "base_parameter": "innings_share", "variance_factor": 0.15, "lineup_dependent": False},
}
_BASEBALL_DEFAULT = {"allocation_method": "pa_share", "base_parameter": "pa_share", "variance_factor": 0.15, "lineup_dependent": True}

_HOCKEY_RULES = {
    "goals": {"allocation_method": "toi_share", "base_parameter": "toi_share", "variance_factor": 0.25, "line_dependent": True},
    "assists": {"allocation_method": "toi_share", "base_parameter": "toi_share", "variance_factor": 0.22, "line_dependent": True},
    "points": {"allocation_method": "toi_share", "base_parameter": "toi_share", "variance_factor": 0.20, "line_dependent": True},
    "shots_on_goal": {"allocation_method": "toi_share", "base_parameter": "toi_share", "variance_factor": 0.18, "line_dependent": True},
    "saves": {"allocation_method": "goalie_only", "base_parameter": "saves_share", "variance_factor": 0.15, "line_dependent": False},
    "blocked_shots": {"allocation_method": "toi_share", "base_parameter": "toi_share", "variance_factor": 0.20, "line_dependent": True},
    "power_play_points": {"allocation_method": "pp_toi_share", "base_parameter": "pp_toi_share", "variance_factor": 0.28, "line_dependent": True},
}
_HOCKEY_DEFAULT = {"allocation_method": "toi_share", "base_parameter": "toi_share", "variance_factor": 0.20, "line_dependent": True}

_SOCCER_RULES = {
    "goals": {"allocation_method": "minutes_share", "base_parameter": "goals_mean", "variance_factor": 0.30, "minutes_dependent": True},
    "assists": {"allocation_method": "minutes_share", "base_parameter": "assists_mean", "variance_factor": 0.28, "minutes_dependent": True},
    "shots": {"allocation_method": "minutes_share", "base_parameter": "shots_mean", "variance_factor": 0.20, "minutes_dependent": True},
    "shots_on_target": {"allocation_method": "minutes_share", "base_parameter": "shots_on_target_mean", "variance_factor": 0.22, "minutes_dependent": True},
    "tackles": {"allocation_method": "minutes_share", "base_parameter": "minutes_mean", "variance_factor": 0.18, "minutes_dependent": True},
    "corners": {"allocation_method": "team_level", "base_parameter": "corners_per_game", "variance_factor": 0.20, "minutes_dependent": False},
}
_SOCCER_DEFAULT = {"allocation_method": "minutes_share", "base_parameter": "minutes_mean", "variance_factor": 0.20, "minutes_dependent": True}

_TENNIS_RULES = {
    "aces": {"allocation_method": "serve_based", "base_parameter": "ace_rate", "variance_factor": 0.25, "minutes_dependent": False},
    "double_faults": {"allocation_method": "serve_based", "base_parameter": "double_fault_rate", "variance_factor": 0.25, "minutes_dependent": False},
    "total_games": {"allocation_method": "match_based", "base_parameter": "games_won_mean", "variance_factor": 0.15, "minutes_dependent": False},
}
_TENNIS_DEFAULT = {"allocation_method": "match_based", "base_parameter": "rating", "variance_factor": 0.20, "minutes_dependent": False}

_GOLF_RULES = {
    "finishing_position": {"allocation_method": "field_based", "base_parameter": "strokes_gained_total", "variance_factor": 0.30, "minutes_dependent": False},
    "round_score": {"allocation_method": "round_based", "base_parameter": "scoring_avg", "variance_factor": 0.10, "minutes_dependent": False},
}
_GOLF_DEFAULT = {"allocation_method": "field_based", "base_parameter": "strokes_gained_total", "variance_factor": 0.25, "minutes_dependent": False}

_FIGHTING_RULES = {
    "method_of_victory": {"allocation_method": "fighter_based", "base_parameter": "ko_tko_rate", "variance_factor": 0.30, "minutes_dependent": False},
    "total_rounds": {"allocation_method": "fighter_based", "base_parameter": "avg_fight_time", "variance_factor": 0.25, "minutes_dependent": False},
    "sig_strikes": {"allocation_method": "fighter_based", "base_parameter": "sig_strikes_per_min", "variance_factor": 0.22, "minutes_dependent": False},
    "takedowns": {"allocation_method": "fighter_based", "base_parameter": "takedown_avg", "variance_factor": 0.25, "minutes_dependent": False},
}
_FIGHTING_DEFAULT = {"allocation_method": "fighter_based", "base_parameter": "win_pct", "variance_factor": 0.25, "minutes_dependent": False}

_ESPORTS_RULES = {
    "kills": {"allocation_method": "rating_based", "base_parameter": "rating", "variance_factor": 0.20, "minutes_dependent": False},
    "deaths": {"allocation_method": "rating_based", "base_parameter": "rating", "variance_factor": 0.20, "minutes_dependent": False},
    "assists": {"allocation_method": "rating_based", "base_parameter": "rating", "variance_factor": 0.22, "minutes_dependent": False},
    "total_rounds": {"allocation_method": "match_based", "base_parameter": "avg_round_diff", "variance_factor": 0.15, "minutes_dependent": False},
    "total_maps": {"allocation_method": "match_based", "base_parameter": "map_win_rate", "variance_factor": 0.15, "minutes_dependent": False},
}
_ESPORTS_DEFAULT = {"allocation_method": "rating_based", "base_parameter": "rating", "variance_factor": 0.20, "minutes_dependent": False}


# ---------------------------------------------------------------------------
# Archetype → rules dispatch
# ---------------------------------------------------------------------------

def _get_archetype_rules(league: str):
    """Return (rules_dict, default_rule) for a league via archetype mapping."""
    try:
        from src.simulation.sport_archetypes import get_archetype_name
        archetype = get_archetype_name(league)
    except ImportError:
        archetype = None

    _DISPATCH = {
        "basketball": (_BASKETBALL_RULES, _BASKETBALL_DEFAULT),
        "american_football": (_FOOTBALL_RULES, _FOOTBALL_DEFAULT),
        "baseball": (_BASEBALL_RULES, _BASEBALL_DEFAULT),
        "hockey": (_HOCKEY_RULES, _HOCKEY_DEFAULT),
        "soccer": (_SOCCER_RULES, _SOCCER_DEFAULT),
        "tennis": (_TENNIS_RULES, _TENNIS_DEFAULT),
        "golf": (_GOLF_RULES, _GOLF_DEFAULT),
        "fighting": (_FIGHTING_RULES, _FIGHTING_DEFAULT),
        "esports": (_ESPORTS_RULES, _ESPORTS_DEFAULT),
    }

    return _DISPATCH.get(archetype, ({}, {"allocation_method": "equal_share", "base_parameter": "usage_rate", "variance_factor": 0.20, "minutes_dependent": False}))


def get_allocation_rules(league: str, stat_key: str) -> Dict[str, Any]:
    """
    Returns allocation rules for deriving player stats from team outcomes.

    Dispatches to archetype-specific rule sets so all 9 sport families are covered.
    """
    league = league.upper()
    stat_key = stat_key.lower()

    rules_dict, default_rule = _get_archetype_rules(league)
    return rules_dict.get(stat_key, default_rule)


# ---------------------------------------------------------------------------
# Stat allocation multiplier per stat key
# ---------------------------------------------------------------------------

_STAT_MULTIPLIERS: Dict[str, float] = {
    # Basketball
    "pts": 1.0, "reb": 0.3, "ast": 0.3, "3pm": 0.15, "stl": 0.1, "blk": 0.1, "pra": 1.0,
    # Football
    "pass_yds": 7.0, "rush_yds": 4.0, "rec_yds": 5.0, "receptions": 0.3, "td": 0.1,
    "pass_td": 0.1, "rush_td": 0.05, "rec_td": 0.05, "completions": 0.5,
    # Baseball
    "hits": 0.25, "total_bases": 0.4, "runs": 0.2, "rbis": 0.25, "hrs": 0.05,
    "stolen_bases": 0.05, "strikeouts_pitched": 0.3, "outs_recorded": 0.5,
    # Hockey
    "goals": 1.0, "assists": 0.6, "points": 1.0, "shots_on_goal": 0.4,
    "saves": 1.0, "blocked_shots": 0.3, "power_play_points": 0.3,
    # Soccer
    "shots": 0.3, "shots_on_target": 0.15, "tackles": 0.2, "corners": 0.2,
    # Tennis
    "aces": 0.15, "double_faults": 0.05, "total_games": 0.5,
    # Golf
    "finishing_position": 1.0, "round_score": 1.0,
    # Fighting
    "method_of_victory": 1.0, "total_rounds": 1.0, "sig_strikes": 0.5, "takedowns": 0.2,
    # Esports
    "kills": 0.4, "deaths": 0.3, "total_rounds": 0.5, "total_maps": 1.0,
}


def allocate_player_stats_from_team(
    team_outcome: Dict[str, Any],
    players: List[Dict[str, Any]],
    league: str,
) -> List[Dict[str, Any]]:
    """
    Allocates player stats from team-level outcomes.
    Works across all archetypes.
    """
    league = league.upper()
    player_outcomes = []

    team_name = team_outcome.get("team_name", "")
    total_points = team_outcome.get("total_points", 0.0)
    total_plays = team_outcome.get("total_plays", team_outcome.get("pace", 0.0))

    players_by_stat: Dict[str, List[Dict]] = {}
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
            elif rules.get("line_dependent", False):
                weight *= player.get("toi_share", 0.15)
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
            elif rules.get("line_dependent", False):
                weight *= player.get("toi_share", 0.15)

            allocation_factor = weight / total_weight if total_weight > 0 else 0.0

            if np is not None:
                variance = np.random.normal(1.0, variance_factor)
            else:
                variance = 1.0 + random.gauss(0.0, variance_factor)
            variance = max(0.5, min(1.5, variance))

            multiplier = _STAT_MULTIPLIERS.get(stat_key, 1.0)

            # For scoring stats, allocate from total_points; for volume stats, from total_plays
            if stat_key in ("pts", "goals", "runs"):
                allocated_stat = total_points * allocation_factor * variance
            else:
                allocated_stat = total_plays * allocation_factor * variance * multiplier

            player_outcomes.append({
                "player_name": player_name,
                "team": team_name,
                "stat_key": stat_key,
                "allocated_stat": max(0.0, allocated_stat),
                "allocation_factor": allocation_factor,
                "variance_applied": variance,
            })

    return player_outcomes


def simulate_team_outcomes(game: Dict[str, Any], n_iter: int = 10000) -> Dict[str, Any]:
    """Simulates team-level outcomes for a game."""
    return {
        "home_outcomes": [],
        "away_outcomes": [],
        "game_outcomes": [],
    }


def simulate_correlated_markets(
    game: Dict[str, Any],
    markets: List[Dict[str, Any]],
    n_iter: int = 10000,
) -> Dict[str, Any]:
    """
    Simulates correlated markets (SGP-style) by first simulating team outcomes,
    then deriving player stats from team outcomes.
    """
    team_outcomes = simulate_team_outcomes(game, n_iter)

    return {
        "team_outcomes": team_outcomes,
        "player_outcomes": [],
        "market_results": [],
    }
