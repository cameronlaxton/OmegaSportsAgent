"""
Calibration Engine

Implements the core calibration logic for the Validator-Lab:
- Expected Calibration Error (ECE)
- Brier Score calculation
- Reliability curves
- Calibration factor generation

This module is the analytical heart of the Predict-Grade-Tune loop.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

from src.modeling.probability_calibration import (
    shrinkage_calibration,
    isotonic_calibration
)


@dataclass
class CalibrationBin:
    """Represents a single confidence bin for calibration analysis."""
    bin_name: str
    lower_bound: float
    upper_bound: float
    predictions: List[float] = field(default_factory=list)
    outcomes: List[float] = field(default_factory=list)  # 1.0 = success, 0.0 = failure

    @property
    def count(self) -> int:
        return len(self.predictions)

    @property
    def mean_predicted(self) -> float:
        if not self.predictions:
            return 0.0
        return sum(self.predictions) / len(self.predictions)

    @property
    def mean_actual(self) -> float:
        if not self.outcomes:
            return 0.0
        return sum(self.outcomes) / len(self.outcomes)

    @property
    def calibration_error(self) -> float:
        """Absolute difference between predicted and actual."""
        return abs(self.mean_predicted - self.mean_actual)

    @property
    def calibration_factor(self) -> float:
        """
        Factor to multiply raw probabilities by to achieve calibration.

        If we predict 70% but only hit 60%, factor = 60/70 = 0.857
        This means our 70% predictions should be treated as 60%.
        """
        if self.mean_predicted == 0:
            return 1.0
        return self.mean_actual / self.mean_predicted

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bin": self.bin_name,
            "lower": self.lower_bound,
            "upper": self.upper_bound,
            "count": self.count,
            "mean_predicted": round(self.mean_predicted, 4),
            "mean_actual": round(self.mean_actual, 4),
            "calibration_error": round(self.calibration_error, 4),
            "calibration_factor": round(self.calibration_factor, 4)
        }


@dataclass
class CalibrationResult:
    """Complete calibration analysis result."""
    n_predictions: int
    n_resolved: int
    brier_score: float
    log_loss: float
    ece: float  # Expected Calibration Error
    mce: float  # Maximum Calibration Error
    hit_rate: float
    roi: Optional[float]
    bins: List[CalibrationBin]
    calibration_factors: Dict[str, float]
    reliability_curve: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_predictions": self.n_predictions,
            "n_resolved": self.n_resolved,
            "brier_score": round(self.brier_score, 4),
            "log_loss": round(self.log_loss, 4),
            "ece": round(self.ece, 4),
            "mce": round(self.mce, 4),
            "hit_rate": round(self.hit_rate, 4),
            "roi": round(self.roi, 4) if self.roi is not None else None,
            "calibration_factors": {k: round(v, 4) for k, v in self.calibration_factors.items()},
            "reliability_curve": self.reliability_curve
        }


class CalibrationEngine:
    """
    Engine for computing calibration metrics and reliability curves.

    The engine groups predictions by confidence bins and calculates
    how well predicted probabilities match actual outcomes.

    Usage:
        engine = CalibrationEngine(bin_width=0.05)
        engine.add_prediction(predicted_prob=0.65, outcome=1.0)
        engine.add_prediction(predicted_prob=0.72, outcome=0.0)
        result = engine.compute_calibration()
    """

    # Default bin boundaries (5% intervals from 50% to 95%)
    DEFAULT_BINS = [
        ("50-55", 0.50, 0.55),
        ("55-60", 0.55, 0.60),
        ("60-65", 0.60, 0.65),
        ("65-70", 0.65, 0.70),
        ("70-75", 0.70, 0.75),
        ("75-80", 0.75, 0.80),
        ("80-85", 0.80, 0.85),
        ("85-90", 0.85, 0.90),
        ("90-95", 0.90, 0.95),
        ("95-100", 0.95, 1.00),
    ]

    def __init__(
        self,
        bin_width: float = 0.05,
        min_bin_count: int = 10,
        custom_bins: Optional[List[Tuple[str, float, float]]] = None
    ):
        """
        Initialize the calibration engine.

        Args:
            bin_width: Width of confidence bins (default 5%)
            min_bin_count: Minimum samples per bin for valid calibration
            custom_bins: Optional custom bin definitions
        """
        self.bin_width = bin_width
        self.min_bin_count = min_bin_count

        # Initialize bins
        bin_defs = custom_bins if custom_bins else self.DEFAULT_BINS
        self.bins: Dict[str, CalibrationBin] = {}
        for name, lower, upper in bin_defs:
            self.bins[name] = CalibrationBin(
                bin_name=name,
                lower_bound=lower,
                upper_bound=upper
            )

        # Raw data storage for aggregate metrics
        self._predictions: List[float] = []
        self._outcomes: List[float] = []
        self._edges: List[float] = []
        self._profits: List[float] = []

    def reset(self) -> None:
        """Clear all stored predictions."""
        for bin_obj in self.bins.values():
            bin_obj.predictions.clear()
            bin_obj.outcomes.clear()
        self._predictions.clear()
        self._outcomes.clear()
        self._edges.clear()
        self._profits.clear()

    def add_prediction(
        self,
        predicted_prob: float,
        outcome: float,
        edge_pct: Optional[float] = None,
        profit: Optional[float] = None
    ) -> None:
        """
        Add a single prediction-outcome pair.

        Args:
            predicted_prob: Model's predicted probability (0.0 to 1.0)
            outcome: Actual outcome (1.0 = success, 0.0 = failure)
            edge_pct: Optional edge percentage for ROI calculation
            profit: Optional profit/loss in units
        """
        # Normalize probability to [0, 1]
        predicted_prob = max(0.0, min(1.0, predicted_prob))

        # Store raw data
        self._predictions.append(predicted_prob)
        self._outcomes.append(outcome)
        if edge_pct is not None:
            self._edges.append(edge_pct)
        if profit is not None:
            self._profits.append(profit)

        # Assign to appropriate bin
        for bin_obj in self.bins.values():
            if bin_obj.lower_bound <= predicted_prob < bin_obj.upper_bound:
                bin_obj.predictions.append(predicted_prob)
                bin_obj.outcomes.append(outcome)
                break
        else:
            # Handle edge case of probability = 1.0
            if predicted_prob >= 0.95:
                self.bins["95-100"].predictions.append(predicted_prob)
                self.bins["95-100"].outcomes.append(outcome)

    def add_predictions_batch(
        self,
        records: List[Dict[str, Any]]
    ) -> int:
        """
        Add multiple predictions from a list of records.

        Args:
            records: List of dicts with keys:
                - predicted_prob (required)
                - outcome (required)
                - edge_pct (optional)
                - profit (optional)

        Returns:
            Number of valid records added
        """
        added = 0
        for record in records:
            prob = record.get("predicted_prob")
            outcome = record.get("outcome")

            if prob is None or outcome is None:
                continue

            self.add_prediction(
                predicted_prob=prob,
                outcome=outcome,
                edge_pct=record.get("edge_pct"),
                profit=record.get("profit")
            )
            added += 1

        return added

    def compute_brier_score(self) -> float:
        """
        Calculate Brier Score (mean squared error of probabilities).

        Brier Score = (1/N) * Σ(predicted - outcome)²

        Lower is better. Range [0, 1].
        - 0.0 = perfect calibration
        - 0.25 = random guessing (for binary outcomes)
        """
        if not self._predictions:
            return 0.0

        squared_errors = [
            (p - o) ** 2
            for p, o in zip(self._predictions, self._outcomes)
        ]
        return sum(squared_errors) / len(squared_errors)

    def compute_log_loss(self) -> float:
        """
        Calculate Log Loss (cross-entropy loss).

        Log Loss = -(1/N) * Σ[y*log(p) + (1-y)*log(1-p)]

        Lower is better. Penalizes confident wrong predictions heavily.
        """
        if not self._predictions:
            return 0.0

        epsilon = 1e-15  # Prevent log(0)
        total_loss = 0.0

        for p, y in zip(self._predictions, self._outcomes):
            p = max(epsilon, min(1 - epsilon, p))
            if y == 1.0:
                total_loss -= math.log(p)
            else:
                total_loss -= math.log(1 - p)

        return total_loss / len(self._predictions)

    def compute_ece(self) -> float:
        """
        Calculate Expected Calibration Error.

        ECE = Σ (n_bin / N) * |accuracy_bin - confidence_bin|

        Weighted average of calibration errors across bins.
        """
        if not self._predictions:
            return 0.0

        total_samples = len(self._predictions)
        weighted_error = 0.0

        for bin_obj in self.bins.values():
            if bin_obj.count >= self.min_bin_count:
                weight = bin_obj.count / total_samples
                weighted_error += weight * bin_obj.calibration_error

        return weighted_error

    def compute_mce(self) -> float:
        """
        Calculate Maximum Calibration Error.

        MCE = max(|accuracy_bin - confidence_bin|) across all bins

        Identifies the worst-calibrated confidence region.
        """
        max_error = 0.0

        for bin_obj in self.bins.values():
            if bin_obj.count >= self.min_bin_count:
                max_error = max(max_error, bin_obj.calibration_error)

        return max_error

    def compute_reliability_curve(self) -> List[Dict[str, Any]]:
        """
        Generate the reliability curve (calibration plot data).

        Returns list of points for plotting predicted vs actual accuracy.
        """
        curve = []

        for bin_obj in self.bins.values():
            if bin_obj.count >= self.min_bin_count:
                curve.append(bin_obj.to_dict())

        return sorted(curve, key=lambda x: x["lower"])

    def compute_calibration_factors(self) -> Dict[str, float]:
        """
        Generate calibration factors for each confidence bin.

        These factors can be applied to future predictions to correct
        systematic biases.

        Returns:
            Dict mapping bin names to calibration factors.
            Factor < 1.0 means we're overconfident in that range.
            Factor > 1.0 means we're underconfident.
        """
        factors = {}

        for bin_name, bin_obj in self.bins.items():
            if bin_obj.count >= self.min_bin_count:
                factors[bin_name] = bin_obj.calibration_factor
            else:
                # Not enough data, use neutral factor
                factors[bin_name] = 1.0

        return factors

    def compute_hit_rate(self) -> float:
        """Calculate overall hit rate (accuracy)."""
        if not self._outcomes:
            return 0.0
        return sum(self._outcomes) / len(self._outcomes)

    def compute_roi(self) -> Optional[float]:
        """Calculate ROI from profit data if available."""
        if not self._profits:
            return None
        return sum(self._profits) / len(self._profits)

    def compute_calibration(self) -> CalibrationResult:
        """
        Run full calibration analysis.

        Returns:
            CalibrationResult with all metrics and recommendations.
        """
        n_predictions = len(self._predictions)
        n_resolved = sum(1 for o in self._outcomes if o is not None)

        return CalibrationResult(
            n_predictions=n_predictions,
            n_resolved=n_resolved,
            brier_score=self.compute_brier_score(),
            log_loss=self.compute_log_loss(),
            ece=self.compute_ece(),
            mce=self.compute_mce(),
            hit_rate=self.compute_hit_rate(),
            roi=self.compute_roi(),
            bins=list(self.bins.values()),
            calibration_factors=self.compute_calibration_factors(),
            reliability_curve=self.compute_reliability_curve()
        )

    def generate_isotonic_map(self) -> Dict[float, float]:
        """
        Generate an isotonic calibration map from current data.

        This map can be used with isotonic_calibration() to transform
        raw probabilities into calibrated ones.
        """
        calibration_map = {}

        for bin_obj in sorted(self.bins.values(), key=lambda b: b.lower_bound):
            if bin_obj.count >= self.min_bin_count:
                # Map bin midpoint to actual hit rate
                midpoint = (bin_obj.lower_bound + bin_obj.upper_bound) / 2
                calibration_map[midpoint] = bin_obj.mean_actual

        # Ensure monotonicity (isotonic property)
        sorted_points = sorted(calibration_map.items())
        isotonic_map = {}
        prev_value = 0.0

        for prob, actual in sorted_points:
            # Enforce non-decreasing
            calibrated = max(prev_value, actual)
            isotonic_map[prob] = calibrated
            prev_value = calibrated

        return isotonic_map

    def apply_calibration(
        self,
        raw_prob: float,
        method: str = "factor"
    ) -> float:
        """
        Apply learned calibration to a new probability.

        Args:
            raw_prob: Raw model probability
            method: "factor" (multiply by bin factor) or "isotonic" (use mapping)

        Returns:
            Calibrated probability
        """
        if method == "isotonic":
            isotonic_map = self.generate_isotonic_map()
            return isotonic_calibration(raw_prob, isotonic_map)

        # Factor method: find appropriate bin and apply factor
        factors = self.compute_calibration_factors()

        for bin_name, bin_obj in self.bins.items():
            if bin_obj.lower_bound <= raw_prob < bin_obj.upper_bound:
                factor = factors.get(bin_name, 1.0)
                # Apply factor but keep probability in [0.05, 0.95] range
                calibrated = raw_prob * factor
                return max(0.05, min(0.95, calibrated))

        return raw_prob


def compute_single_brier(predicted_prob: float, outcome: float) -> float:
    """
    Compute Brier score for a single prediction.

    Args:
        predicted_prob: Predicted probability (0-1)
        outcome: Actual outcome (0 or 1)

    Returns:
        Squared error (0-1)
    """
    return (predicted_prob - outcome) ** 2


def compute_percentile_rank(
    actual_value: float,
    predicted_mean: float,
    predicted_std: float
) -> float:
    """
    Calculate where the actual value falls in the predicted distribution.

    Uses normal distribution CDF approximation.

    Args:
        actual_value: The actual outcome value
        predicted_mean: Predicted mean from simulation
        predicted_std: Predicted standard deviation

    Returns:
        Percentile rank (0-1). 0.5 means actual was at predicted mean.
    """
    if predicted_std <= 0:
        return 0.5 if actual_value == predicted_mean else (1.0 if actual_value > predicted_mean else 0.0)

    # Z-score
    z = (actual_value - predicted_mean) / predicted_std

    # Standard normal CDF approximation (Abramowitz and Stegun)
    def norm_cdf(x: float) -> float:
        a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
        p = 0.3275911
        sign = 1 if x >= 0 else -1
        x = abs(x)
        t = 1.0 / (1.0 + p * x)
        y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x / 2)
        return 0.5 * (1.0 + sign * y)

    return norm_cdf(z)


def grade_prediction(
    prediction_payload: Dict[str, Any],
    outcome_payload: Dict[str, Any],
    market_payload: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Grade a single prediction against its outcome.

    This is the core grading function used by the calibration loop.

    Args:
        prediction_payload: Full prediction distribution from simulation
        outcome_payload: Actual outcome data
        market_payload: Optional market odds at prediction time

    Returns:
        Dict with calibration metrics for this prediction
    """
    metrics = {}

    # Extract predicted probability based on market type
    dist_type = prediction_payload.get("dist", "bernoulli")

    if "win_prob" in prediction_payload:
        # Moneyline
        predicted_prob = prediction_payload["win_prob"]
        outcome = 1.0 if outcome_payload.get("winner") == prediction_payload.get("selection") else 0.0

    elif "cover_prob" in prediction_payload:
        # Spread
        predicted_prob = prediction_payload["cover_prob"]
        outcome = 1.0 if outcome_payload.get("covered") else 0.0

    elif "over_prob" in prediction_payload or "under_prob" in prediction_payload:
        # Total or Player Prop
        selection = prediction_payload.get("selection", "over")
        predicted_prob = prediction_payload.get(f"{selection}_prob", 0.5)
        outcome = 1.0 if outcome_payload.get("hit") else 0.0

    else:
        # Fallback
        predicted_prob = 0.5
        outcome = 1.0 if outcome_payload.get("success") else 0.0

    # Brier Score
    metrics["brier_score"] = compute_single_brier(predicted_prob, outcome)

    # Log Loss component
    epsilon = 1e-15
    p = max(epsilon, min(1 - epsilon, predicted_prob))
    if outcome == 1.0:
        metrics["log_loss"] = -math.log(p)
    else:
        metrics["log_loss"] = -math.log(1 - p)

    # Confidence bin
    bin_lower = int(predicted_prob * 20) * 5  # 5% bins
    bin_upper = bin_lower + 5
    metrics["confidence_bin"] = f"{bin_lower}-{bin_upper}"

    # Percentile rank (for continuous predictions)
    if "mean" in prediction_payload and "std" in prediction_payload:
        actual_value = outcome_payload.get("actual_value")
        if actual_value is not None:
            metrics["percentile_rank"] = compute_percentile_rank(
                actual_value,
                prediction_payload["mean"],
                prediction_payload["std"]
            )

    # Edge realized
    if market_payload and "implied_prob" in market_payload:
        edge = predicted_prob - market_payload["implied_prob"]
        metrics["edge_pct"] = round(edge * 100, 2)
        metrics["edge_realized"] = (edge > 0 and outcome == 1.0) or (edge < 0 and outcome == 0.0)

    # CLV (Closing Line Value) if available
    if market_payload and "closing_prob" in market_payload:
        clv = market_payload["closing_prob"] - market_payload["implied_prob"]
        metrics["clv"] = round(clv, 4)

    metrics["outcome"] = outcome
    metrics["predicted_prob"] = predicted_prob

    return metrics
