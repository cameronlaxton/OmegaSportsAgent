"""
Omega Modeling Package

Provides projection models, probability calibration, and realtime context handling.
"""

from omega.modeling.realtime_context import (
    RealTimeContext,
    normalize_realtime_inputs,
    derive_pace_bias,
    game_script_bias,
    context_multipliers,
)

from omega.modeling.projection_model import (
    compute_baseline,
    compute_context,
    final_projection,
    compute_player_baseline,
    compute_player_context_multiplier,
    compute_player_projections,
)

from omega.modeling.probability_calibration import (
    shrinkage_calibration,
    cap_calibration,
    isotonic_calibration,
    calibrate_probability,
    should_apply_calibration,
)

__all__ = [
    "RealTimeContext",
    "normalize_realtime_inputs",
    "derive_pace_bias",
    "game_script_bias",
    "context_multipliers",
    "compute_baseline",
    "compute_context",
    "final_projection",
    "compute_player_baseline",
    "compute_player_context_multiplier",
    "compute_player_projections",
    "shrinkage_calibration",
    "cap_calibration",
    "isotonic_calibration",
    "calibrate_probability",
    "should_apply_calibration",
]
