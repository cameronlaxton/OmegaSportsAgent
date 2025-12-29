#!/usr/bin/env python3
"""
Test script to validate OmegaSports engine is working correctly.
This script tests module imports, data structures, and basic simulation.
"""

import sys
import os

def test_environment_setup():
    """
    Test 1: Environment Setup
    
    Validates:
    - Python version is 3.10 or higher
    - Required directories can be created (logs/, outputs/, data/logs/, data/outputs/)
    """
    print("\n=== Test 1: Environment Setup ===")
    
    # Check Python version
    py_version = sys.version_info
    assert py_version >= (3, 10), f"Python 3.10+ required (found {py_version.major}.{py_version.minor})"
    print(f"✓ Python {py_version.major}.{py_version.minor}")
    
    # Check directories
    for directory in ["logs", "outputs", "data/logs", "data/outputs"]:
        os.makedirs(directory, exist_ok=True)
        assert os.path.exists(directory), f"Failed to create {directory}"
    print("✓ All directories created")
    
    return True


def test_module_imports():
    """Test 2: Module Imports"""
    print("\n=== Test 2: Module Imports ===")
    
    # Foundation
    from omega.schema import GameData, BettingLine
    from omega.foundation.model_config import get_edge_thresholds
    from omega.foundation.league_config import get_league_config
    from omega.foundation.core_abstractions import Team
    print("✓ Foundation modules (4/4)")
    
    # Data
    from omega.data.schedule_api import get_todays_games
    from omega.data.stats_scraper import get_team_stats
    from omega.data.odds_scraper import get_upcoming_games
    from omega.data.injury_api import get_injured_players
    print("✓ Data modules (4/4)")
    
    # Simulation
    from omega.simulation.simulation_engine import run_game_simulation
    from omega.simulation.correlated_simulation import simulate_correlated_markets
    print("✓ Simulation modules (2/2)")
    
    # Betting
    from omega.betting.odds_eval import edge_percentage, implied_probability
    from omega.betting.kelly_staking import recommend_stake
    print("✓ Betting modules (2/2)")
    
    # Utilities
    from omega.utilities.output_formatter import format_full_output
    from omega.utilities.data_logging import log_bet_recommendation
    from omega.utilities.sandbox_persistence import OmegaCacheLogger
    print("✓ Utility modules (3/3)")
    
    # Workflows
    from omega.workflows.morning_bets import run_morning_workflow
    print("✓ Workflow modules (1/1)")
    
    # Scraper
    from scraper_engine import fetch_sports_markdown, validate_game_data
    print("✓ Scraper engine (2/2)")
    
    return True


def test_schema_validation():
    """Test 3: Schema Validation"""
    print("\n=== Test 3: Schema Validation ===")
    
    from omega.schema import GameData, BettingLine
    from scraper_engine import validate_game_data
    
    # Create a game
    game = GameData(
        sport="NBA",
        league="NBA",
        home_team="Boston Celtics",
        away_team="Indiana Pacers",
        moneyline={
            "home": BettingLine(sportsbook="DraftKings", price=-150),
            "away": BettingLine(sportsbook="DraftKings", price=130)
        },
        spread={
            "home": BettingLine(sportsbook="DraftKings", price=-110, value=-4.5),
            "away": BettingLine(sportsbook="DraftKings", price=-110, value=4.5)
        },
        total={
            "over": BettingLine(sportsbook="DraftKings", price=-110, value=220.5),
            "under": BettingLine(sportsbook="DraftKings", price=-110, value=220.5)
        }
    )
    print(f"✓ Game created: {game.away_team} @ {game.home_team}")
    
    # Validate
    is_valid, result = validate_game_data(game.model_dump())
    assert is_valid, f"Validation failed: {result}"
    print("✓ Game data validated")
    
    # Test odds helpers
    home_ml = game.moneyline["home"].price
    assert home_ml == -150
    print(f"✓ Moneyline odds: {home_ml}")
    
    spread_val = game.get_spread_value()
    assert spread_val == -4.5
    print(f"✓ Spread: {spread_val}")
    
    total_val = game.get_total_value()
    assert total_val == 220.5
    print(f"✓ Total: {total_val}")
    
    return True


def test_simulation():
    """Test 4: Basic Simulation"""
    print("\n=== Test 4: Basic Simulation ===")
    
    from omega.simulation.simulation_engine import run_game_simulation
    
    # Define projection
    projection = {
        "off_rating": {
            "Boston Celtics": 118.5,
            "Indiana Pacers": 115.2
        },
        "def_rating": {
            "Boston Celtics": 110.2,
            "Indiana Pacers": 112.5
        },
        "pace": {
            "Boston Celtics": 99.5,
            "Indiana Pacers": 101.3
        },
        "league": "NBA",
        "variance_scalar": 1.0
    }
    print("✓ Projection data prepared")
    
    # Run simulation
    result = run_game_simulation(projection, n_iter=1000, league="NBA")
    print(f"✓ Simulation complete (1000 iterations)")
    
    # Validate results (simulation returns team_a_wins, team_b_wins, true_prob_a, etc.)
    assert "true_prob_a" in result, "Missing true_prob_a"
    assert "true_prob_b" in result, "Missing true_prob_b"
    assert 0 <= result["true_prob_a"] <= 1, "Invalid probability"
    
    print(f"  Team A Win: {result['true_prob_a']:.2%}")
    print(f"  Team B Win: {result['true_prob_b']:.2%}")
    print(f"  Team A Wins: {result.get('team_a_wins', 0)}")
    print(f"  Team B Wins: {result.get('team_b_wins', 0)}")
    
    return True


def test_betting_analysis():
    """Test 5: Betting Analysis"""
    print("\n=== Test 5: Betting Analysis ===")
    
    from omega.betting.odds_eval import implied_probability, edge_percentage, expected_value_percent
    from omega.foundation.model_config import get_edge_thresholds
    
    # Test odds conversion
    odds = -150
    impl_prob = implied_probability(odds)
    assert 0 < impl_prob < 1, "Invalid implied probability"
    print(f"✓ Implied probability from {odds}: {impl_prob:.2%}")
    
    # Test edge calculation
    model_prob = 0.65
    edge = edge_percentage(model_prob, impl_prob)
    print(f"✓ Edge: {edge:.2f}%")
    
    # Test EV calculation
    ev = expected_value_percent(model_prob, odds)
    print(f"✓ Expected Value: {ev:.2f}%")
    
    # Test threshold
    thresholds = get_edge_thresholds()
    assert "min_edge_pct" in thresholds, "Missing min_edge_pct"
    print(f"✓ Edge thresholds loaded: min_edge={thresholds['min_edge_pct']}%")
    
    return True


def test_configuration():
    """Test 6: Configuration"""
    print("\n=== Test 6: Configuration ===")
    
    from omega.foundation.model_config import get_edge_thresholds, get_simulation_params
    from omega.foundation.league_config import get_league_config
    
    # Test model config
    edge_thresh = get_edge_thresholds()
    assert isinstance(edge_thresh, dict), "Invalid edge thresholds"
    print(f"✓ Edge thresholds: min_edge={edge_thresh['min_edge_pct']}%")
    
    sim_params = get_simulation_params()
    assert "default_iterations" in sim_params, "Missing simulation params"
    print(f"✓ Simulation params: default_iterations={sim_params['default_iterations']}")
    
    # Test league config
    nba_config = get_league_config("NBA")
    assert "periods" in nba_config, "Invalid NBA config"
    assert nba_config["periods"] == 4, "NBA should have 4 periods"
    print(f"✓ NBA config loaded: {nba_config['periods']} periods")
    
    return True


def test_main_cli():
    """Test 7: Main CLI"""
    print("\n=== Test 7: Main CLI ===")
    
    import subprocess
    
    # Test --help
    result = subprocess.run(
        ["python", "main.py", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, "main.py --help failed"
    assert "OmegaSports Headless Simulation Engine" in result.stdout
    print("✓ main.py --help works")
    
    return True


def run_all_tests():
    """Run all tests"""
    print("="*60)
    print("OmegaSports Engine Test Suite")
    print("="*60)
    
    tests = [
        ("Environment Setup", test_environment_setup),
        ("Module Imports", test_module_imports),
        ("Schema Validation", test_schema_validation),
        ("Simulation", test_simulation),
        ("Betting Analysis", test_betting_analysis),
        ("Configuration", test_configuration),
        ("Main CLI", test_main_cli),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {name} passed")
        except Exception as e:
            failed += 1
            print(f"❌ {name} failed: {e}")
    
    print("\n" + "="*60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*60)
    
    if failed == 0:
        print("\n✅ All tests passed! Engine is ready for use.")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed. Review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
