"""
Omega Betting Module

Provides odds evaluation, Kelly staking, and parlay tools.
"""

from src.betting.odds_eval import (
    american_to_decimal,
    implied_probability,
    expected_value,
    expected_value_percent,
    edge_percentage,
)

from src.betting.kelly_staking import (
    kelly_fraction,
    recommend_stake,
    UNIT_SIZE,
    MAX_BANKROLL_ALLOC,
)

from src.betting.parlay_tools import (
    validate_correlation_matrix,
    joint_probability,
    adjusted_ev,
)

from src.betting.correlation_engine import (
    CorrelationEngine,
    compute_sgp_correlations,
    get_correlation_strength_label,
)

__all__ = [
    "american_to_decimal",
    "implied_probability",
    "expected_value",
    "expected_value_percent",
    "edge_percentage",
    "kelly_fraction",
    "recommend_stake",
    "UNIT_SIZE",
    "MAX_BANKROLL_ALLOC",
    "validate_correlation_matrix",
    "joint_probability",
    "adjusted_ev",
    "CorrelationEngine",
    "compute_sgp_correlations",
    "get_correlation_strength_label",
]
