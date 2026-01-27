"""
Calibration Tuner

Implements the feedback mechanism of the Predict-Grade-Tune loop.
Reads calibration results and updates config/league_calibrations.yaml
to correct systematic biases in the model.

This allows the engine to "learn" from its past mistakes automatically.
"""

from __future__ import annotations
import os
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from copy import deepcopy

try:
    import yaml
except ImportError:
    yaml = None

from src.validation.calibrator import CalibrationEngine, CalibrationResult

logger = logging.getLogger(__name__)


# Default path to calibration config
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "league_calibrations.yaml"
BACKUP_DIR = Path(__file__).parent.parent.parent / "config" / "calibration_backups"


@dataclass
class TuningRecommendation:
    """Recommendation for a single calibration parameter adjustment."""
    league: str
    parameter: str
    current_value: Any
    recommended_value: Any
    reason: str
    confidence: float  # 0-1, higher = more confident in recommendation
    sample_size: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "league": self.league,
            "parameter": self.parameter,
            "current": self.current_value,
            "recommended": self.recommended_value,
            "reason": self.reason,
            "confidence": round(self.confidence, 3),
            "sample_size": self.sample_size
        }


@dataclass
class TuningResult:
    """Complete result of a tuning operation."""
    timestamp: datetime
    leagues_analyzed: List[str]
    recommendations: List[TuningRecommendation]
    applied: bool
    backup_path: Optional[str]
    metrics_before: Dict[str, CalibrationResult]
    config_diff: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "leagues_analyzed": self.leagues_analyzed,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "applied": self.applied,
            "backup_path": self.backup_path,
            "config_diff": self.config_diff,
            "metrics_summary": {
                league: {
                    "brier_score": result.brier_score,
                    "ece": result.ece,
                    "hit_rate": result.hit_rate,
                    "n_predictions": result.n_predictions
                }
                for league, result in self.metrics_before.items()
            }
        }


class CalibrationTuner:
    """
    Service for automatically tuning model calibration based on historical performance.

    The tuner implements the feedback loop:
    1. Read calibration results from CalibrationEngine
    2. Compare predicted vs actual performance
    3. Generate adjustment recommendations
    4. Apply adjustments to config/league_calibrations.yaml

    Key Parameters Tuned:
    - kelly_multiplier: Reduced if we're overconfident, increased if underconfident
    - confidence_threshold: Adjusted based on where we have positive ROI
    - shrinkage_factor: Applied to probabilities based on ECE
    - calibration_factors: Per-bin adjustments for isotonic calibration

    Usage:
        tuner = CalibrationTuner()

        # Add calibration data
        tuner.add_league_calibration("NBA", nba_calibration_result)

        # Generate recommendations
        result = tuner.generate_recommendations()

        # Apply if confident
        if result.recommendations and all(r.confidence > 0.7 for r in result.recommendations):
            tuner.apply_recommendations(result, backup=True)
    """

    # Minimum samples required per league for tuning
    MIN_SAMPLES = 100

    # Maximum adjustment per tuning cycle (prevents overcorrection)
    MAX_KELLY_ADJUSTMENT = 0.10  # +/- 10%
    MAX_THRESHOLD_ADJUSTMENT = 0.05  # +/- 5%

    # ECE thresholds for triggering adjustments
    ECE_GOOD = 0.03  # Below this, calibration is good
    ECE_ACCEPTABLE = 0.05  # Below this, minor adjustments
    ECE_POOR = 0.08  # Above this, significant adjustments needed

    def __init__(
        self,
        config_path: Optional[Path] = None,
        min_samples: int = MIN_SAMPLES
    ):
        """
        Initialize the tuner.

        Args:
            config_path: Path to league_calibrations.yaml
            min_samples: Minimum samples required for tuning
        """
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.min_samples = min_samples

        # Store calibration results by league
        self._calibrations: Dict[str, CalibrationResult] = {}

        # Current config (loaded lazily)
        self._current_config: Optional[Dict] = None

    def _load_config(self) -> Dict[str, Any]:
        """Load current calibration config from YAML."""
        if self._current_config is not None:
            return self._current_config

        if yaml is None:
            logger.warning("PyYAML not installed, using empty config")
            return {}

        if not self.config_path.exists():
            logger.warning(f"Config not found at {self.config_path}")
            return {}

        try:
            with open(self.config_path, 'r') as f:
                self._current_config = yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self._current_config = {}

        return self._current_config

    def _save_config(self, config: Dict[str, Any], backup: bool = True) -> Optional[str]:
        """
        Save config to YAML file.

        Args:
            config: Config dict to save
            backup: Whether to create a backup first

        Returns:
            Path to backup file if created, None otherwise
        """
        if yaml is None:
            logger.error("PyYAML not installed, cannot save config")
            return None

        backup_path = None

        # Create backup
        if backup and self.config_path.exists():
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = BACKUP_DIR / f"league_calibrations_{timestamp}.yaml"

            try:
                with open(self.config_path, 'r') as src:
                    with open(backup_path, 'w') as dst:
                        dst.write(src.read())
                logger.info(f"Created backup at {backup_path}")
            except Exception as e:
                logger.error(f"Failed to create backup: {e}")

        # Save new config
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Saved config to {self.config_path}")
            self._current_config = config
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

        return str(backup_path) if backup_path else None

    def add_league_calibration(
        self,
        league: str,
        calibration: CalibrationResult
    ) -> None:
        """
        Add calibration results for a league.

        Args:
            league: League identifier (NBA, NFL, etc.)
            calibration: CalibrationResult from CalibrationEngine
        """
        self._calibrations[league.upper()] = calibration
        logger.info(f"Added calibration for {league}: n={calibration.n_predictions}, ECE={calibration.ece:.4f}")

    def add_from_engine(
        self,
        league: str,
        engine: CalibrationEngine
    ) -> CalibrationResult:
        """
        Compute and add calibration from a CalibrationEngine instance.

        Args:
            league: League identifier
            engine: CalibrationEngine with loaded predictions

        Returns:
            The computed CalibrationResult
        """
        result = engine.compute_calibration()
        self.add_league_calibration(league, result)
        return result

    def _recommend_kelly_adjustment(
        self,
        league: str,
        calibration: CalibrationResult,
        current_kelly: float
    ) -> Optional[TuningRecommendation]:
        """
        Generate Kelly multiplier adjustment recommendation.

        If we're overconfident (ECE high, hit rate < predicted),
        reduce Kelly to bet smaller on potentially overrated edges.
        """
        if calibration.n_predictions < self.min_samples:
            return None

        # Calculate average overconfidence
        total_pred = sum(b.mean_predicted * b.count for b in calibration.bins if b.count >= 10)
        total_actual = sum(b.mean_actual * b.count for b in calibration.bins if b.count >= 10)
        total_count = sum(b.count for b in calibration.bins if b.count >= 10)

        if total_count == 0:
            return None

        avg_pred = total_pred / total_count
        avg_actual = total_actual / total_count

        # Overconfidence ratio: 1.0 = perfectly calibrated
        # < 1.0 = overconfident, > 1.0 = underconfident
        confidence_ratio = avg_actual / avg_pred if avg_pred > 0 else 1.0

        # Calculate recommended adjustment
        if confidence_ratio < 0.90:  # Significantly overconfident
            adjustment = -self.MAX_KELLY_ADJUSTMENT
            reason = f"Overconfident: predicted {avg_pred:.1%} avg, actual {avg_actual:.1%}"
            confidence = min(0.9, (0.90 - confidence_ratio) * 10)
        elif confidence_ratio > 1.10:  # Significantly underconfident
            adjustment = self.MAX_KELLY_ADJUSTMENT * 0.5  # More conservative for increases
            reason = f"Underconfident: predicted {avg_pred:.1%} avg, actual {avg_actual:.1%}"
            confidence = min(0.7, (confidence_ratio - 1.10) * 5)
        else:
            return None  # Within acceptable range

        new_kelly = max(0.05, min(0.50, current_kelly + adjustment))

        if abs(new_kelly - current_kelly) < 0.01:
            return None

        return TuningRecommendation(
            league=league,
            parameter="kelly_multiplier",
            current_value=current_kelly,
            recommended_value=round(new_kelly, 3),
            reason=reason,
            confidence=confidence,
            sample_size=calibration.n_predictions
        )

    def _recommend_threshold_adjustment(
        self,
        league: str,
        calibration: CalibrationResult,
        current_threshold: float
    ) -> Optional[TuningRecommendation]:
        """
        Generate confidence threshold adjustment recommendation.

        If low-confidence predictions have negative ROI, raise threshold.
        If high-confidence predictions are being missed, consider lowering.
        """
        if calibration.n_predictions < self.min_samples:
            return None

        # Find the bin where we transition from profitable to unprofitable
        profitable_cutoff = None
        bins_sorted = sorted(calibration.bins, key=lambda b: b.lower_bound)

        for bin_obj in bins_sorted:
            if bin_obj.count >= 10:
                # Rough profitability estimate: actual > implied (0.524 for -110)
                if bin_obj.mean_actual > 0.524:
                    if profitable_cutoff is None or bin_obj.lower_bound < profitable_cutoff:
                        profitable_cutoff = bin_obj.lower_bound

        if profitable_cutoff is None:
            # No profitable bins found, recommend raising threshold
            return TuningRecommendation(
                league=league,
                parameter="confidence_threshold",
                current_value=current_threshold,
                recommended_value=min(0.75, current_threshold + self.MAX_THRESHOLD_ADJUSTMENT),
                reason="No profitable confidence bins found",
                confidence=0.6,
                sample_size=calibration.n_predictions
            )

        # Recommend threshold at or near profitable cutoff
        recommended = max(0.52, profitable_cutoff)

        if abs(recommended - current_threshold) < 0.02:
            return None

        return TuningRecommendation(
            league=league,
            parameter="confidence_threshold",
            current_value=current_threshold,
            recommended_value=round(recommended, 3),
            reason=f"Profitable above {profitable_cutoff:.1%} confidence",
            confidence=0.7 if calibration.n_predictions > 200 else 0.5,
            sample_size=calibration.n_predictions
        )

    def _recommend_calibration_factors(
        self,
        league: str,
        calibration: CalibrationResult
    ) -> Optional[TuningRecommendation]:
        """
        Generate calibration factor recommendation.

        These factors are applied to raw probabilities to correct
        systematic biases in each confidence bin.
        """
        if calibration.n_predictions < self.min_samples:
            return None

        # Only recommend if ECE is above acceptable threshold
        if calibration.ece < self.ECE_ACCEPTABLE:
            return None

        factors = calibration.calibration_factors

        # Filter to bins with significant deviation
        significant_factors = {
            k: v for k, v in factors.items()
            if abs(v - 1.0) > 0.05  # More than 5% deviation
        }

        if not significant_factors:
            return None

        return TuningRecommendation(
            league=league,
            parameter="calibration_factors",
            current_value=None,
            recommended_value=significant_factors,
            reason=f"ECE={calibration.ece:.3f} indicates calibration needed",
            confidence=min(0.85, calibration.n_predictions / 500),
            sample_size=calibration.n_predictions
        )

    def generate_recommendations(self) -> TuningResult:
        """
        Analyze all loaded calibrations and generate tuning recommendations.

        Returns:
            TuningResult with all recommendations
        """
        config = self._load_config()
        recommendations: List[TuningRecommendation] = []
        config_diff: Dict[str, Any] = {}

        for league, calibration in self._calibrations.items():
            league_config = config.get(league, {})

            # Kelly multiplier
            current_kelly = league_config.get("kelly_multiplier", 0.25)
            kelly_rec = self._recommend_kelly_adjustment(league, calibration, current_kelly)
            if kelly_rec:
                recommendations.append(kelly_rec)
                config_diff.setdefault(league, {})["kelly_multiplier"] = {
                    "old": current_kelly,
                    "new": kelly_rec.recommended_value
                }

            # Confidence threshold
            current_threshold = league_config.get("confidence_threshold", 0.55)
            threshold_rec = self._recommend_threshold_adjustment(league, calibration, current_threshold)
            if threshold_rec:
                recommendations.append(threshold_rec)
                config_diff.setdefault(league, {})["confidence_threshold"] = {
                    "old": current_threshold,
                    "new": threshold_rec.recommended_value
                }

            # Calibration factors
            factors_rec = self._recommend_calibration_factors(league, calibration)
            if factors_rec:
                recommendations.append(factors_rec)
                config_diff.setdefault(league, {})["calibration_factors"] = factors_rec.recommended_value

        return TuningResult(
            timestamp=datetime.now(),
            leagues_analyzed=list(self._calibrations.keys()),
            recommendations=recommendations,
            applied=False,
            backup_path=None,
            metrics_before=deepcopy(self._calibrations),
            config_diff=config_diff
        )

    def apply_recommendations(
        self,
        result: TuningResult,
        backup: bool = True,
        min_confidence: float = 0.5
    ) -> TuningResult:
        """
        Apply tuning recommendations to the config file.

        Args:
            result: TuningResult from generate_recommendations()
            backup: Whether to backup current config
            min_confidence: Minimum confidence threshold for applying

        Returns:
            Updated TuningResult with applied=True
        """
        if not result.recommendations:
            logger.info("No recommendations to apply")
            return result

        # Filter by confidence
        to_apply = [r for r in result.recommendations if r.confidence >= min_confidence]

        if not to_apply:
            logger.info(f"No recommendations meet confidence threshold ({min_confidence})")
            return result

        config = deepcopy(self._load_config())

        # Apply each recommendation
        for rec in to_apply:
            if rec.league not in config:
                config[rec.league] = {}

            if rec.parameter == "calibration_factors":
                # Merge calibration factors
                existing_factors = config[rec.league].get("calibration_factors", {})
                existing_factors.update(rec.recommended_value)
                config[rec.league]["calibration_factors"] = existing_factors
            else:
                config[rec.league][rec.parameter] = rec.recommended_value

            logger.info(f"Applied {rec.league}.{rec.parameter}: {rec.current_value} -> {rec.recommended_value}")

        # Save config
        backup_path = self._save_config(config, backup=backup)

        # Update result
        result.applied = True
        result.backup_path = backup_path

        return result

    def rollback(self, backup_path: str) -> bool:
        """
        Rollback config to a previous backup.

        Args:
            backup_path: Path to backup file

        Returns:
            True if rollback successful
        """
        if yaml is None:
            logger.error("PyYAML not installed")
            return False

        backup_file = Path(backup_path)
        if not backup_file.exists():
            logger.error(f"Backup not found: {backup_path}")
            return False

        try:
            with open(backup_file, 'r') as src:
                with open(self.config_path, 'w') as dst:
                    dst.write(src.read())
            self._current_config = None  # Force reload
            logger.info(f"Rolled back config from {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def get_tuning_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current calibration state across all leagues.

        Returns:
            Dict with per-league metrics and overall health
        """
        summary = {
            "timestamp": datetime.now().isoformat(),
            "leagues": {},
            "overall_health": "unknown"
        }

        health_scores = []

        for league, calibration in self._calibrations.items():
            # Health score based on ECE
            if calibration.ece < self.ECE_GOOD:
                health = "good"
                score = 1.0
            elif calibration.ece < self.ECE_ACCEPTABLE:
                health = "acceptable"
                score = 0.7
            elif calibration.ece < self.ECE_POOR:
                health = "needs_attention"
                score = 0.4
            else:
                health = "poor"
                score = 0.1

            health_scores.append(score)

            summary["leagues"][league] = {
                "health": health,
                "ece": round(calibration.ece, 4),
                "brier_score": round(calibration.brier_score, 4),
                "hit_rate": round(calibration.hit_rate, 4),
                "n_predictions": calibration.n_predictions,
                "calibration_factors": calibration.calibration_factors
            }

        # Overall health
        if health_scores:
            avg_score = sum(health_scores) / len(health_scores)
            if avg_score > 0.8:
                summary["overall_health"] = "good"
            elif avg_score > 0.5:
                summary["overall_health"] = "acceptable"
            else:
                summary["overall_health"] = "needs_tuning"

        return summary
