#!/usr/bin/env python3
"""
Test script to verify ValidationLab calibration parameters are properly implemented.

Validates:
- Calibrated edge thresholds are loaded correctly
- Platt + shrinkage transforms work as expected
- Kelly staking parameters are accessible
- BetRecorder integration with calibrated parameters
- ValidationLab compatibility
"""

import sys
from datetime import datetime

def test_calibrated_edge_thresholds():
    """Test that calibrated edge thresholds from ValidationLab are loaded"""
    print("\n=== Test: Calibrated Edge Thresholds ===")
    
    from config.calibration_loader import CalibrationLoader
    
    cal = CalibrationLoader("NBA")
    
    # Verify version
    assert cal.get_version() == "v2.0", f"Expected v2.0, got {cal.get_version()}"
    print(f"✓ Calibration version: {cal.get_version()}")
    
    # Verify calibrated thresholds from ValidationLab
    expected_thresholds = {
        "moneyline": 0.03,
        "spread": 0.095,
        "total": 0.01,
        "player_prop_points": 0.03,
        "player_prop_rebounds": 0.03,
        "player_prop_assists": 0.03,
    }
    
    for market_type, expected_value in expected_thresholds.items():
        actual = cal.get_edge_threshold(market_type)
        assert abs(actual - expected_value) < 0.001, f"{market_type}: expected {expected_value}, got {actual}"
        print(f"✓ {market_type}: {actual} (expected {expected_value})")
    
    print("✅ Calibrated Edge Thresholds passed")
    return True


def test_platt_shrink_transforms():
    """Test that Platt + shrinkage transforms work correctly"""
    print("\n=== Test: Platt + Shrinkage Transforms ===")
    
    from config.calibration_loader import CalibrationLoader
    
    cal = CalibrationLoader("NBA")
    
    # Test moneyline transform (platt + shrink with alpha=0.25)
    ml_transform = cal.get_probability_transform("moneyline")
    assert ml_transform is not None, "Moneyline transform not found"
    
    # Test that transform changes probabilities
    test_prob = 0.65
    adjusted = ml_transform(test_prob)
    
    # Should be different from raw probability
    assert abs(adjusted - test_prob) > 0.01, "Transform not applying changes"
    
    # Should be in valid probability range
    assert 0.0 < adjusted < 1.0, f"Invalid adjusted probability: {adjusted}"
    
    print(f"✓ Moneyline transform: {test_prob:.3f} → {adjusted:.3f}")
    
    # Test spread transform (different platt coefficients)
    spread_transform = cal.get_probability_transform("spread")
    assert spread_transform is not None, "Spread transform not found"
    
    spread_adjusted = spread_transform(test_prob)
    # Should be different from moneyline (different coefficients)
    assert abs(spread_adjusted - adjusted) > 0.001, "Spread and moneyline transforms identical"
    
    print(f"✓ Spread transform: {test_prob:.3f} → {spread_adjusted:.3f}")
    
    # Test total transform
    total_transform = cal.get_probability_transform("total")
    assert total_transform is not None, "Total transform not found"
    
    total_adjusted = total_transform(test_prob)
    print(f"✓ Total transform: {test_prob:.3f} → {total_adjusted:.3f}")
    
    # Test player prop transform
    prop_transform = cal.get_probability_transform("player_prop_points")
    assert prop_transform is not None, "Player prop transform not found"
    
    prop_adjusted = prop_transform(test_prob)
    print(f"✓ Player prop transform: {test_prob:.3f} → {prop_adjusted:.3f}")
    
    print("✅ Platt + Shrinkage Transforms passed")
    return True


def test_kelly_staking_parameters():
    """Test Kelly staking parameters from ValidationLab"""
    print("\n=== Test: Kelly Staking Parameters ===")
    
    from config.calibration_loader import CalibrationLoader
    
    cal = CalibrationLoader("NBA")
    
    # Get kelly staking config
    kelly_staking = cal.get_kelly_staking()
    
    # Verify expected values
    assert kelly_staking["method"] == "fractional", f"Expected fractional, got {kelly_staking['method']}"
    assert kelly_staking["fraction"] == 0.25, f"Expected 0.25, got {kelly_staking['fraction']}"
    assert kelly_staking["max_stake"] == 0.05, f"Expected 0.05, got {kelly_staking['max_stake']}"
    assert kelly_staking["min_stake"] == 0.01, f"Expected 0.01, got {kelly_staking['min_stake']}"
    
    print(f"✓ Kelly method: {kelly_staking['method']}")
    print(f"✓ Kelly fraction: {kelly_staking['fraction']}")
    print(f"✓ Max stake: {kelly_staking['max_stake']}")
    print(f"✓ Min stake: {kelly_staking['min_stake']}")
    
    # Verify tier multipliers
    tier_mult = kelly_staking["tier_multipliers"]
    assert tier_mult["high_confidence"] == 1.0, "High confidence multiplier incorrect"
    assert tier_mult["medium_confidence"] == 0.5, "Medium confidence multiplier incorrect"
    assert tier_mult["low_confidence"] == 0.25, "Low confidence multiplier incorrect"
    
    print(f"✓ Tier multipliers: {tier_mult}")
    
    print("✅ Kelly Staking Parameters passed")
    return True


def test_variance_scalars():
    """Test variance scalars are available"""
    print("\n=== Test: Variance Scalars ===")
    
    from config.calibration_loader import CalibrationLoader
    
    cal = CalibrationLoader("NBA")
    
    variance = cal.get_variance_scalars()
    
    assert "NBA" in variance, "NBA not in variance scalars"
    assert variance["NBA"] == 1.0, f"Expected 1.0, got {variance['NBA']}"
    
    print(f"✓ Variance scalars loaded: {variance}")
    
    print("✅ Variance Scalars passed")
    return True


def test_test_performance_metrics():
    """Test that test performance metrics are accessible"""
    print("\n=== Test: Test Performance Metrics ===")
    
    from config.calibration_loader import CalibrationLoader
    
    cal = CalibrationLoader("NBA")
    
    perf = cal.get_test_performance()
    
    assert perf is not None, "Test performance metrics not found"
    
    # Verify key metrics from ValidationLab calibration
    assert perf["hit_rate"] == 0.60, f"Expected 0.60, got {perf['hit_rate']}"
    assert abs(perf["roi"] - 0.281) < 0.001, f"Expected 0.281, got {perf['roi']}"
    assert perf["sharpe_ratio"] == 0.25, f"Expected 0.25, got {perf['sharpe_ratio']}"
    
    print(f"✓ Hit rate: {perf['hit_rate']:.1%}")
    print(f"✓ ROI: {perf['roi']:.1%}")
    print(f"✓ Sharpe ratio: {perf['sharpe_ratio']:.2f}")
    print(f"✓ Total bets: {perf['total_bets']}")
    print(f"✓ Brier score: {perf['brier_score']:.4f}")
    
    print("✅ Test Performance Metrics passed")
    return True


def test_validation_lab_compatibility():
    """Test complete workflow with ValidationLab calibration"""
    print("\n=== Test: ValidationLab Compatibility ===")
    
    from outputs.bet_recorder import BetRecorder
    from config.calibration_loader import CalibrationLoader
    from omega.betting.odds_eval import implied_probability
    
    # Load NBA calibration
    cal = CalibrationLoader("NBA")
    print(f"✓ Loaded calibration version: {cal.get_version()}")
    
    # Simulate a bet evaluation with calibrated parameters
    date = datetime.now().strftime("%Y-%m-%d")
    game_id = "test_validation_001"
    market_type = "spread"  # Using spread with high threshold (9.5%)
    market_odds = -110
    raw_model_prob = 0.65
    
    # Apply calibrated probability transform
    transform = cal.get_probability_transform(market_type)
    if transform:
        model_prob = transform(raw_model_prob)
        print(f"✓ Applied {market_type} transform: {raw_model_prob:.3f} → {model_prob:.3f}")
    else:
        model_prob = raw_model_prob
    
    # Calculate edge with calibrated parameters
    market_prob = implied_probability(market_odds)
    edge = model_prob - market_prob
    edge_threshold = cal.get_edge_threshold(market_type)
    
    print(f"✓ Edge: {edge:.3f} (threshold: {edge_threshold:.3f})")
    
    # Get Kelly staking parameters
    kelly_staking = cal.get_kelly_staking()
    kelly_frac = kelly_staking["fraction"]
    max_stake = kelly_staking["max_stake"]
    
    print(f"✓ Kelly fraction: {kelly_frac}")
    print(f"✓ Max stake: {max_stake}")
    
    # If bet qualifies, record it with calibrated parameters
    if edge >= edge_threshold:
        print(f"✓ Bet qualifies (edge {edge:.1%} >= threshold {edge_threshold:.1%})")
        
        bet_id = f"{game_id}_{market_type}_test"
        
        filepath = BetRecorder.record_bet(
            date=date,
            league="NBA",
            bet_id=bet_id,
            game_id=game_id,
            game_date=date,
            market_type=market_type,
            recommendation="AWAY",
            edge=edge,
            model_probability=model_prob,
            market_probability=market_prob,
            stake=2.5,  # Example stake
            odds=market_odds,
            line=-3.5,
            edge_threshold=edge_threshold,
            kelly_fraction=kelly_frac,
            confidence="medium",
            calibration_version=cal.get_version(),
            metadata={
                "test": True,
                "raw_model_prob": raw_model_prob,
                "transform_applied": True
            }
        )
        
        print(f"✓ Bet recorded with calibration v{cal.get_version()}")
    else:
        print(f"✓ Bet filtered out correctly (edge {edge:.1%} < threshold {edge_threshold:.1%})")
    
    print("✅ ValidationLab Compatibility passed")
    return True


def test_edge_threshold_differences():
    """Test that different market types have correct calibrated thresholds"""
    print("\n=== Test: Market-Specific Edge Thresholds ===")
    
    from config.calibration_loader import CalibrationLoader
    
    cal = CalibrationLoader("NBA")
    
    # Get thresholds for different markets
    ml_threshold = cal.get_edge_threshold("moneyline")
    spread_threshold = cal.get_edge_threshold("spread")
    total_threshold = cal.get_edge_threshold("total")
    
    # Verify spread has highest threshold (9.5% from ValidationLab)
    assert spread_threshold > ml_threshold, "Spread threshold should be higher than moneyline"
    assert spread_threshold > total_threshold, "Spread threshold should be higher than total"
    
    # Verify total has lowest threshold (1.0% from ValidationLab)
    assert total_threshold < ml_threshold, "Total threshold should be lower than moneyline"
    
    print(f"✓ Moneyline: {ml_threshold:.1%}")
    print(f"✓ Spread: {spread_threshold:.1%} (highest)")
    print(f"✓ Total: {total_threshold:.1%} (lowest)")
    
    print("✅ Market-Specific Edge Thresholds passed")
    return True


def main():
    """Run all validation tests"""
    print("="*60)
    print("ValidationLab Calibration Parameters Validation")
    print("="*60)
    
    tests = [
        ("Calibrated Edge Thresholds", test_calibrated_edge_thresholds),
        ("Platt + Shrinkage Transforms", test_platt_shrink_transforms),
        ("Kelly Staking Parameters", test_kelly_staking_parameters),
        ("Variance Scalars", test_variance_scalars),
        ("Test Performance Metrics", test_test_performance_metrics),
        ("Market-Specific Thresholds", test_edge_threshold_differences),
        ("ValidationLab Compatibility", test_validation_lab_compatibility),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*60)
    
    if failed == 0:
        print("\n✅ All ValidationLab calibration parameters validated!")
        print("\n🎉 OmegaSportsAgent is properly configured with:")
        print("   • Calibrated edge thresholds (ML: 3%, Spread: 9.5%, Total: 1%)")
        print("   • Platt + shrinkage probability transforms")
        print("   • Kelly staking parameters (fraction: 0.25)")
        print("   • ValidationLab format compatibility")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
