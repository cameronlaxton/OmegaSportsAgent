"""
Validation Module (Predict-Grade-Tune)

The calibration engine that acts as the source of truth for confidence intervals.
Implements the Predict-Grade-Tune loop for continuous model improvement.

Architecture:
    1. CAPTURE: When run_game_simulation runs, serialize full probability distribution
    2. RESOLVE: Asynchronously fetch final scores/stats
    3. CALIBRATE: Calculate ECE and Brier Scores
    4. TUNE: Update parameters and config to correct bias

Components:
    - PredictionAudit: JSONB-heavy SQLAlchemy model for any market type
    - CalibrationEngine: ECE, Brier Score, reliability curves
    - ParameterTuner: Runtime simulation parameter adjustment (used by AutoCalibrator)
    - CalibrationTuner: Config write-back — reads CalibrationEngine results and updates
      config/league_calibrations.yaml with corrected shrinkage/threshold values
    - AutoCalibrator: Coordinates PerformanceTracker + ParameterTuner in the runtime loop

Example Usage:
    from src.validation import (
        PredictionAudit,
        CalibrationEngine,
        CalibrationTuner,
        grade_prediction
    )

    # Grade a prediction
    metrics = grade_prediction(prediction_payload, outcome_payload)

    # Build calibration from historical data
    engine = CalibrationEngine()
    engine.add_predictions_batch(historical_records)
    result = engine.compute_calibration()

    # Write back config corrections (CalibrationTuner)
    tuner = CalibrationTuner()
    tuner.add_league_calibration("NBA", result)
    recommendations = tuner.generate_recommendations()
    tuner.apply_recommendations(recommendations, backup=True)
"""

from src.validation.models import (
    PredictionAudit,
    CalibrationSnapshot,
    MarketType,
    AuditStatus,
)

from src.validation.calibrator import (
    CalibrationEngine,
    CalibrationBin,
    CalibrationResult,
    compute_single_brier,
    compute_percentile_rank,
    grade_prediction,
)

from src.validation.tuner import (
    CalibrationTuner,
    TuningRecommendation,
    TuningResult,
)
from src.validation.auto_calibrator import (
    AutoCalibrator,
    CalibrationConfig,
    get_global_calibrator,
    get_tuned_parameter,
)
from src.validation.performance_tracker import PerformanceTracker, PredictionRecord
from src.validation.parameter_tuner import ParameterTuner, TuningStrategy

__all__ = [
    # Models
    "PredictionAudit",
    "CalibrationSnapshot",
    "MarketType",
    "AuditStatus",
    # Calibrator
    "CalibrationEngine",
    "CalibrationBin",
    "CalibrationResult",
    "compute_single_brier",
    "compute_percentile_rank",
    "grade_prediction",
    # Runtime auto-calibration (AutoCalibrator uses ParameterTuner)
    "AutoCalibrator",
    "CalibrationConfig",
    "get_global_calibrator",
    "get_tuned_parameter",
    "PerformanceTracker",
    "PredictionRecord",
    "ParameterTuner",
    "TuningStrategy",
    # Config write-back (CalibrationTuner writes to league_calibrations.yaml)
    "CalibrationTuner",
    "TuningRecommendation",
    "TuningResult",
]
