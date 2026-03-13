"""
Calibration Loader — reads calibration packs from config/calibration/.

Provides edge thresholds, Kelly parameters, and probability transforms
for each league from JSON calibration pack files.
"""

from __future__ import annotations

import json
import math
import os
from typing import Any, Callable, Dict, List, Optional

# Config directory is at project root config/calibration/
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CAL_DIR = os.path.join(_PROJECT_ROOT, "config", "calibration")
_UNIVERSAL_PACK = os.path.join(_CAL_DIR, "universal_latest.json")


def _platt_transform(a: float, b: float) -> Callable[[float], float]:
    """Return a Platt-scaling transform: 1 / (1 + exp(a*x + b))."""
    def transform(p: float) -> float:
        z = a * p + b
        return 1.0 / (1.0 + math.exp(-z))
    return transform


def _shrink_transform(factor: float) -> Callable[[float], float]:
    """Shrink probability toward 0.5 by *factor*."""
    def transform(p: float) -> float:
        return 0.5 + factor * (p - 0.5)
    return transform


def _build_transform_fn(steps: List[Dict[str, Any]]) -> Callable[[float], float]:
    """Chain a list of transform step dicts into a single callable."""
    fns: List[Callable[[float], float]] = []
    for step in steps:
        t = step.get("type")
        params = step.get("params", {})
        if t == "platt":
            fns.append(_platt_transform(params["a"], params["b"]))
        elif t == "shrink":
            fns.append(_shrink_transform(params["factor"]))

    def chained(p: float) -> float:
        for fn in fns:
            p = fn(p)
        return max(0.0, min(1.0, p))

    return chained


class CalibrationLoader:
    """Load calibration parameters for a league from JSON pack files."""

    def __init__(self, league: str) -> None:
        self.league = league.upper()
        self.pack_name: Optional[str] = None
        self._data: Dict[str, Any] = {}
        self._league_data: Dict[str, Any] = {}
        self._using_defaults = True

        self._load()

    # ------------------------------------------------------------------
    def _load(self) -> None:
        # Try league-specific pack first, then universal
        league_pack = os.path.join(_CAL_DIR, f"{self.league.lower()}_latest.json")
        if os.path.exists(league_pack):
            with open(league_pack, "r", encoding="utf-8") as f:
                self._data = json.load(f)
            self.pack_name = self._data.get("version", self.league)
            self._league_data = self._data
            self._using_defaults = False
        elif os.path.exists(_UNIVERSAL_PACK):
            with open(_UNIVERSAL_PACK, "r", encoding="utf-8") as f:
                self._data = json.load(f)
            self.pack_name = self._data.get("version", "universal")
            # Prefer league-specific overrides inside universal pack
            self._league_data = self._data.get("leagues", {}).get(self.league, {})
            self._using_defaults = not bool(self._league_data)
        else:
            self._data = {}
            self._league_data = {}
            self._using_defaults = True

    # ------------------------------------------------------------------
    def is_using_defaults(self) -> bool:
        return self._using_defaults

    def get_version(self) -> str:
        return self._league_data.get("version", self._data.get("version", "default"))

    # ------------------------------------------------------------------
    # Edge thresholds
    # ------------------------------------------------------------------
    def get_edge_threshold(self, market_type: str) -> float:
        thresholds = self._league_data.get("edge_thresholds", self._data.get("edge_thresholds", {}))
        if market_type in thresholds:
            return thresholds[market_type]
        return thresholds.get("default", 0.03)

    # ------------------------------------------------------------------
    # Kelly parameters
    # ------------------------------------------------------------------
    def get_kelly_fraction(self) -> float:
        return self._league_data.get("kelly_fraction", self._data.get("kelly_fraction", 0.25))

    def get_kelly_policy(self) -> str:
        return self._league_data.get("kelly_policy", self._data.get("kelly_policy", "quarter_kelly"))

    # ------------------------------------------------------------------
    # Probability transforms
    # ------------------------------------------------------------------
    def get_probability_transform(self, market_type: str) -> Optional[Callable[[float], float]]:
        transforms = self._league_data.get("probability_transforms", self._data.get("probability_transforms", {}))
        steps = transforms.get(market_type, transforms.get("default"))
        if steps:
            return _build_transform_fn(steps)
        return None

    def get_probability_transforms(self) -> Dict[str, List[Dict[str, Any]]]:
        return self._league_data.get("probability_transforms", self._data.get("probability_transforms", {}))
