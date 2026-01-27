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

from src.validation.probability_calibration import (
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
        """
        Number of predictions assigned to this calibration bin.
        
        Returns:
            int: The count of predictions in the bin.
        """
        return len(self.predictions)

    @property
    def mean_predicted(self) -> float:
        """
        Compute the mean predicted probability for this calibration bin.
        
        Returns:
            The average of stored predicted probabilities for the bin, or 0.0 if the bin has no predictions.
        """
        if not self.predictions:
            return 0.0
        return sum(self.predictions) / len(self.predictions)

    @property
    def mean_actual(self) -> float:
        """
        Compute the average actual outcome for this bin.
        
        Returns:
            float: Mean of the stored outcomes; 0.0 if the bin contains no outcomes.
        """
        if not self.outcomes:
            return 0.0
        return sum(self.outcomes) / len(self.outcomes)

    @property
    def calibration_error(self) -> float:
        """
        Absolute calibration error for the bin.
        
        Returns:
            error (float): Absolute difference between the bin's mean predicted probability and the bin's mean actual outcome.
        """
        return abs(self.mean_predicted - self.mean_actual)

    @property
    def calibration_factor(self) -> float:
        """
        Compute the multiplicative calibration factor for this bin as the ratio of observed frequency to predicted probability.
        
        Returns:
            float: The scaling factor equal to mean_actual / mean_predicted; returns 1.0 if mean_predicted is 0.
        """
        if self.mean_predicted == 0:
            return 1.0
        return self.mean_actual / self.mean_predicted

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize this CalibrationBin's statistics to a dictionary suitable for reporting or JSON export.
        
        Returns:
            dict: Mapping with keys:
                - "bin" (str): bin name.
                - "lower" (float): lower bound of the bin.
                - "upper" (float): upper bound of the bin.
                - "count" (int): number of samples in the bin.
                - "mean_predicted" (float): mean predicted probability rounded to 4 decimals.
                - "mean_actual" (float): mean actual outcome rounded to 4 decimals.
                - "calibration_error" (float): absolute difference between means rounded to 4 decimals.
                - "calibration_factor" (float): ratio of mean_actual to mean_predicted (or 1.0 if mean_predicted is 0) rounded to 4 decimals.
        """
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
        """
        Serialize the calibration result into a dictionary with rounded numeric metrics suitable for JSON output.
        
        Returns:
            A dictionary containing:
            - n_predictions: total number of predictions analyzed.
            - n_resolved: number of predictions with observed outcomes.
            - brier_score: Brier score rounded to 4 decimals.
            - log_loss: Log loss rounded to 4 decimals.
            - ece: Expected Calibration Error rounded to 4 decimals.
            - mce: Maximum Calibration Error rounded to 4 decimals.
            - hit_rate: Overall hit rate rounded to 4 decimals.
            - roi: Average profit per prediction rounded to 4 decimals, or `None` if not available.
            - calibration_factors: mapping of bin name to calibration factor, each rounded to 4 decimals.
            - reliability_curve: raw reliability curve data (not rounded).
        """
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
        Create a CalibrationEngine configured with binning and minimum-sample thresholds.
        
        Parameters:
        	bin_width (float): Width of bins as a fraction (e.g., 0.05 for 5% bins).
        	min_bin_count (int): Minimum number of samples required for a bin to be considered valid in calibration metrics.
        	custom_bins (Optional[List[Tuple[str, float, float]]]): Optional list of custom bins as (name, lower_bound, upper_bound). If provided, these override the engine's default bin definitions.
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
        """
        Reset the engine's stored data and clear all bins.
        
        Clears per-bin predictions and outcomes and empties internal raw storage for predictions, outcomes, edge percentages, and profits.
        """
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
        Record a single predicted probability with its actual outcome and optional financial metrics.
        
        Parameters:
            predicted_prob (float): Model's predicted probability; will be clamped to the range [0.0, 1.0] before storage.
            outcome (float): Actual outcome (1.0 = success, 0.0 = failure).
            edge_pct (Optional[float]): Optional edge percentage used for ROI/edge analyses.
            profit (Optional[float]): Optional profit or loss associated with the prediction.
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
        Add multiple prediction records to the engine by delegating each valid record to add_prediction.
        
        Parameters:
            records (List[Dict[str, Any]]): List of records where each must include 'predicted_prob' and 'outcome'. Optional keys: 'edge_pct', 'profit'.
        
        Returns:
            int: Number of records successfully added.
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
        Compute the Brier score for the stored predictions.
        
        Returns:
            float: Mean squared error between predicted probabilities and actual outcomes; returns 0.0 if no predictions are available.
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
        Compute the average log loss (cross-entropy) over stored predictions.
        
        Computes - (1/N) * sum[y*log(p) + (1-y)*log(1-p)] with clamping to avoid log(0).
        Lower values indicate better probabilistic calibration; confident wrong predictions are penalized heavily.
        
        Returns:
        	Average log loss across all stored predictions; returns 0.0 if no predictions have been added.
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
        Compute the Expected Calibration Error (ECE) across bins.
        
        ECE is the weighted average of per-bin absolute calibration errors (|mean_actual - mean_predicted|),
        where each bin's weight is its fraction of total predictions. Only bins with at least
        min_bin_count samples contribute. Returns 0.0 if no predictions have been recorded.
        
        Returns:
            ece (float): Expected Calibration Error between 0.0 and 1.0.
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
        Compute the maximum calibration error across bins that meet the minimum sample requirement.
        
        Only bins with a count greater than or equal to self.min_bin_count are considered.
        
        Returns:
            max_error (float): The largest absolute difference between mean predicted probability and mean actual outcome among eligible bins; 0.0 if no bins qualify.
        """
        max_error = 0.0

        for bin_obj in self.bins.values():
            if bin_obj.count >= self.min_bin_count:
                max_error = max(max_error, bin_obj.calibration_error)

        return max_error

    def compute_reliability_curve(self) -> List[Dict[str, Any]]:
        """
        Builds reliability-curve data points from bins that meet the minimum sample count.
        
        Each list item is a dictionary of bin statistics (as returned by CalibrationBin.to_dict) suitable for plotting predicted probability versus observed frequency.
        
        Returns:
            List[Dict[str, Any]]: Bin dictionaries for bins with count >= self.min_bin_count, sorted by lower bound.
        """
        curve = []

        for bin_obj in self.bins.values():
            if bin_obj.count >= self.min_bin_count:
                curve.append(bin_obj.to_dict())

        return sorted(curve, key=lambda x: x["lower"])

    def compute_calibration_factors(self) -> Dict[str, float]:
        """
        Compute per-bin calibration factors to adjust future predicted probabilities.
        
        Bins with fewer than self.min_bin_count samples receive a neutral factor of 1.0.
        
        Returns:
            factors (Dict[str, float]): Mapping from bin name to calibration factor.
                Values less than 1.0 indicate overconfidence for that bin,
                values greater than 1.0 indicate underconfidence.
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
        """
        Compute the overall hit rate as the proportion of successful outcomes.
        
        Returns:
            float: Proportion of outcomes equal to 1.0 (range 0.0–1.0); returns 0.0 when there are no recorded outcomes.
        """
        if not self._outcomes:
            return 0.0
        return sum(self._outcomes) / len(self._outcomes)

    def compute_roi(self) -> Optional[float]:
        """
        Calculate the average profit per prediction from recorded profits.
        
        Returns:
            average_profit (Optional[float]): The mean of recorded profits, or `None` if no profit data is available.
        """
        if not self._profits:
            return None
        return sum(self._profits) / len(self._profits)

    def compute_calibration(self) -> CalibrationResult:
        """
        Produce a complete calibration analysis from the engine's collected predictions and outcomes.
        
        The result aggregates overall metrics (Brier score, log loss, Expected/Maximum Calibration Error, hit rate, ROI), per-bin statistics, per-bin calibration factors, and a reliability curve.
        
        Returns:
            CalibrationResult: Aggregated calibration metrics and per-bin data.
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
        Build an isotonic calibration mapping from bin midpoints to observed hit rates.
        
        Only bins with at least `min_bin_count` samples contribute; the returned mapping enforces non-decreasing (isotonic) calibrated values across midpoints.
        
        Returns:
            isotonic_map (Dict[float, float]): Mapping from bin midpoint (float) to calibrated observed probability (float), with values non-decreasing by midpoint.
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
        Apply a chosen calibration method to a single predicted probability.
        
        Parameters:
            raw_prob (float): The uncalibrated probability in [0.0, 1.0].
            method (str): Calibration method to apply; "factor" to scale by per-bin factors, "isotonic" to use an isotonic mapping.
        
        Returns:
            float: The calibrated probability. For the "factor" method the result is clamped to the range [0.05, 0.95]. For the "isotonic" method the isotonic mapping produced by the engine is used. If no bin matches the input probability when using the factor method, the original `raw_prob` is returned.
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
    Compute the Brier score (squared error) for a single probabilistic prediction.
    
    Parameters:
        predicted_prob (float): Predicted probability between 0 and 1.
        outcome (float): Actual outcome, 0.0 or 1.0.
    
    Returns:
        float: Squared error between the prediction and outcome (range 0 to 1).
    """
    return (predicted_prob - outcome) ** 2


def compute_percentile_rank(
    actual_value: float,
    predicted_mean: float,
    predicted_std: float
) -> float:
    """
    Compute the percentile rank of an actual value within a predicted normal distribution.
    
    Parameters:
        actual_value (float): Observed value to rank.
        predicted_mean (float): Mean of the predicted distribution.
        predicted_std (float): Standard deviation of the predicted distribution.
    
    Returns:
        float: Percentile rank in the range [0.0, 1.0]; 0.5 indicates the actual value equals the predicted mean.
        If `predicted_std` is less than or equal to 0, returns 0.5 when `actual_value == predicted_mean`,
        `1.0` when `actual_value > predicted_mean`, and `0.0` when `actual_value < predicted_mean`.
    """
    if predicted_std <= 0:
        return 0.5 if actual_value == predicted_mean else (1.0 if actual_value > predicted_mean else 0.0)

    # Z-score
    z = (actual_value - predicted_mean) / predicted_std

    # Standard normal CDF approximation (Abramowitz and Stegun)
    def norm_cdf(x: float) -> float:
        """
        Approximate the cumulative distribution function (CDF) of the standard normal distribution at x.
        
        Parameters:
            x (float): The z-score or value at which to evaluate the standard normal CDF.
        
        Returns:
            float: The CDF value in [0.0, 1.0].
        """
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
    Grade a single probabilistic prediction against its observed outcome and produce calibration metrics.
    
    Parameters:
        prediction_payload (dict): Prediction distribution and metadata. Recognized keys:
            - "win_prob", "cover_prob", "over_prob"/"under_prob": predicted probabilities for moneyline, spread, or totals/props.
            - "selection" (optional): chosen side for over/under or moneyline.
            - "mean", "std" (optional): distribution parameters for percentile rank calculations.
        outcome_payload (dict): Observed outcome data. Recognized keys include:
            - "winner", "covered", "hit", "success" for binary outcomes.
            - "actual_value" (optional) for continuous outcomes used with mean/std.
        market_payload (dict, optional): Market/odds information. Recognized keys:
            - "implied_prob" (optional): market implied probability at prediction time.
            - "closing_prob" (optional): closing market probability.
    
    Returns:
        dict: Metrics for the prediction containing:
            - "brier_score": squared error between predicted probability and outcome.
            - "log_loss": log loss for the observed outcome.
            - "confidence_bin": 5%-bucket label for the predicted probability (e.g., "50-55").
            - "percentile_rank" (optional): percentile of the actual value under the predicted normal distribution.
            - "edge_pct" (optional): percentage edge versus market implied probability (rounded).
            - "edge_realized" (optional): boolean indicating whether the edge produced a favorable outcome.
            - "clv" (optional): closing line value (rounded).
            - "outcome": binary outcome used for scoring (1.0 or 0.0).
            - "predicted_prob": the probability used for grading.
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
