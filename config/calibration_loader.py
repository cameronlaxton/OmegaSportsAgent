"""
Calibration Pack Loader Module

Loads league-specific calibration packs from config/calibration/ directory.
Provides safe fallback defaults and exposes calibration parameters via getters.

Calibration packs contain:
- Edge thresholds by market type
- Kelly fraction and staking policy
- Probability transforms (Platt scaling, shrinkage)
- Version metadata

Usage Example:
    from config.calibration_loader import CalibrationLoader
    
    # Load NBA calibration
    cal = CalibrationLoader("NBA")
    
    # Get parameters
    edge_threshold = cal.get_edge_threshold("moneyline")
    kelly_frac = cal.get_kelly_fraction()
    transform = cal.get_probability_transform("moneyline")
    
    # Apply transform to probability
    if transform:
        adjusted_prob = transform(model_prob)
"""

from __future__ import annotations
import json
import os
import logging
from typing import Dict, List, Optional, Any, Callable


logger = logging.getLogger(__name__)


# Default fallback values if calibration pack is missing
DEFAULT_EDGE_THRESHOLDS = {
    "moneyline": 0.04,
    "spread": 0.04,
    "total": 0.04,
    "player_prop_points": 0.05,
    "player_prop_rebounds": 0.05,
    "player_prop_assists": 0.05,
    "player_prop_receiving_yards": 0.05,
    "player_prop_passing_yards": 0.05,
    "default": 0.04
}

DEFAULT_KELLY_FRACTION = 0.25
DEFAULT_KELLY_POLICY = "quarter_kelly"


def _get_calibration_dir() -> str:
    """
    Get the calibration directory path.
    
    Returns:
        Path to config/calibration directory
    """
    # Navigate from config/ to config/calibration/
    base_dir = os.path.dirname(__file__)
    cal_dir = os.path.join(base_dir, "calibration")
    os.makedirs(cal_dir, exist_ok=True)
    return cal_dir


def _load_calibration_pack(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Load calibration pack from JSON file.
    
    Args:
        filepath: Path to calibration pack JSON
    
    Returns:
        Calibration pack data or None if load fails
    """
    if not os.path.exists(filepath):
        return None
    
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to load calibration pack from {filepath}: {e}")
        return None


def _create_platt_transform(platt_params: Dict[str, float]) -> Callable[[float], float]:
    """
    Create Platt scaling transform function.
    
    Platt scaling: adjusted_prob = 1 / (1 + exp(A * logit(prob) + B))
    
    Args:
        platt_params: Dict with 'a'/'A' and 'b'/'B' coefficients
    
    Returns:
        Transform function
    """
    # Support both uppercase and lowercase parameter names
    A = platt_params.get("a", platt_params.get("A", 1.0))
    B = platt_params.get("b", platt_params.get("B", 0.0))
    
    def transform(prob: float) -> float:
        import math
        # Clamp probability to valid range
        prob = max(0.01, min(0.99, prob))
        # Logit transform
        logit = math.log(prob / (1 - prob))
        # Apply Platt scaling
        scaled_logit = A * logit + B
        # Convert back to probability
        adjusted = 1.0 / (1.0 + math.exp(-scaled_logit))
        return max(0.01, min(0.99, adjusted))
    
    return transform


def _create_shrink_transform(shrink_params: Dict[str, float]) -> Callable[[float], float]:
    """
    Create shrinkage transform function.
    
    Shrinkage: adjusted_prob = 0.5 + (prob - 0.5) * shrink_factor
    
    Args:
        shrink_params: Dict with 'factor' (0.0 to 1.0)
    
    Returns:
        Transform function
    """
    factor = shrink_params.get("factor", 0.625)
    
    def transform(prob: float) -> float:
        # Shrink toward 0.5
        adjusted = 0.5 + (prob - 0.5) * factor
        return max(0.01, min(0.99, adjusted))
    
    return transform


def _create_combined_transform(transforms: List[Dict[str, Any]]) -> Callable[[float], float]:
    """
    Create combined transform by chaining multiple transforms.
    
    Args:
        transforms: List of transform definitions
    
    Returns:
        Combined transform function
    """
    transform_funcs = []
    
    for t in transforms:
        t_type = t.get("type", "").lower()
        t_params = t.get("params", {})
        
        if t_type == "platt":
            transform_funcs.append(_create_platt_transform(t_params))
        elif t_type == "shrink":
            transform_funcs.append(_create_shrink_transform(t_params))
        else:
            logger.warning(f"Unknown transform type: {t_type}")
    
    def combined(prob: float) -> float:
        result = prob
        for func in transform_funcs:
            result = func(result)
        return result
    
    return combined if transform_funcs else lambda p: p


class CalibrationLoader:
    """
    Loads and provides access to league-specific calibration parameters.
    
    Supports:
    - Edge thresholds by market type
    - Kelly fraction and staking policy
    - Probability transforms (Platt, shrinkage)
    - Version tracking
    
    Falls back to safe defaults if calibration pack is missing.
    """
    
    def __init__(self, league: str, pack_name: Optional[str] = None):
        """
        Initialize calibration loader for a league.
        
        Args:
            league: League identifier (NBA, NFL, NCAAB, NCAAF, etc.)
            pack_name: Optional specific pack name (default: {league}_latest.json)
        """
        self.league = league.upper()
        
        # Determine pack filename
        if pack_name is None:
            pack_name = f"{self.league.lower()}_latest.json"
        
        # Load calibration pack
        cal_dir = _get_calibration_dir()
        filepath = os.path.join(cal_dir, pack_name)
        
        self.pack = _load_calibration_pack(filepath)
        self.pack_name = pack_name
        self.pack_filepath = filepath
        
        if self.pack:
            logger.info(f"Loaded calibration pack: {pack_name} (version: {self.get_version()})")
        else:
            logger.warning(f"Calibration pack not found: {pack_name}. Using defaults.")
        
        # Cache transforms
        self._transforms_cache: Dict[str, Optional[Callable]] = {}
    
    def get_version(self) -> str:
        """
        Get calibration pack version.
        
        Returns:
            Version string (e.g., "v1.0" or "default" if using fallback)
        """
        if self.pack:
            return self.pack.get("version", "unknown")
        return "default"
    
    def get_edge_threshold(self, market_type: str, default: float = 0.04) -> float:
        """
        Get edge threshold for a market type.
        
        Args:
            market_type: Market type (moneyline, spread, total, player_prop_*, etc.)
            default: Default threshold if not found
        
        Returns:
            Edge threshold (e.g., 0.04 for 4%)
        """
        if self.pack:
            thresholds = self.pack.get("edge_thresholds", {})
            # Try exact match first
            if market_type in thresholds:
                return thresholds[market_type]
            # Try default
            if "default" in thresholds:
                return thresholds["default"]
        
        # Fallback to defaults
        return DEFAULT_EDGE_THRESHOLDS.get(market_type, DEFAULT_EDGE_THRESHOLDS.get("default", default))
    
    def get_kelly_fraction(self) -> float:
        """
        Get Kelly fraction for staking.
        
        Returns:
            Kelly fraction (e.g., 0.25 for quarter-Kelly)
        """
        if self.pack:
            return self.pack.get("kelly_fraction", DEFAULT_KELLY_FRACTION)
        return DEFAULT_KELLY_FRACTION
    
    def get_kelly_policy(self) -> str:
        """
        Get Kelly staking policy.
        
        Returns:
            Policy name (e.g., "quarter_kelly", "half_kelly")
        """
        if self.pack:
            return self.pack.get("kelly_policy", DEFAULT_KELLY_POLICY)
        return DEFAULT_KELLY_POLICY
    
    def get_probability_transform(self, market_type: str) -> Optional[Callable[[float], float]]:
        """
        Get probability transform function for a market type.
        
        Returns a callable that transforms model probabilities.
        
        Args:
            market_type: Market type (moneyline, spread, total, player_prop_*, etc.)
        
        Returns:
            Transform function or None if no transform defined
        """
        # Check cache
        if market_type in self._transforms_cache:
            return self._transforms_cache[market_type]
        
        if not self.pack:
            self._transforms_cache[market_type] = None
            return None
        
        transforms_config = self.pack.get("probability_transforms", {})
        
        # Try exact match first
        if market_type in transforms_config:
            transform_list = transforms_config[market_type]
        elif "default" in transforms_config:
            transform_list = transforms_config["default"]
        else:
            self._transforms_cache[market_type] = None
            return None
        
        # Create transform function
        if isinstance(transform_list, list) and len(transform_list) > 0:
            transform_func = _create_combined_transform(transform_list)
            self._transforms_cache[market_type] = transform_func
            return transform_func
        
        self._transforms_cache[market_type] = None
        return None
    
    def get_probability_transforms(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all probability transforms configuration.
        
        Returns:
            Dict mapping market types to transform definitions
        """
        if self.pack:
            return self.pack.get("probability_transforms", {})
        return {}
    
    def get_kelly_staking(self) -> Dict[str, Any]:
        """
        Get Kelly staking configuration.
        
        Returns:
            Dict with kelly_staking parameters (method, fraction, max_stake, min_stake, tier_multipliers)
        """
        if self.pack and "kelly_staking" in self.pack:
            return self.pack["kelly_staking"]
        
        # Fallback to basic kelly configuration
        return {
            "method": "fractional",
            "fraction": self.get_kelly_fraction(),
            "max_stake": 0.05,
            "min_stake": 0.01,
            "tier_multipliers": {
                "high_confidence": 1.0,
                "medium_confidence": 0.5,
                "low_confidence": 0.25
            }
        }
    
    def get_variance_scalars(self) -> Dict[str, float]:
        """
        Get variance scalars for leagues.
        
        Returns:
            Dict mapping league names to variance scalar multipliers
        """
        if self.pack and "variance_scalars" in self.pack:
            return self.pack["variance_scalars"]
        
        # Fallback defaults
        return {
            "NBA": 1.0,
            "NFL": 1.0,
            "global": 1.0
        }
    
    def get_test_performance(self) -> Optional[Dict[str, Any]]:
        """
        Get test performance metrics from calibration.
        
        Returns:
            Dict with test performance metrics or None if not available
        """
        if self.pack and "test_performance" in self.pack:
            return self.pack["test_performance"]
        return None
    
    def get_raw_pack(self) -> Optional[Dict[str, Any]]:
        """
        Get the raw calibration pack data.
        
        Returns:
            Full calibration pack dict or None if using defaults
        """
        return self.pack
    
    def is_using_defaults(self) -> bool:
        """
        Check if using default fallback values.
        
        Returns:
            True if no calibration pack loaded
        """
        return self.pack is None
