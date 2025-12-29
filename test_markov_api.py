#!/usr/bin/env python3
"""
Test script for Markov Simulation API

Tests the new Markov analysis API functionality.
"""

import sys
import os

def test_markov_api_imports():
    """Test that Markov API modules can be imported."""
    print("\n=== Test: Markov API Imports ===")
    
    try:
        from omega.api.markov_analysis import (
            analyze_player_prop_markov,
            analyze_multiple_props,
            simulate_game_with_markov,
            get_markov_prop_recommendations
        )
        print("✓ Markov API imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_markov_engine_imports():
    """Test that Markov engine modules can be imported."""
    print("\n=== Test: Markov Engine Imports ===")
    
    try:
        from omega.simulation.markov_engine import (
            MarkovSimulator,
            MarkovState,
            TransitionMatrix,
            run_markov_player_prop_simulation,
            validate_team_context,
            validate_player_context,
            validate_game_for_simulation
        )
        print("✓ Markov engine imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_player_context_validation():
    """Test player context validation."""
    print("\n=== Test: Player Context Validation ===")
    
    from omega.simulation.markov_engine import validate_player_context
    
    # Valid player
    valid_player = {
        "name": "Test Player",
        "pts_mean": 25.5
    }
    is_valid, issues = validate_player_context(valid_player)
    assert is_valid, f"Valid player failed validation: {issues}"
    print("✓ Valid player passed validation")
    
    # Invalid player (missing stats)
    invalid_player = {
        "name": "Test Player",
        "pts_mean": 0
    }
    is_valid, issues = validate_player_context(invalid_player)
    assert not is_valid, "Invalid player should fail validation"
    print("✓ Invalid player correctly rejected")
    
    return True


def test_team_context_validation():
    """Test team context validation."""
    print("\n=== Test: Team Context Validation ===")
    
    from omega.simulation.markov_engine import validate_team_context
    
    # Valid team
    valid_team = {
        "name": "Test Team",
        "off_rating": 115.0,
        "def_rating": 110.0,
        "pace": 100.0
    }
    is_valid, issues = validate_team_context(valid_team)
    assert is_valid, f"Valid team failed validation: {issues}"
    print("✓ Valid team passed validation")
    
    # Invalid team (missing stats)
    invalid_team = {
        "name": "Test Team",
        "off_rating": 0,
        "def_rating": 0,
        "pace": 0
    }
    is_valid, issues = validate_team_context(invalid_team)
    assert not is_valid, "Invalid team should fail validation"
    print("✓ Invalid team correctly rejected")
    
    return True


def test_transition_matrix():
    """Test transition matrix creation."""
    print("\n=== Test: Transition Matrix ===")
    
    from omega.simulation.markov_engine import TransitionMatrix
    
    # Test NBA transitions
    nba_matrix = TransitionMatrix("NBA")
    probs = nba_matrix.get_transition_probs("possession")
    assert len(probs) > 0, "NBA transition matrix should have transitions"
    assert "two_point_make" in probs, "NBA should have two_point_make transition"
    print(f"✓ NBA transitions loaded: {len(probs)} outcomes")
    
    # Test NFL transitions
    nfl_matrix = TransitionMatrix("NFL")
    probs = nfl_matrix.get_transition_probs("play_type")
    assert len(probs) > 0, "NFL transition matrix should have transitions"
    assert "pass" in probs, "NFL should have pass transition"
    print(f"✓ NFL transitions loaded: {len(probs)} outcomes")
    
    return True


def test_markov_simulator_basic():
    """Test basic Markov simulator functionality."""
    print("\n=== Test: Markov Simulator Basic ===")
    
    from omega.simulation.markov_engine import MarkovSimulator
    
    # Create simple test players
    players = [
        {
            "name": "Player 1",
            "team": "Team A",
            "team_side": "home",
            "usage_rate": 0.30,
            "pts_mean": 25.0
        },
        {
            "name": "Player 2",
            "team": "Team B",
            "team_side": "away",
            "usage_rate": 0.25,
            "pts_mean": 20.0
        }
    ]
    
    # Create simulator
    simulator = MarkovSimulator("NBA", players)
    print("✓ Markov simulator created")
    
    # Run a single game
    state = simulator.simulate_game(n_possessions=50, seed=42)
    assert state is not None, "Game simulation should return state"
    assert state.league == "NBA", "State should have correct league"
    print(f"✓ Game simulated: Home {state.home_score:.0f}, Away {state.away_score:.0f}")
    
    # Check player stats were tracked
    assert len(state.player_stats) > 0, "Should have player stats"
    print(f"✓ Player stats tracked for {len(state.player_stats)} players")
    
    return True


def test_analyze_player_prop_basic():
    """Test basic player prop analysis."""
    print("\n=== Test: Analyze Player Prop ===")
    
    from omega.api.markov_analysis import analyze_player_prop_markov
    
    # Simple test data
    player = {
        "name": "Test Player",
        "team": "Test Team",
        "usage_rate": 0.30,
        "pts_mean": 25.0
    }
    
    teammates = [
        {"name": "Teammate", "team": "Test Team", "usage_rate": 0.20, "pts_mean": 15.0}
    ]
    
    opponents = [
        {"name": "Opponent", "team": "Opp Team", "usage_rate": 0.25, "pts_mean": 20.0}
    ]
    
    # Run analysis (with fewer iterations for speed)
    result = analyze_player_prop_markov(
        player=player,
        teammates=teammates,
        opponents=opponents,
        prop_type="pts",
        market_line=25.0,
        over_odds=-110,
        under_odds=-110,
        league="NBA",
        n_iter=100  # Use fewer iterations for testing
    )
    
    # Check result structure
    assert "player_name" in result, "Result should have player_name"
    assert "over_prob" in result, "Result should have over_prob"
    assert "under_prob" in result, "Result should have under_prob"
    assert "recommended_bet" in result, "Result should have recommended_bet"
    assert result["recommended_bet"] in ["over", "under", "pass"], "Recommendation should be valid"
    
    print(f"✓ Analysis complete: {result['recommended_bet']}")
    print(f"  Over prob: {result['over_prob']:.2%}")
    print(f"  Edge: {result.get('best_edge_pct', 0):.2f}%")
    
    return True


def main():
    """Run all tests."""
    print("="*70)
    print("Markov Simulation API Test Suite")
    print("="*70)
    
    tests = [
        ("Markov API Imports", test_markov_api_imports),
        ("Markov Engine Imports", test_markov_engine_imports),
        ("Player Context Validation", test_player_context_validation),
        ("Team Context Validation", test_team_context_validation),
        ("Transition Matrix", test_transition_matrix),
        ("Markov Simulator Basic", test_markov_simulator_basic),
        ("Analyze Player Prop", test_analyze_player_prop_basic),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"✗ {name} failed")
        except Exception as e:
            failed += 1
            print(f"✗ {name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*70)
    
    if failed > 0:
        print("\n❌ Some tests failed")
        sys.exit(1)
    else:
        print("\n✅ All Markov API tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
