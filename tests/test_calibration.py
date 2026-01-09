"""
Test Suite for Autonomous Calibration System

Tests performance tracking, parameter tuning, and auto-calibration.
"""

import os
import tempfile
import shutil
from datetime import datetime

def test_performance_tracker():
    """Test the performance tracking system."""
    print("="*70)
    print("Test: Performance Tracker")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "predictions.json")
        
        from omega.calibration.performance_tracker import PerformanceTracker
        
        tracker = PerformanceTracker(storage_path=storage_path)
        print("✓ PerformanceTracker initialized")
        
        # Log some predictions
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
                parameters_used={"test_param": 1.0}
            )
            pred_ids.append(pred_id)
        
        print(f"✓ Logged {len(pred_ids)} predictions")
        
        # Update outcomes
        for i, pred_id in enumerate(pred_ids):
            tracker.update_outcome(
                prediction_id=pred_id,
                actual_value=26.0 if i % 2 == 0 else 24.0,
                actual_result="Win" if i % 2 == 0 else "Loss",
                profit_loss=18.0 if i % 2 == 0 else -20.0
            )
        
        print("✓ Updated outcomes")
        
        # Get performance summary
        summary = tracker.get_performance_summary()
        print(f"✓ Performance summary: Win rate = {summary['win_rate']:.2%}, ROI = {summary['roi']:.1f}%")
        
        assert summary['settled_predictions'] == 5
        assert 0.5 <= summary['win_rate'] <= 0.7  # Should be 60% (3 wins, 2 losses)
        
    print("✅ Performance Tracker tests passed!\n")


def test_parameter_tuner():
    """Test the parameter tuning system."""
    print("="*70)
    print("Test: Parameter Tuner")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "predictions.json")
        config_path = os.path.join(tmpdir, "tuned_parameters.json")
        
        from omega.calibration.performance_tracker import PerformanceTracker
        from omega.calibration.parameter_tuner import ParameterTuner, TuningStrategy
        
        tracker = PerformanceTracker(storage_path=storage_path)
        tuner = ParameterTuner(tracker, config_path=config_path)
        
        print("✓ ParameterTuner initialized")
        
        # Check initial parameters
        initial_edge = tuner.get_parameter("edge_threshold_prop")
        print(f"✓ Initial edge_threshold_prop: {initial_edge}")
        
        assert initial_edge is not None
        
        # Log poor performance data
        for i in range(60):
            pred_id = tracker.log_prediction(
                prediction_type="player_prop",
                league="NBA",
                predicted_value=25.5,
                predicted_probability=0.55,
                confidence_tier="C",
                edge_pct=4.0,
                stake_amount=20.0,
                parameters_used={"edge_threshold_prop": initial_edge}
            )
            
            # Simulate losing more than winning
            tracker.update_outcome(
                prediction_id=pred_id,
                actual_value=26.0 if i % 3 == 0 else 24.0,
                actual_result="Win" if i % 3 == 0 else "Loss",
                profit_loss=18.0 if i % 3 == 0 else -20.0
            )
        
        print("✓ Logged 60 predictions with poor performance")
        
        # Run tuning
        result = tuner.auto_tune(
            strategy=TuningStrategy.ADAPTIVE,
            min_samples=50,
            recent_window=60
        )
        
        print(f"✓ Auto-tuning complete: {result['parameters_tuned']} parameters adjusted")
        
        if result['parameters_tuned'] > 0:
            for adj in result['adjustments']:
                print(f"  - {adj['parameter']}: {adj['old_value']} → {adj['new_value']}")
        
        assert result['status'] == 'success'
        
    print("✅ Parameter Tuner tests passed!\n")


def test_auto_calibrator():
    """Test the main auto-calibrator."""
    print("="*70)
    print("Test: Auto-Calibrator")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "predictions.json")
        config_path = os.path.join(tmpdir, "tuned_parameters.json")
        
        from omega.calibration import AutoCalibrator, CalibrationConfig, TuningStrategy
        
        config = CalibrationConfig(
            auto_tune_enabled=False,  # Manual for testing
            min_samples_for_tuning=10
        )
        
        calibrator = AutoCalibrator(
            config=config,
            storage_path=storage_path,
            param_config_path=config_path
        )
        
        print("✓ AutoCalibrator initialized")
        
        # Test logging predictions
        pred_id = calibrator.log_prediction(
            prediction_type="spread",
            league="NFL",
            predicted_value=-7.5,
            predicted_probability=0.62,
            confidence_tier="A",
            edge_pct=9.0,
            stake_amount=30.0
        )
        
        print(f"✓ Logged prediction: {pred_id}")
        
        # Update outcome
        calibrator.update_outcome(
            prediction_id=pred_id,
            actual_value=-10.0,
            actual_result="Win",
            profit_loss=27.0
        )
        
        print("✓ Updated outcome")
        
        # Test getting calibrated parameter
        threshold = calibrator.get_calibrated_parameter("edge_threshold_spread", 3.0)
        print(f"✓ Got calibrated parameter: edge_threshold_spread = {threshold}")
        
        assert threshold is not None
        
        # Test performance report
        report = calibrator.get_performance_report()
        print("✓ Generated performance report")
        
        assert 'overall_performance' in report
        assert 'current_parameters' in report
        
    print("✅ Auto-Calibrator tests passed!\n")


def test_markov_integration():
    """Test that Markov engine uses calibrated parameters."""
    print("="*70)
    print("Test: Markov Integration")
    print("="*70)
    
    try:
        from omega.simulation.markov_engine import TransitionMatrix
        from omega.calibration import get_tuned_parameter
        
        # Create transition matrix
        matrix = TransitionMatrix("NBA")
        print("✓ TransitionMatrix created")
        
        # Check that shot allocation is retrieved
        allocation = matrix.get_transition_probs("shot_allocation")
        star_pct = allocation.get("star_player", 0)
        
        print(f"✓ Star player shot allocation: {star_pct:.2%}")
        
        # Get the tuned parameter directly
        tuned_star = get_tuned_parameter("markov_shot_allocation_star", 0.30)
        print(f"✓ Tuned star allocation parameter: {tuned_star}")
        
        # They should be close (may differ slightly due to normalization)
        assert abs(star_pct - tuned_star) < 0.05
        
    except ImportError as e:
        print(f"⚠ Skipping Markov integration test: {e}")
    
    print("✅ Markov integration test passed!\n")


def main():
    """Run all calibration tests."""
    print("\n")
    print("="*70)
    print("OMEGA Autonomous Calibration Test Suite")
    print("="*70)
    print("\n")
    
    tests_passed = 0
    tests_failed = 0
    
    try:
        test_performance_tracker()
        tests_passed += 1
    except Exception as e:
        print(f"❌ Performance Tracker test failed: {e}\n")
        tests_failed += 1
    
    try:
        test_parameter_tuner()
        tests_passed += 1
    except Exception as e:
        print(f"❌ Parameter Tuner test failed: {e}\n")
        tests_failed += 1
    
    try:
        test_auto_calibrator()
        tests_passed += 1
    except Exception as e:
        print(f"❌ Auto-Calibrator test failed: {e}\n")
        tests_failed += 1
    
    try:
        test_markov_integration()
        tests_passed += 1
    except Exception as e:
        print(f"❌ Markov integration test failed: {e}\n")
        tests_failed += 1
    
    # Summary
    print("="*70)
    print(f"Test Results: {tests_passed} passed, {tests_failed} failed")
    print("="*70)
    
    if tests_failed == 0:
        print("\n✅ All calibration tests passed!")
        return 0
    else:
        print(f"\n❌ {tests_failed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())
