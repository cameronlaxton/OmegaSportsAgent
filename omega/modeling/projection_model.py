"""
Projection Model Module

Generates baseline strengths and context adjustments for both team-level
and player-level projections.
"""

from __future__ import annotations
from typing import Dict, List, Any

from omega.foundation.model_config import get_blend_weights, get_variance_scalars


def compute_baseline(matchup_data: Dict[str, Any], league: str) -> Dict[str, Any]:
    """
    Computes baseline metrics from matchup data.
    
    Args:
        matchup_data: Dict with team_a and team_b data
        league: League identifier
    
    Returns:
        Dict with baseline metrics (pace, off_rating, def_rating, etc.)
    """
    league = league.upper()
    baseline: Dict[str, Any] = {}
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


def compute_context(baseline: Dict[str, Any], context_modifiers: Dict[str, float], league: str) -> Dict[str, Any]:
    """
    Applies context modifiers to baseline metrics.
    
    Args:
        baseline: Dict from compute_baseline
        context_modifiers: Dict with pace, efficiency, scoring_variance modifiers
        league: League identifier
    
    Returns:
        Dict with contextualized metrics
    """
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


def final_projection(injury_adjusted: Dict[str, Any], contextualized: Dict[str, Any], market_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Combines injury adjustments, contextualized metrics, and market info into final projection.
    
    Args:
        injury_adjusted: Dict with injury_penalty and adjustments
        contextualized: Dict from compute_context
        market_info: Dict with market lines and odds
    
    Returns:
        Dict with final projection including true_strength and expected_total
    """
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


def compute_player_baseline(player_data: Dict[str, Any], league: str) -> float:
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
        baseline_per_snap = player_data.get("baseline_per_snap", 0.0)
        proj_snaps = player_data.get("proj_snaps", 0.0)
        return baseline_per_snap * proj_snaps
    else:
        baseline_per_min = player_data.get("baseline_per_min", 0.0)
        proj_minutes = player_data.get("proj_minutes", 0.0)
        return baseline_per_min * proj_minutes


def compute_player_context_multiplier(player_data: Dict[str, Any], context_modifiers: Dict[str, float], league: str) -> float:
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
    
    stat_key = player_data.get("stat_key", "default").lower()
    
    if stat_key in {"reb", "rebounds"}:
        context_mult = 0.3 * matchup_mult + 0.7 * pace_mult
    elif stat_key in {"ast", "assists"}:
        context_mult = 0.5 * matchup_mult + 0.5 * pace_mult
    else:
        context_mult = 0.6 * matchup_mult + 0.4 * pace_mult
    
    return context_mult


def compute_player_projections(
    players: List[Dict[str, Any]],
    context_modifiers: Dict[str, float],
    injury_adjusted_usage: Dict[str, float],
    league: str
) -> List[Dict[str, Any]]:
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
    
    projections: List[Dict[str, Any]] = []
    
    for player in players:
        player_name = player.get("player_name", "")
        
        original_usage = player.get("usage_rate", 1.0)
        adjusted_usage = injury_adjusted_usage.get(player_name, original_usage)
        
        baseline = compute_player_baseline(player, league)
        
        stat_key = player.get("stat_key", "pts").lower()
        usage_sensitive_stats = {"pts", "fgm", "fga", "3pm", "3pa", "ftm", "fta", "ast", "touches", "pass_att", "rush_att", "targets"}
        if stat_key in usage_sensitive_stats:
            baseline = baseline * (adjusted_usage / max(0.1, original_usage))
        
        context_mult = compute_player_context_multiplier(player, context_modifiers, league)
        
        player_mean = baseline * (baseline_weight + context_weight * context_mult)
        player_mean = max(0.0, player_mean)
        
        variance_scalar = get_variance_scalars(league, stat_key)
        variance = player_mean * variance_scalar
        
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
