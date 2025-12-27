"""
Model Configuration Module

Centralized configuration for edge thresholds, variance scalars, blend weights,
and other model parameters.
"""

from __future__ import annotations
from typing import Dict


def get_edge_thresholds() -> Dict:
    """
    Returns edge and EV thresholds for bet acceptance.
    
    Returns:
        Dict with keys:
            - "min_edge_pct": float (default 3.0) - minimum edge percentage for sides/ML
            - "min_ev_pct": float (default 2.5) - minimum EV percentage
            - "min_prop_hit_rate": float (default 0.56) - minimum model hit rate for props
            - "max_ci_width_pct": float (default 30.0) - maximum confidence interval width
    """
    return {
        "min_edge_pct": 3.0,
        "min_ev_pct": 2.5,
        "min_prop_hit_rate": 0.56,
        "max_ci_width_pct": 30.0,
        "contrarian_edge_override": 5.0,
        "high_confidence_edge_override": 10.0
    }


def get_variance_scalars(league: str, stat_key: str = "default") -> float:
    """
    Returns variance scalar for a given league and stat.
    
    Variance is typically computed as: variance = mean * variance_scalar
    
    Args:
        league: League identifier (e.g., "NBA", "NFL", "MLB")
        stat_key: Stat identifier (e.g., "pts", "reb", "pass_yds", "score")
    
    Returns:
        float: Variance scalar multiplier
    """
    league = league.upper()
    stat_key = stat_key.lower()
    
    defaults = {
        "NBA": {
            "default": 0.45,
            "pts": 0.50,
            "reb": 0.40,
            "ast": 0.45,
            "score": 0.35,
        },
        "NFL": {
            "default": 0.60,
            "pass_yds": 0.65,
            "rush_yds": 0.55,
            "rec_yds": 0.60,
            "td": 0.80,
            "score": 0.50,
        },
        "MLB": {
            "default": 0.50,
            "score": 0.40,
        },
        "NHL": {
            "default": 0.55,
            "goals": 0.70,
            "score": 0.45,
        }
    }
    
    league_defaults = defaults.get(league, {"default": 0.50})
    return league_defaults.get(stat_key, league_defaults.get("default", 0.50))


def get_blend_weights() -> Dict:
    """
    Returns blend weights for combining baseline performance with context adjustments.
    
    The formula is: final = baseline * (baseline_weight + context_weight * context_multiplier)
    
    Returns:
        Dict with keys:
            - "baseline_weight": float (default 0.60)
            - "context_weight": float (default 0.40)
    """
    return {
        "baseline_weight": 0.60,
        "context_weight": 0.40,
    }


def get_confidence_tier_caps() -> Dict:
    """
    Returns unit caps and definitions for confidence tiers.
    
    Returns:
        Dict with tier definitions including min_edge, min_ev, and max_units
    """
    return {
        "tier_a": {
            "min_edge_pct": 7.0,
            "min_ev_pct": 5.0,
            "max_units": 2.0,
            "description": "High confidence: edge >= 7% & EV >= 5%"
        },
        "tier_b": {
            "min_edge_pct": 4.0,
            "min_ev_pct": 3.0,
            "max_units": 1.5,
            "description": "Medium confidence: edge 4-6.9% or EV 3-4.9%"
        },
        "tier_c": {
            "min_edge_pct": 3.0,
            "min_ev_pct": 2.5,
            "max_units": 1.0,
            "description": "Low confidence: edge 3-3.9% or EV 2.5-2.9%"
        }
    }


def get_simulation_params() -> Dict:
    """
    Returns default simulation parameters.
    
    Returns:
        Dict with simulation configuration
    """
    return {
        "default_iterations": 10000,
        "high_precision_iterations": 25000,
        "edge_threshold_for_high_precision": 1.5,
    }
