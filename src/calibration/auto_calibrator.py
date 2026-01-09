"""
Auto-Calibrator Module

Main autonomous calibration engine that coordinates performance tracking,
parameter tuning, and feedback loops for continuous model improvement.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List

from src.calibration.performance_tracker import PerformanceTracker
from src.calibration.parameter_tuner import ParameterTuner, TuningStrategy

logger = logging.getLogger(__name__)


@dataclass
class CalibrationConfig:
    """
    Configuration for autonomous calibration system.
    
    Attributes:
        auto_tune_enabled: Enable automatic parameter tuning
        auto_tune_frequency: How often to run auto-tuning (in predictions or time-based)
        auto_tune_mode: "prediction_count" or "time_based"
        auto_tune_schedule: For time_based mode: "daily", "weekly", or cron expression
        min_samples_for_tuning: Minimum settled predictions before tuning
        tuning_strategy: Which tuning strategy to use
        performance_window: Number of recent predictions to analyze
        alert_on_poor_performance: Send alerts when performance drops
        roi_alert_threshold: ROI threshold for alerts (negative)
        brier_alert_threshold: Brier score threshold for alerts
        last_calibration_time: Timestamp of last calibration (internal use)
    """
    auto_tune_enabled: bool = True
    auto_tune_frequency: int = 100  # Tune every 100 predictions (if prediction_count mode)
    auto_tune_mode: str = "prediction_count"  # "prediction_count" or "time_based"
    auto_tune_schedule: str = "weekly"  # "daily", "weekly", or cron expression
    min_samples_for_tuning: int = 50
    tuning_strategy: TuningStrategy = TuningStrategy.ADAPTIVE
    performance_window: int = 100
    alert_on_poor_performance: bool = True
    roi_alert_threshold: float = -10.0
    brier_alert_threshold: float = 0.25
    last_calibration_time: Optional[str] = None


class AutoCalibrator:
    """
    Main autonomous calibration engine.
    
    This is the brain of the self-enhancement system. It:
    1. Tracks all predictions and outcomes
    2. Monitors performance metrics continuously
    3. Auto-tunes parameters based on feedback
    4. Alerts when performance degrades
    5. Provides calibrated probabilities and parameters
    
    Usage:
        calibrator = AutoCalibrator()
        
        # Log a prediction
        pred_id = calibrator.log_prediction(...)
        
        # Later, update with outcome
        calibrator.update_outcome(pred_id, ...)
        
        # System auto-tunes periodically
        # Or manually trigger tuning
        calibrator.run_calibration()
    """
    
    def __init__(
        self,
        config: Optional[CalibrationConfig] = None,
        storage_path: str = "data/logs/predictions.json",
        param_config_path: str = "config/calibration/tuned_parameters.json"
    ):
        """
        Initialize the auto-calibrator.
        
        Args:
            config: Calibration configuration
            storage_path: Path for storing prediction records
            param_config_path: Path for storing tuned parameters
        """
        self.config = config or CalibrationConfig()
        
        # Initialize subsystems
        self.tracker = PerformanceTracker(storage_path)
        self.tuner = ParameterTuner(self.tracker, param_config_path)
        
        # Track when last auto-tune was run
        self._predictions_since_tune = 0
        
        logger.info("AutoCalibrator initialized with strategy: %s", self.config.tuning_strategy)
    
    def log_prediction(
        self,
        prediction_type: str,
        league: str,
        predicted_value: float,
        predicted_probability: float,
        confidence_tier: str,
        edge_pct: float,
        stake_amount: float,
        parameters_used: Optional[Dict[str, Any]] = None,
        model_version: str = "1.0",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a new prediction to the tracking system.
        
        This should be called every time the system makes a prediction.
        
        Returns:
            prediction_id for later updating with outcome
        """
        # Get current parameter values if not provided
        if parameters_used is None:
            parameters_used = {}
        
        # Add current tuned parameter values
        for param_name in self.tuner.parameters:
            if param_name not in parameters_used:
                parameters_used[param_name] = self.tuner.get_parameter(param_name)
        
        prediction_id = self.tracker.log_prediction(
            prediction_type=prediction_type,
            league=league,
            predicted_value=predicted_value,
            predicted_probability=predicted_probability,
            confidence_tier=confidence_tier,
            edge_pct=edge_pct,
            stake_amount=stake_amount,
            parameters_used=parameters_used,
            model_version=model_version,
            metadata=metadata
        )
        
        # Increment counter and check if auto-tune should run
        self._predictions_since_tune += 1
        
        if self.config.auto_tune_enabled:
            should_calibrate = False
            
            if self.config.auto_tune_mode == "prediction_count":
                # Original behavior: calibrate every N predictions
                if self._predictions_since_tune >= self.config.auto_tune_frequency:
                    should_calibrate = True
            elif self.config.auto_tune_mode == "time_based":
                # New behavior: calibrate based on time schedule
                should_calibrate = self._should_run_time_based_calibration()
            
            if should_calibrate:
                logger.info("Auto-tune threshold reached, running calibration...")
                self.run_calibration()
                self._predictions_since_tune = 0
                self.config.last_calibration_time = datetime.now().isoformat()
        
        return prediction_id
    
    def _should_run_time_based_calibration(self) -> bool:
        """
        Check if time-based calibration should run.
        
        Returns:
            True if enough time has passed since last calibration
        """
        if not self.config.last_calibration_time:
            # First time, run calibration
            return True
        
        try:
            from datetime import timedelta
            last_cal = datetime.fromisoformat(self.config.last_calibration_time)
            now = datetime.now()
            time_diff = now - last_cal
            
            if self.config.auto_tune_schedule == "daily":
                # Run once per day (after 24 hours)
                return time_diff >= timedelta(days=1)
            elif self.config.auto_tune_schedule == "weekly":
                # Run once per week (after 7 days)
                return time_diff >= timedelta(days=7)
            else:
                # For custom schedules, default to weekly
                return time_diff >= timedelta(days=7)
        except Exception as e:
            logger.error(f"Error checking time-based calibration: {e}")
            return False
    
    def update_outcome(
        self,
        prediction_id: str,
        actual_value: float,
        actual_result: str,
        profit_loss: float
    ) -> None:
        """
        Update a prediction with its actual outcome.
        
        Args:
            prediction_id: ID returned from log_prediction
            actual_value: Actual outcome value
            actual_result: "Win", "Loss", or "Push"
            profit_loss: Actual profit or loss amount
        """
        self.tracker.update_outcome(
            prediction_id=prediction_id,
            actual_value=actual_value,
            actual_result=actual_result,
            profit_loss=profit_loss
        )
        
        # Check if performance alerts should be triggered
        if self.config.alert_on_poor_performance:
            self._check_performance_alerts()
    
    def run_calibration(
        self,
        strategy: Optional[TuningStrategy] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Run autonomous calibration and parameter tuning.
        
        This analyzes recent performance and adjusts parameters accordingly.
        
        Args:
            strategy: Tuning strategy (uses config default if not specified)
            force: Force calibration even if insufficient samples
        
        Returns:
            Dict with calibration results
        """
        strategy = strategy or self.config.tuning_strategy
        
        logger.info("Running calibration with strategy: %s", strategy)
        
        # Run parameter tuning
        tuning_result = self.tuner.auto_tune(
            strategy=strategy,
            min_samples=0 if force else self.config.min_samples_for_tuning,
            recent_window=self.config.performance_window
        )
        
        # Get updated performance summary
        performance = self.tracker.get_performance_summary(
            recent_n=self.config.performance_window
        )
        
        # Log calibration event
        logger.info(
            "Calibration complete: tuned %d parameters, ROI: %.2f%%, Brier: %.3f",
            tuning_result.get("parameters_tuned", 0),
            performance.get("roi", 0),
            performance.get("brier_score", 0)
        )
        
        return {
            "timestamp": datetime.now().isoformat(),
            "tuning_result": tuning_result,
            "current_performance": performance,
            "status": "success"
        }
    
    def _check_performance_alerts(self) -> None:
        """Check if performance alerts should be triggered."""
        performance = self.tracker.get_performance_summary(
            recent_n=self.config.performance_window
        )
        
        roi = performance.get("roi", 0)
        brier = performance.get("brier_score", 0)
        
        if roi < self.config.roi_alert_threshold:
            logger.warning(
                "PERFORMANCE ALERT: ROI below threshold (%.2f%% < %.2f%%)",
                roi, self.config.roi_alert_threshold
            )
        
        if brier > self.config.brier_alert_threshold:
            logger.warning(
                "CALIBRATION ALERT: Brier score above threshold (%.3f > %.3f)",
                brier, self.config.brier_alert_threshold
            )
    
    def get_calibrated_parameter(self, name: str, default: float = None) -> Optional[float]:
        """
        Get current calibrated value for a parameter.
        
        This is the primary interface for other modules to get tuned parameters.
        
        Args:
            name: Parameter name
            default: Default value if parameter not found
        
        Returns:
            Current tuned value or default (typically float, but could be int)
        """
        value = self.tuner.get_parameter(name)
        return value if value is not None else default
    
    def get_performance_report(
        self,
        prediction_type: Optional[str] = None,
        league: Optional[str] = None,
        include_details: bool = False
    ) -> Dict[str, Any]:
        """
        Get comprehensive performance report.
        
        Args:
            prediction_type: Filter by prediction type
            league: Filter by league
            include_details: Include detailed breakdowns
        
        Returns:
            Dict with performance metrics and analysis
        """
        overall = self.tracker.get_performance_summary(
            prediction_type=prediction_type,
            league=league,
            recent_n=self.config.performance_window
        )
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_performance": overall,
            "current_parameters": {
                name: config.current_value
                for name, config in self.tuner.parameters.items()
            },
            "config": {
                "auto_tune_enabled": self.config.auto_tune_enabled,
                "tuning_strategy": self.config.tuning_strategy.value,
                "performance_window": self.config.performance_window
            }
        }
        
        if include_details:
            # Add per-league breakdown
            report["by_league"] = {}
            for league in ["NBA", "NFL", "MLB", "NHL"]:
                league_perf = self.tracker.get_performance_summary(
                    league=league,
                    recent_n=self.config.performance_window
                )
                if league_perf.get("settled_predictions", 0) > 0:
                    report["by_league"][league] = league_perf
            
            # Add per-type breakdown
            report["by_type"] = {}
            for pred_type in ["spread", "total", "moneyline", "player_prop"]:
                type_perf = self.tracker.get_performance_summary(
                    prediction_type=pred_type,
                    recent_n=self.config.performance_window
                )
                if type_perf.get("settled_predictions", 0) > 0:
                    report["by_type"][pred_type] = type_perf
        
        return report
    
    def reset_to_defaults(self) -> Dict[str, Any]:
        """
        Reset all parameters to default values.
        
        Use this if auto-tuning has led to poor performance and you want to start over.
        
        Returns:
            Dict with reset parameters
        """
        logger.warning("Resetting all parameters to defaults")
        
        old_params = {
            name: config.current_value
            for name, config in self.tuner.parameters.items()
        }
        
        # Reload defaults
        self.tuner.parameters = self.tuner._get_default_parameters()
        self.tuner.save_parameters()
        
        return {
            "status": "reset_complete",
            "old_parameters": old_params,
            "new_parameters": {
                name: config.current_value
                for name, config in self.tuner.parameters.items()
            },
            "timestamp": datetime.now().isoformat()
        }


# Global instance for easy access across the codebase
_global_calibrator: Optional[AutoCalibrator] = None


def get_global_calibrator() -> AutoCalibrator:
    """
    Get or create global AutoCalibrator instance.
    
    This provides a singleton pattern for easy access across modules.
    """
    global _global_calibrator
    
    if _global_calibrator is None:
        _global_calibrator = AutoCalibrator()
    
    return _global_calibrator


def get_tuned_parameter(name: str, default: Any = None) -> Any:
    """
    Convenience function to get a tuned parameter value.
    
    Usage:
        from src.calibration import get_tuned_parameter
        
        edge_threshold = get_tuned_parameter("edge_threshold_prop", default=5.0)
    """
    calibrator = get_global_calibrator()
    return calibrator.get_calibrated_parameter(name, default)
