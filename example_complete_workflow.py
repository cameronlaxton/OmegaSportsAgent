#!/usr/bin/env python3
"""
Example: Complete Betting Analysis Workflow

This script demonstrates a complete end-to-end workflow for analyzing
a sports matchup and generating betting recommendations.

Usage:
    python example_complete_workflow.py
"""

import os
import json
from datetime import datetime


def main():
    """Run a complete analysis workflow."""
    
    print("="*70)
    print("OmegaSports Complete Workflow Example")
    print("="*70)
    print()
    
    # ============================================================
    # STEP 1: Setup Environment
    # ============================================================
    print("STEP 1: Environment Setup")
    print("-"*70)
    
    os.makedirs("outputs", exist_ok=True)
    print("✓ Output directory ready")
    
    # ============================================================
    # STEP 2: Import Required Modules
    # ============================================================
    print("\nSTEP 2: Import Modules")
    print("-"*70)
    
    from omega.schema import GameData, BettingLine
    from omega.simulation.simulation_engine import run_game_simulation
    from omega.betting.odds_eval import implied_probability, edge_percentage, expected_value_percent
    from omega.foundation.model_config import get_edge_thresholds
    from scraper_engine import validate_game_data
    
    print("✓ All modules imported")
    
    # ============================================================
    # STEP 3: Define Game Data
    # ============================================================
    print("\nSTEP 3: Define Game Data")
    print("-"*70)
    
    # Create game with betting lines
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
    
    print(f"✓ Game: {game.away_team} @ {game.home_team}")
    print(f"  Moneyline: Home {game.moneyline['home'].price}, Away {game.moneyline['away'].price}")
    print(f"  Spread: {game.spread['home'].value}")
    print(f"  Total: {game.total['over'].value}")
    
    # Validate
    is_valid, _ = validate_game_data(game.model_dump())
    assert is_valid, "Game data validation failed"
    print("✓ Game data validated")
    
    # ============================================================
    # STEP 4: Prepare Team Projections
    # ============================================================
    print("\nSTEP 4: Team Projections")
    print("-"*70)
    
    # In a real scenario, these would come from stats_scraper.get_team_stats()
    # For this example, we use sample data
    projection = {
        "off_rating": {
            "Boston Celtics": 118.5,   # Points per 100 possessions (offense)
            "Indiana Pacers": 115.2
        },
        "def_rating": {
            "Boston Celtics": 110.2,   # Points allowed per 100 possessions
            "Indiana Pacers": 112.5
        },
        "pace": {
            "Boston Celtics": 99.5,    # Possessions per game
            "Indiana Pacers": 101.3
        },
        "league": "NBA",
        "variance_scalar": 1.0
    }
    
    print("✓ Projections prepared:")
    print(f"  Boston Celtics: Off={projection['off_rating']['Boston Celtics']}, Def={projection['def_rating']['Boston Celtics']}")
    print(f"  Indiana Pacers: Off={projection['off_rating']['Indiana Pacers']}, Def={projection['def_rating']['Indiana Pacers']}")
    
    # ============================================================
    # STEP 5: Run Monte Carlo Simulation
    # ============================================================
    print("\nSTEP 5: Run Simulation")
    print("-"*70)
    
    print("Running 10,000 iterations...")
    simulation = run_game_simulation(
        projection=projection,
        n_iter=10000,
        league="NBA"
    )
    
    # Extract results (simulation returns team_a, team_b based on projection order)
    # First team in projection dict is team_a (Boston Celtics)
    celtics_win_prob = simulation["true_prob_a"]
    pacers_win_prob = simulation["true_prob_b"]
    
    print(f"✓ Simulation complete")
    print(f"  Boston Celtics win probability: {celtics_win_prob:.2%}")
    print(f"  Indiana Pacers win probability: {pacers_win_prob:.2%}")
    print(f"  Simulation wins: Celtics {simulation['team_a_wins']}, Pacers {simulation['team_b_wins']}")
    
    # ============================================================
    # STEP 6: Analyze Moneyline Bet
    # ============================================================
    print("\nSTEP 6: Analyze Moneyline Bet")
    print("-"*70)
    
    # Celtics moneyline
    celtics_odds = game.moneyline["home"].price
    celtics_implied_prob = implied_probability(celtics_odds)
    celtics_edge = edge_percentage(celtics_win_prob, celtics_implied_prob)
    celtics_ev = expected_value_percent(celtics_win_prob, celtics_odds)
    
    print(f"Boston Celtics ML @ {celtics_odds}")
    print(f"  Model probability: {celtics_win_prob:.2%}")
    print(f"  Implied probability: {celtics_implied_prob:.2%}")
    print(f"  Edge: {celtics_edge:.2f}%")
    print(f"  Expected Value: {celtics_ev:.2f}%")
    
    # Pacers moneyline
    pacers_odds = game.moneyline["away"].price
    pacers_implied_prob = implied_probability(pacers_odds)
    pacers_edge = edge_percentage(pacers_win_prob, pacers_implied_prob)
    pacers_ev = expected_value_percent(pacers_win_prob, pacers_odds)
    
    print(f"\nIndiana Pacers ML @ {pacers_odds}")
    print(f"  Model probability: {pacers_win_prob:.2%}")
    print(f"  Implied probability: {pacers_implied_prob:.2%}")
    print(f"  Edge: {pacers_edge:.2f}%")
    print(f"  Expected Value: {pacers_ev:.2f}%")
    
    # ============================================================
    # STEP 7: Apply Edge Threshold Filter
    # ============================================================
    print("\nSTEP 7: Filter by Edge Threshold")
    print("-"*70)
    
    thresholds = get_edge_thresholds()
    min_edge = thresholds["min_edge_pct"]
    
    print(f"Minimum edge threshold: {min_edge}%")
    
    qualified_bets = []
    
    if celtics_edge >= min_edge:
        qualified_bets.append({
            "pick": f"Boston Celtics ML @ {celtics_odds}",
            "edge_pct": celtics_edge,
            "ev_pct": celtics_ev,
            "model_prob": celtics_win_prob
        })
        print(f"✅ Boston Celtics ML QUALIFIED (edge {celtics_edge:.2f}% >= {min_edge}%)")
    else:
        print(f"❌ Boston Celtics ML rejected (edge {celtics_edge:.2f}% < {min_edge}%)")
    
    if pacers_edge >= min_edge:
        qualified_bets.append({
            "pick": f"Indiana Pacers ML @ {pacers_odds}",
            "edge_pct": pacers_edge,
            "ev_pct": pacers_ev,
            "model_prob": pacers_win_prob
        })
        print(f"✅ Indiana Pacers ML QUALIFIED (edge {pacers_edge:.2f}% >= {min_edge}%)")
    else:
        print(f"❌ Indiana Pacers ML rejected (edge {pacers_edge:.2f}% < {min_edge}%)")
    
    # ============================================================
    # STEP 8: Generate Output
    # ============================================================
    print("\nSTEP 8: Generate Output")
    print("-"*70)
    
    output = {
        "game": {
            "matchup": f"{game.away_team} @ {game.home_team}",
            "sport": game.sport,
            "league": game.league
        },
        "simulation": {
            "iterations": 10000,
            "celtics_win_prob": celtics_win_prob,
            "pacers_win_prob": pacers_win_prob
        },
        "analysis": {
            "celtics_ml": {
                "odds": celtics_odds,
                "model_prob": celtics_win_prob,
                "implied_prob": celtics_implied_prob,
                "edge_pct": celtics_edge,
                "ev_pct": celtics_ev
            },
            "pacers_ml": {
                "odds": pacers_odds,
                "model_prob": pacers_win_prob,
                "implied_prob": pacers_implied_prob,
                "edge_pct": pacers_edge,
                "ev_pct": pacers_ev
            }
        },
        "qualified_bets": qualified_bets,
        "edge_threshold": min_edge,
        "generated_at": datetime.now().isoformat()
    }
    
    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"outputs/example_analysis_{timestamp}.json"
    
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"✓ Results saved to: {output_file}")
    
    # ============================================================
    # STEP 9: Display Recommendations
    # ============================================================
    print("\nSTEP 9: Final Recommendations")
    print("-"*70)
    
    if qualified_bets:
        print(f"\n🎯 Found {len(qualified_bets)} qualified bet(s):\n")
        for i, bet in enumerate(qualified_bets, 1):
            print(f"{i}. {bet['pick']}")
            print(f"   Edge: {bet['edge_pct']:.2f}% | EV: {bet['ev_pct']:.2f}%")
            print(f"   Model Probability: {bet['model_prob']:.2%}")
            print()
    else:
        print("\n❌ No qualified bets found (no edges above threshold)")
    
    print("="*70)
    print("Workflow Complete!")
    print("="*70)


if __name__ == "__main__":
    main()
