#!/usr/bin/env python3
"""
Example: Autonomous Calibration System

This script demonstrates the autonomous calibration and self-enhancement
capabilities of the OmegaSportsAgent system.

Usage:
    python example_autonomous_calibration.py
"""

import os
import json
from datetime import datetime


def main():
    """Demonstrate autonomous calibration system."""
    
    print("="*70)
    print("OMEGA Autonomous Calibration System Demo")
    print("="*70)
    print()
    
    # ============================================================
    # STEP 1: Initialize Calibration System
    # ============================================================
    print("STEP 1: Initialize Calibration System")
    print("-"*70)
    
    from omega.calibration import AutoCalibrator, CalibrationConfig, TuningStrategy
    
    config = CalibrationConfig(
        auto_tune_enabled=True,
        auto_tune_frequency=50,  # Tune every 50 predictions
        min_samples_for_tuning=20,
        tuning_strategy=TuningStrategy.ADAPTIVE,
        performance_window=100
    )
    
    calibrator = AutoCalibrator(config=config)
    print("✓ AutoCalibrator initialized")
    print(f"  Strategy: {config.tuning_strategy.value}")
    print(f"  Auto-tune frequency: every {config.auto_tune_frequency} predictions")
    
    # ============================================================
    # STEP 2: View Current Parameters
    # ============================================================
    print("\nSTEP 2: Current Tuned Parameters")
    print("-"*70)
    
    important_params = [
        "edge_threshold_spread",
        "edge_threshold_prop",
        "kelly_fraction",
        "calibration_shrink_factor",
        "markov_shot_allocation_star"
    ]
    
    print("\nKey Parameters:")
    for param in important_params:
        value = calibrator.get_calibrated_parameter(param)
        if value is not None:
            print(f"  {param}: {value}")
    
    # ============================================================
    # STEP 3: Simulate Making Predictions
    # ============================================================
    print("\nSTEP 3: Simulate Predictions and Outcomes")
    print("-"*70)
    
    print("\nLogging 30 simulated predictions...")
    
    prediction_ids = []
    
    # Simulate various predictions
    import random
    random.seed(42)
    
    for i in range(30):
        # Simulate a player prop prediction
        predicted_prob = 0.55 + random.gauss(0, 0.1)
        predicted_prob = max(0.3, min(0.8, predicted_prob))
        
        edge = (predicted_prob - 0.52) * 100  # vs market
        
        pred_id = calibrator.log_prediction(
            prediction_type="player_prop",
            league="NBA",
            predicted_value=27.5,
            predicted_probability=predicted_prob,
            confidence_tier="B" if edge > 5 else "C",
            edge_pct=edge,
            stake_amount=20.0,
            metadata={"player": f"Player_{i}"}
        )
        
        prediction_ids.append((pred_id, predicted_prob))
    
    print(f"✓ Logged {len(prediction_ids)} predictions")
    
    # ============================================================
    # STEP 4: Simulate Outcomes
    # ============================================================
    print("\nSTEP 4: Update with Simulated Outcomes")
    print("-"*70)
    
    wins = 0
    losses = 0
    
    for pred_id, pred_prob in prediction_ids:
        # Simulate outcome (slightly worse than predicted to trigger calibration)
        actual_win = random.random() < (pred_prob - 0.05)  # Slightly worse than predicted
        
        if actual_win:
            wins += 1
            calibrator.update_outcome(
                prediction_id=pred_id,
                actual_value=28.5,
                actual_result="Win",
                profit_loss=18.0  # -110 odds
            )
        else:
            losses += 1
            calibrator.update_outcome(
                prediction_id=pred_id,
                actual_value=26.5,
                actual_result="Loss",
                profit_loss=-20.0
            )
    
    print(f"✓ Updated {wins + losses} outcomes")
    print(f"  Wins: {wins}")
    print(f"  Losses: {losses}")
    print(f"  Win Rate: {wins/(wins+losses):.2%}")
    
    # ============================================================
    # STEP 5: Get Performance Report
    # ============================================================
    print("\nSTEP 5: Performance Report (Before Calibration)")
    print("-"*70)
    
    report = calibrator.get_performance_report()
    perf = report["overall_performance"]
    
    print(f"\n📊 PERFORMANCE METRICS:")
    print(f"  Settled Predictions: {perf['settled_predictions']}")
    print(f"  Win Rate: {perf['win_rate']:.2%}")
    print(f"  Total Staked: ${perf['total_staked']:.2f}")
    print(f"  Total Profit: ${perf['total_profit']:.2f}")
    print(f"  ROI: {perf['roi']:.2f}%")
    print(f"  Brier Score: {perf['brier_score']:.3f}")
    print(f"  Calibration Quality: {perf['calibration_quality']}")
    
    # ============================================================
    # STEP 6: Run Autonomous Calibration
    # ============================================================
    print("\nSTEP 6: Run Autonomous Calibration")
    print("-"*70)
    
    print("\nRunning adaptive parameter tuning...")
    calibration_result = calibrator.run_calibration(force=True)
    
    tuning = calibration_result["tuning_result"]
    print(f"\n✓ Calibration complete")
    print(f"  Strategy: {tuning.get('strategy', 'N/A')}")
    print(f"  Parameters Tuned: {tuning['parameters_tuned']}")
    
    if tuning['parameters_tuned'] > 0:
        print(f"\n📝 PARAMETER ADJUSTMENTS:")
        for adj in tuning['adjustments']:
            print(f"  {adj['parameter']}:")
            print(f"    {adj['old_value']:.4f} → {adj['new_value']:.4f}")
            print(f"    Reason: {adj['reason']}")
    else:
        print("\n  No adjustments needed - performance is satisfactory")
    
    # ============================================================
    # STEP 7: View Updated Parameters
    # ============================================================
    print("\nSTEP 7: Updated Parameters")
    print("-"*70)
    
    print("\nKey Parameters After Calibration:")
    for param in important_params:
        value = calibrator.get_calibrated_parameter(param)
        if value is not None:
            print(f"  {param}: {value}")
    
    # ============================================================
    # STEP 8: Demonstrate Integration
    # ============================================================
    print("\nSTEP 8: Integration with Existing Code")
    print("-"*70)
    
    print("\nHow to use calibrated parameters in your code:")
    print("""
from omega.calibration import get_tuned_parameter

# In your betting analysis code:
edge_threshold = get_tuned_parameter("edge_threshold_prop", default=5.0)

if calculated_edge >= edge_threshold:
    # Place bet
    pass

# In your Markov simulation:
star_allocation = get_tuned_parameter("markov_shot_allocation_star", default=0.30)

# In your probability calibration:
shrink_factor = get_tuned_parameter("calibration_shrink_factor", default=0.70)
""")
    
    # ============================================================
    # STEP 9: Save Report
    # ============================================================
    print("\nSTEP 9: Save Calibration Report")
    print("-"*70)
    
    os.makedirs("outputs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    output_file = f"outputs/calibration_report_{timestamp}.json"
    
    full_report = calibrator.get_performance_report(include_details=True)
    
    with open(output_file, 'w') as f:
        json.dump(full_report, f, indent=2, default=str)
    
    print(f"✓ Report saved to: {output_file}")
    
    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "="*70)
    print("SUMMARY: Autonomous Calibration Features")
    print("="*70)
    
    print("""
✅ The OmegaSportsAgent now has autonomous calibration capabilities:

1. **Performance Tracking**
   - Every prediction and outcome is logged
   - Comprehensive performance metrics calculated
   - Historical data persisted for learning

2. **Autonomous Parameter Tuning**
   - Parameters automatically adjusted based on performance
   - Multiple tuning strategies (Adaptive, Conservative, Gradient)
   - Learns which parameter values lead to best outcomes

3. **Feedback Loops**
   - Continuous monitoring of ROI, win rate, Brier score
   - Automatic alerts when performance degrades
   - Self-correction mechanisms

4. **Integration Points**
   - Markov simulation uses calibrated shot allocation
   - Edge thresholds auto-adjust based on win rate
   - Probability calibration shrinkage self-tunes
   - Kelly fraction optimizes based on volatility

5. **Calibration Strategies**
   - **Adaptive**: Aggressive when losing, conservative when winning
   - **Conservative**: Small, safe adjustments only
   - **Gradient**: Moves toward historically best parameter values

The system runs automatically every N predictions, or can be triggered manually.
All calibrated parameters are accessible via get_tuned_parameter() function.
""")
    
    print("\n" + "="*70)
    print("✅ Demo complete! The system is learning and improving.")
    print("="*70)


if __name__ == "__main__":
    main()
