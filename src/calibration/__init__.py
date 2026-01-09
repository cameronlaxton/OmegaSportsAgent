"""
OMEGA Autonomous Calibration System

This module provides autonomous calibration and self-enhancement capabilities
for all simulation and prediction functions across the OmegaSportsAgent system.

Components:
    - AutoCalibrator: Main autonomous calibration engine
    - PerformanceTracker: Tracks predictions vs actual outcomes
    - ParameterTuner: Auto-adjusts model parameters based on performance
    - FeedbackLoop: Implements learning from historical performance
"""

from src.calibration.auto_calibrator import (
    AutoCalibrator,
    CalibrationConfig,
    get_global_calibrator,
    get_tuned_parameter
)
from src.calibration.performance_tracker import PerformanceTracker, PredictionRecord
from src.calibration.parameter_tuner import ParameterTuner, TuningStrategy

__all__ = [
    "AutoCalibrator",
    "CalibrationConfig",
    "PerformanceTracker",
    "PredictionRecord",
    "ParameterTuner",
    "TuningStrategy",
    "get_global_calibrator",
    "get_tuned_parameter",
]
