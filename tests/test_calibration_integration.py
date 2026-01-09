#!/usr/bin/env python3
"""
Test script for Bet Recorder and Calibration Loader modules.

Validates:
- BetRecorder can record bets to daily JSON files
- CalibrationLoader can load calibration packs
- Module imports work correctly
- Coexistence with existing logging utilities
"""

import os
import sys
import json
from datetime import datetime

def test_bet_recorder():
    """Test BetRecorder functionality"""
    print("\n=== Test: BetRecorder ===")
    
    from outputs.bet_recorder import BetRecorder
    
    # Record a test bet
    test_date = "2026-01-05"
    filepath = BetRecorder.record_bet(
        date=test_date,
        league="NBA",
        bet_id="test_bet_001",
        game_id="401234567",
        game_date=test_date,
        market_type="moneyline",
        recommendation="HOME",
        edge=0.055,
        model_probability=0.625,
        market_probability=0.570,
        stake=10.0,
        odds=-150,
        calibration_version="nba_v1.0",
        confidence="medium",
        metadata={"test": True}
    )
    
    print(f"✓ Bet recorded to: {filepath}")
    
    # Verify file exists
    assert os.path.exists(filepath), "Recommendations file not created"
    print(f"✓ File exists")
    
    # Load and verify content
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    assert data["date"] == test_date, "Date mismatch"
    assert data["league"] == "NBA", "League mismatch"
    assert len(data["bets"]) >= 1, "No bets in file"
    assert data["bets"][-1]["bet_id"] == "test_bet_001", "Bet ID mismatch"
    assert abs(data["bets"][-1]["edge"] - 0.055) < 0.001, "Edge calculation error"
    print(f"✓ File content validated")
    
    # Test retrieval
    bets = BetRecorder.get_bets_for_date(test_date)
    assert len(bets) >= 1, "Failed to retrieve bets"
    print(f"✓ Bet retrieval works")
    
    # Record another bet to same file
    filepath2 = BetRecorder.record_bet(
        date=test_date,
        league="NBA",
        bet_id="test_bet_002",
        game_id="401234568",
        game_date=test_date,
        market_type="spread",
        recommendation="AWAY",
        edge=0.042,
        model_probability=0.556,
        market_probability=0.514,
        stake=7.5,
        odds=-110,
        line=-3.5,
        calibration_version="nba_v1.0"
    )
    
    assert filepath2 == filepath, "Different filepath for same date"
    
    # Verify append worked
    bets = BetRecorder.get_bets_for_date(test_date)
    assert len(bets) >= 2, "Append failed"
    print(f"✓ Append to existing file works ({len(bets)} bets total)")
    
    print("✅ BetRecorder passed")
    return True


def test_calibration_loader():
    """Test CalibrationLoader functionality"""
    print("\n=== Test: CalibrationLoader ===")
    
    from config.calibration_loader import CalibrationLoader
    
    # Load NBA calibration
    cal = CalibrationLoader("NBA")
    print(f"✓ CalibrationLoader initialized for NBA")
    
    # Check version
    version = cal.get_version()
    print(f"✓ Loaded version: {version}")
    
    # Check if using defaults or pack
    if cal.is_using_defaults():
        print(f"⚠ Using default fallback values (pack not found)")
    else:
        print(f"✓ Using calibration pack: {cal.pack_name}")
    
    # Get edge thresholds
    ml_threshold = cal.get_edge_threshold("moneyline")
    assert 0.0 < ml_threshold < 1.0, "Invalid edge threshold"
    print(f"✓ Moneyline threshold: {ml_threshold}")
    
    spread_threshold = cal.get_edge_threshold("spread")
    print(f"✓ Spread threshold: {spread_threshold}")
    
    prop_threshold = cal.get_edge_threshold("player_prop_points")
    print(f"✓ Player prop points threshold: {prop_threshold}")
    
    default_threshold = cal.get_edge_threshold("unknown_market")
    print(f"✓ Default threshold: {default_threshold}")
    
    # Get Kelly parameters
    kelly = cal.get_kelly_fraction()
    assert 0.0 < kelly <= 1.0, "Invalid Kelly fraction"
    print(f"✓ Kelly fraction: {kelly}")
    
    kelly_policy = cal.get_kelly_policy()
    print(f"✓ Kelly policy: {kelly_policy}")
    
    # Test probability transforms
    transform = cal.get_probability_transform("moneyline")
    if transform:
        test_prob = 0.65
        adjusted_prob = transform(test_prob)
        print(f"✓ Transform test: {test_prob:.3f} → {adjusted_prob:.3f}")
        assert 0.0 < adjusted_prob < 1.0, "Invalid transformed probability"
    else:
        print(f"⚠ No transform defined for moneyline")
    
    # Get all transforms
    all_transforms = cal.get_probability_transforms()
    print(f"✓ Transform configs available: {len(all_transforms)} market types")
    
    print("✅ CalibrationLoader passed")
    return True


def test_module_imports():
    """Test that new modules import without breaking existing ones"""
    print("\n=== Test: Module Imports ===")
    
    # Test new modules
    from outputs.bet_recorder import BetRecorder
    from config.calibration_loader import CalibrationLoader
    print("✓ New modules import successfully")
    
    # Test existing utilities still work
    from omega.utilities.data_logging import log_bet_recommendation, get_log_directory
    from omega.utilities.sandbox_persistence import OmegaCacheLogger
    print("✓ Existing utilities still import")
    
    # Test betting modules
    from omega.betting.odds_eval import edge_percentage, implied_probability
    from omega.betting.kelly_staking import recommend_stake
    print("✓ Betting modules still import")
    
    print("✅ Module Imports passed")
    return True


def test_integration_example():
    """Test integration example showing how to use both modules together"""
    print("\n=== Test: Integration Example ===")
    
    from outputs.bet_recorder import BetRecorder
    from config.calibration_loader import CalibrationLoader
    from omega.betting.odds_eval import implied_probability, edge_percentage
    
    # Load calibration for NBA
    cal = CalibrationLoader("NBA")
    print(f"✓ Loaded calibration version: {cal.get_version()}")
    
    # Simulate a betting decision
    market_odds = -150
    model_prob = 0.65
    market_type = "moneyline"
    
    # Get calibration parameters
    edge_threshold = cal.get_edge_threshold(market_type)
    kelly_frac = cal.get_kelly_fraction()
    
    # Apply probability transform if available
    transform = cal.get_probability_transform(market_type)
    if transform:
        adjusted_prob = transform(model_prob)
        print(f"✓ Applied transform: {model_prob:.3f} → {adjusted_prob:.3f}")
    else:
        adjusted_prob = model_prob
    
    # Calculate edge
    market_prob = implied_probability(market_odds)
    edge = adjusted_prob - market_prob
    
    print(f"✓ Model prob: {adjusted_prob:.3f}")
    print(f"✓ Market prob: {market_prob:.3f}")
    print(f"✓ Edge: {edge:.3f} (threshold: {edge_threshold:.3f})")
    
    # Determine if bet qualifies
    qualifies = edge >= edge_threshold
    
    if qualifies:
        print(f"✓ Bet qualifies (edge {edge:.1%} >= threshold {edge_threshold:.1%})")
        
        # Record the bet
        filepath = BetRecorder.record_bet(
            date="2026-01-05",
            league="NBA",
            bet_id="integration_test_001",
            game_id="401234569",
            game_date="2026-01-05",
            market_type=market_type,
            recommendation="HOME",
            edge=edge,
            model_probability=adjusted_prob,
            market_probability=market_prob,
            stake=5.0,
            odds=market_odds,
            edge_threshold=edge_threshold,
            kelly_fraction=kelly_frac,
            confidence="medium",
            calibration_version=cal.get_version()
        )
        print(f"✓ Bet recorded to: {filepath}")
    else:
        print(f"✓ Bet does not qualify (edge too low)")
    
    print("✅ Integration Example passed")
    return True


def main():
    """Run all tests"""
    print("="*60)
    print("Continual Calibration Integration Test Suite")
    print("="*60)
    
    tests = [
        ("Module Imports", test_module_imports),
        ("BetRecorder", test_bet_recorder),
        ("CalibrationLoader", test_calibration_loader),
        ("Integration Example", test_integration_example),
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
        print("\n✅ All tests passed!")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
