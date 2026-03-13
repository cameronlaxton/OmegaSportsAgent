"""
Tests for the Autonomous Calibration System.

Tests performance tracking, parameter tuning, and auto-calibration —
all active, load-bearing modules in src.validation.
"""

import os
import tempfile

import pytest


class TestPerformanceTracker:
    """Test the performance tracking system."""

    def test_log_and_settle_predictions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "predictions.json")

            from src.validation.performance_tracker import PerformanceTracker

            tracker = PerformanceTracker(storage_path=storage_path)

            pred_ids = []
            for i in range(5):
                pred_id = tracker.log_prediction(
                    prediction_type="player_prop",
                    league="NBA",
                    predicted_value=25.5,
                    predicted_probability=0.60,
                    confidence_tier="B",
                    edge_pct=7.5,
                    stake_amount=20.0,
                    parameters_used={"test_param": 1.0},
                )
                pred_ids.append(pred_id)

            assert len(pred_ids) == 5

            for i, pred_id in enumerate(pred_ids):
                tracker.update_outcome(
                    prediction_id=pred_id,
                    actual_value=26.0 if i % 2 == 0 else 24.0,
                    actual_result="Win" if i % 2 == 0 else "Loss",
                    profit_loss=18.0 if i % 2 == 0 else -20.0,
                )

            summary = tracker.get_performance_summary()
            assert summary["settled_predictions"] == 5
            assert 0.5 <= summary["win_rate"] <= 0.7  # 3W/2L = 60%


class TestParameterTuner:
    """Test the parameter tuning system."""

    def test_auto_tune_with_poor_performance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "predictions.json")
            config_path = os.path.join(tmpdir, "tuned_parameters.json")

            from src.validation.performance_tracker import PerformanceTracker
            from src.validation.parameter_tuner import ParameterTuner, TuningStrategy

            tracker = PerformanceTracker(storage_path=storage_path)
            tuner = ParameterTuner(tracker, config_path=config_path)

            initial_edge = tuner.get_parameter("edge_threshold_prop")
            assert initial_edge is not None

            # Log poor performance data (33% win rate)
            for i in range(60):
                pred_id = tracker.log_prediction(
                    prediction_type="player_prop",
                    league="NBA",
                    predicted_value=25.5,
                    predicted_probability=0.55,
                    confidence_tier="C",
                    edge_pct=4.0,
                    stake_amount=20.0,
                    parameters_used={"edge_threshold_prop": initial_edge},
                )
                tracker.update_outcome(
                    prediction_id=pred_id,
                    actual_value=26.0 if i % 3 == 0 else 24.0,
                    actual_result="Win" if i % 3 == 0 else "Loss",
                    profit_loss=18.0 if i % 3 == 0 else -20.0,
                )

            result = tuner.auto_tune(
                strategy=TuningStrategy.ADAPTIVE,
                min_samples=50,
                recent_window=60,
            )
            assert result["status"] == "success"


class TestAutoCalibrator:
    """Test the main auto-calibrator."""

    def test_log_predict_and_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "predictions.json")
            config_path = os.path.join(tmpdir, "tuned_parameters.json")

            from src.validation import AutoCalibrator, CalibrationConfig

            config = CalibrationConfig(
                auto_tune_enabled=False,
                min_samples_for_tuning=10,
            )
            calibrator = AutoCalibrator(
                config=config,
                storage_path=storage_path,
                param_config_path=config_path,
            )

            pred_id = calibrator.log_prediction(
                prediction_type="spread",
                league="NFL",
                predicted_value=-7.5,
                predicted_probability=0.62,
                confidence_tier="A",
                edge_pct=9.0,
                stake_amount=30.0,
            )
            assert pred_id is not None

            calibrator.update_outcome(
                prediction_id=pred_id,
                actual_value=-10.0,
                actual_result="Win",
                profit_loss=27.0,
            )

            threshold = calibrator.get_calibrated_parameter("edge_threshold_spread", 3.0)
            assert threshold is not None

            report = calibrator.get_performance_report()
            assert "overall_performance" in report
            assert "current_parameters" in report


class TestMarkovIntegration:
    """Test that Markov engine uses calibrated parameters."""

    def test_transition_matrix_and_tuned_params(self, tmp_path, monkeypatch):
        import src.validation.auto_calibrator as _ac

        # Reset global singleton and redirect its storage to tmp_path
        monkeypatch.setattr(_ac, "_global_calibrator", None)

        _orig_init = _ac.AutoCalibrator.__init__

        def _patched_init(self, config=None, storage_path=None, param_config_path=None):
            _orig_init(
                self,
                config=config,
                storage_path=str(tmp_path / "predictions.json"),
                param_config_path=str(tmp_path / "tuned.json"),
            )

        monkeypatch.setattr(_ac.AutoCalibrator, "__init__", _patched_init)

        from src.simulation.markov_engine import TransitionMatrix
        from src.validation import get_tuned_parameter

        matrix = TransitionMatrix("NBA")
        allocation = matrix.get_transition_probs("shot_allocation")
        star_pct = allocation.get("star_player", 0)

        tuned_star = get_tuned_parameter("markov_shot_allocation_star", 0.30)
        assert abs(star_pct - tuned_star) < 0.05
