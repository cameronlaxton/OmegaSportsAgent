"""
Model and simulation configuration.

Provides default thresholds and simulation parameters. These can later
be backed by config/settings.yaml; for now, sensible defaults.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def get_edge_thresholds() -> Dict[str, float]:
    """Return edge threshold tiers for filtering actionable bets."""
    return {
        "low": 0.03,
        "mid": 0.05,
        "high": 0.08,
    }


def get_simulation_params(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return default simulation parameters, merged with any overrides."""
    defaults: Dict[str, Any] = {
        "n_iterations": 1000,
        "seed": None,
        "calibration_method": "combined",
        "shrink_factor": 0.7,
        "cap_max": 0.9,
        "cap_min": 0.1,
    }
    if overrides:
        defaults.update(overrides)
    return defaults
