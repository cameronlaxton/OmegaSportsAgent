"""
Validator-Lab Module

The calibration engine that acts as the source of truth for confidence intervals.
Implements the Predict-Grade-Tune loop for continuous model improvement.

Architecture:
    1. CAPTURE: When run_game_simulation runs, serialize full probability distribution
    2. RESOLVE: Asynchronously fetch final scores/stats
    3. CALIBRATE: Calculate ECE and Brier Scores
    4. TUNE: Update config/league_calibrations.yaml to correct bias

Components:
    - PredictionAudit: JSONB-heavy SQLAlchemy model for any market type
    - CalibrationEngine: ECE, Brier Score, reliability curves
    - CalibrationTuner: Automatic config updates based on performance

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

    # Auto-tune configuration
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
    # Tuner
    "CalibrationTuner",
    "TuningRecommendation",
    "TuningResult",
]
