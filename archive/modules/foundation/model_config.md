# Model Configuration Module

"""
Module Name: Model Configuration
Version: 1.0.0
Description: Centralized configuration for edge thresholds, variance scalars, blend weights, and other model parameters.
Functions:
    - get_edge_thresholds() -> dict
    - get_variance_scalars(league: str, stat_key: str) -> float
    - get_blend_weights() -> dict
    - get_confidence_tier_caps() -> dict
Usage Notes:
    - All thresholds and weights are centralized here for easy tuning.
    - Update these values to adjust model behavior across the entire system.
"""

```python
from __future__ import annotations
from typing import Dict

# ============================================================================
# EDGE & EV THRESHOLDS
# ============================================================================

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
        "min_edge_pct": 3.0,          # Minimum edge % for sides/ML/totals
        "min_ev_pct": 2.5,            # Minimum EV % for all bets
        "min_prop_hit_rate": 0.56,    # Minimum model hit rate for props (56%)
        "max_ci_width_pct": 30.0,     # Maximum CI width in percentage points
        "contrarian_edge_override": 5.0,  # Required edge when market is contrarian
        "high_confidence_edge_override": 10.0  # Required edge when market confidence is low
    }

# ============================================================================
# VARIANCE SCALARS (per league and stat)
# ============================================================================

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
    
    # League-specific defaults
    defaults = {
        "NBA": {
            "default": 0.45,      # General NBA stat variance
            "pts": 0.50,          # Points have higher variance
            "reb": 0.40,          # Rebounds slightly lower variance
            "ast": 0.45,          # Assists similar to default
            "score": 0.35,        # Team scoring (lower variance than individual)
        },
        "NFL": {
            "default": 0.60,      # General NFL stat variance
            "pass_yds": 0.65,     # Passing yards higher variance
            "rush_yds": 0.55,     # Rushing yards moderate variance
            "rec_yds": 0.60,      # Receiving yards similar to default
            "td": 0.80,           # Touchdowns high variance (discrete)
            "score": 0.50,        # Team scoring
        },
        "MLB": {
            "default": 0.50,
            "score": 0.40,
        },
        "NHL": {
            "default": 0.55,
            "goals": 0.70,        # Goals high variance (discrete)
            "score": 0.45,
        }
    }
    
    league_defaults = defaults.get(league, {"default": 0.50})
    return league_defaults.get(stat_key, league_defaults.get("default", 0.50))

# ============================================================================
# BLEND WEIGHTS (baseline vs context)
# ============================================================================

def get_blend_weights() -> Dict:
    """
    Returns blend weights for combining baseline performance with context adjustments.
    
    The formula is: final = baseline * (baseline_weight + context_weight * context_multiplier)
    Or equivalently: final = baseline * baseline_weight + (baseline * context_multiplier) * context_weight
    
    Returns:
        Dict with keys:
            - "baseline_weight": float (default 0.60)
            - "context_weight": float (default 0.40)
    """
    return {
        "baseline_weight": 0.60,   # Weight for baseline performance
        "context_weight": 0.40,    # Weight for context-adjusted performance
    }

# ============================================================================
# CONFIDENCE TIER DEFINITIONS
# ============================================================================

def get_confidence_tier_caps() -> Dict:
    """
    Returns unit caps and definitions for confidence tiers.
    
    Returns:
        Dict with keys:
            - "tier_a": dict with "min_edge", "min_ev", "max_units"
            - "tier_b": dict with "min_edge", "min_ev", "max_units"
            - "tier_c": dict with "min_edge", "min_ev", "max_units"
    """
    return {
        "tier_a": {
            "min_edge_pct": 7.0,
            "min_ev_pct": 5.0,
            "max_units": 2.0,
            "description": "High confidence: edge ≥ 7% & EV ≥ 5%"
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

# ============================================================================
# SIMULATION PARAMETERS
# ============================================================================

def get_simulation_params() -> Dict:
    """
    Returns default simulation parameters.
    
    Returns:
        Dict with keys:
            - "default_iterations": int (default 10000)
            - "high_precision_iterations": int (default 25000)
            - "edge_threshold_for_high_precision": float (default 1.5) - multiplier of min_edge
    """
    return {
        "default_iterations": 10000,
        "high_precision_iterations": 25000,
        "edge_threshold_for_high_precision": 1.5,  # Use high precision when edge < 1.5 * min_edge
    }
```

