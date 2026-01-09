"""
Analytics Module

Provides universal predictive models, league-specific baselines, and market analysis.
"""

from src.analytics.universal_analytics import (
    pythagorean_expectation,
    elo_win_probability,
    elo_rating_update,
    glicko_rating_update,
    get_pythagorean_exponent,
    get_elo_k_factor,
    get_elo_home_adjustment,
)

from src.analytics.league_baselines import (
    dean_oliver_four_factors,
    nfl_epa_interface,
    mlb_run_expectancy,
    nhl_xg_per_shot,
    MLB_RE_TABLE,
)

from src.analytics.market_analysis import (
    calculate_line_movement_score,
    evaluate_sharp_contrarian_signal,
    assess_market_confidence,
)

__all__ = [
    "pythagorean_expectation",
    "elo_win_probability",
    "elo_rating_update",
    "glicko_rating_update",
    "get_pythagorean_exponent",
    "get_elo_k_factor",
    "get_elo_home_adjustment",
    "dean_oliver_four_factors",
    "nfl_epa_interface",
    "mlb_run_expectancy",
    "nhl_xg_per_shot",
    "MLB_RE_TABLE",
    "calculate_line_movement_score",
    "evaluate_sharp_contrarian_signal",
    "assess_market_confidence",
]
