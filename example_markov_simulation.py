#!/usr/bin/env python3
"""
Example: Markov Play-by-Play Simulation for Player Props

This script demonstrates how to use the Markov simulation engine to analyze
player props with detailed play-by-play modeling. The Markov engine simulates
games at the possession/play level, tracking individual player involvement
and stat accumulation.

Usage:
    python example_markov_simulation.py
"""

import os
import json
from datetime import datetime


def main():
    """Run a Markov simulation example for player props."""
    
    print("="*70)
    print("OmegaSports Markov Simulation Example")
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
    
    from omega.api.markov_analysis import analyze_player_prop_markov
    from omega.simulation.markov_engine import MarkovSimulator
    
    print("✓ Markov simulation modules imported")
    
    # ============================================================
    # STEP 3: Define Player and Team Data
    # ============================================================
    print("\nSTEP 3: Define Player Data")
    print("-"*70)
    
    # Player we want to analyze
    player = {
        "name": "Jayson Tatum",
        "team": "Boston Celtics",
        "usage_rate": 0.32,  # 32% of possessions when on court
        "pts_mean": 27.5,
        "reb_mean": 8.2,
        "ast_mean": 4.8,
        "fg_pct": 0.47,
        "three_pt_pct": 0.37
    }
    
    # Teammates
    teammates = [
        {
            "name": "Jaylen Brown",
            "team": "Boston Celtics",
            "usage_rate": 0.28,
            "pts_mean": 23.1
        },
        {
            "name": "Kristaps Porzingis",
            "team": "Boston Celtics",
            "usage_rate": 0.20,
            "pts_mean": 19.8
        },
        {
            "name": "Jrue Holiday",
            "team": "Boston Celtics",
            "usage_rate": 0.16,
            "pts_mean": 12.5
        }
    ]
    
    # Opponents
    opponents = [
        {
            "name": "Tyrese Haliburton",
            "team": "Indiana Pacers",
            "usage_rate": 0.25,
            "pts_mean": 22.4
        },
        {
            "name": "Pascal Siakam",
            "team": "Indiana Pacers",
            "usage_rate": 0.23,
            "pts_mean": 20.8
        },
        {
            "name": "Myles Turner",
            "team": "Indiana Pacers",
            "usage_rate": 0.18,
            "pts_mean": 16.5
        }
    ]
    
    print(f"✓ Player: {player['name']}")
    print(f"  Usage: {player['usage_rate']:.1%}")
    print(f"  Avg Points: {player['pts_mean']}")
    print(f"✓ Teammates: {len(teammates)}")
    print(f"✓ Opponents: {len(opponents)}")
    
    # ============================================================
    # STEP 4: Define Betting Market
    # ============================================================
    print("\nSTEP 4: Define Prop Bet")
    print("-"*70)
    
    prop_type = "pts"  # Points prop
    market_line = 27.5  # Over/Under line
    over_odds = -110    # American odds
    under_odds = -110
    
    print(f"✓ Prop: {player['name']} Points")
    print(f"  Line: {market_line}")
    print(f"  Over odds: {over_odds}")
    print(f"  Under odds: {under_odds}")
    
    # ============================================================
    # STEP 5: Optional Team Context (for more accurate simulation)
    # ============================================================
    print("\nSTEP 5: Team Context (Optional)")
    print("-"*70)
    
    home_context = {
        "name": "Boston Celtics",
        "off_rating": 118.5,  # Points per 100 possessions
        "def_rating": 110.2,  # Points allowed per 100 possessions
        "pace": 99.5,         # Possessions per game
        "fg_pct": 0.47,
        "three_pt_pct": 0.38
    }
    
    away_context = {
        "name": "Indiana Pacers",
        "off_rating": 120.1,
        "def_rating": 112.5,
        "pace": 101.3,
        "fg_pct": 0.48,
        "three_pt_pct": 0.37
    }
    
    print(f"✓ Home: {home_context['name']}")
    print(f"  Off Rating: {home_context['off_rating']}")
    print(f"  Def Rating: {home_context['def_rating']}")
    print(f"  Pace: {home_context['pace']}")
    print(f"✓ Away: {away_context['name']}")
    print(f"  Off Rating: {away_context['off_rating']}")
    print(f"  Def Rating: {away_context['def_rating']}")
    print(f"  Pace: {away_context['pace']}")
    
    # ============================================================
    # STEP 6: Run Markov Simulation
    # ============================================================
    print("\nSTEP 6: Run Markov Simulation")
    print("-"*70)
    print("Running 10,000 play-by-play simulations...")
    print("(This models each possession and player involvement)")
    
    result = analyze_player_prop_markov(
        player=player,
        teammates=teammates,
        opponents=opponents,
        prop_type=prop_type,
        market_line=market_line,
        over_odds=over_odds,
        under_odds=under_odds,
        league="NBA",
        n_iter=10000,
        home_context=home_context,
        away_context=away_context
    )
    
    print("✓ Simulation complete")
    
    # ============================================================
    # STEP 7: Display Results
    # ============================================================
    print("\nSTEP 7: Analysis Results")
    print("-"*70)
    
    print(f"\nPlayer: {result['player_name']}")
    print(f"Prop: {result['prop_type'].upper()} {result['market_line']}")
    print(f"League: {result['league']}")
    print(f"Iterations: {result['simulation_iterations']:,}")
    
    print(f"\n📊 SIMULATION STATISTICS:")
    print(f"  Projected Mean: {result['projected_mean']:.2f}")
    print(f"  Projected Std Dev: {result['projected_std']:.2f}")
    print(f"  Projected Range: {result['projected_min']:.1f} - {result['projected_max']:.1f}")
    
    print(f"\n🎲 PROBABILITIES:")
    print(f"  Over Probability: {result['over_prob']:.2%}")
    print(f"  Under Probability: {result['under_prob']:.2%}")
    print(f"  Push Probability: {result['push_prob']:.2%}")
    
    print(f"\n📈 MARKET ANALYSIS:")
    print(f"  Over Implied Prob: {result['over_implied_prob']:.2%}")
    print(f"  Under Implied Prob: {result['under_implied_prob']:.2%}")
    print(f"  Over Edge: {result['over_edge_pct']:.2f}%")
    print(f"  Under Edge: {result['under_edge_pct']:.2f}%")
    print(f"  Over EV: {result['over_ev_pct']:.2f}%")
    print(f"  Under EV: {result['under_ev_pct']:.2f}%")
    
    print(f"\n💡 RECOMMENDATION:")
    print(f"  Recommended Bet: {result['recommended_bet'].upper()}")
    print(f"  Confidence Tier: {result['confidence_tier']}")
    print(f"  Best Edge: {result['best_edge_pct']:.2f}%")
    print(f"  Best EV: {result['best_ev_pct']:.2f}%")
    
    if result.get('stake_recommendation'):
        stake = result['stake_recommendation']
        print(f"\n💰 STAKING (Kelly Criterion):")
        print(f"  Recommended Units: {stake.get('units', 0):.2f}")
        print(f"  Amount ($1000 bank): ${stake.get('amount', 0):.2f}")
        print(f"  % of Bankroll: {stake.get('pct_bankroll', 0):.2f}%")
    
    # ============================================================
    # STEP 8: Save Results
    # ============================================================
    print("\nSTEP 8: Save Results")
    print("-"*70)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    output_file = f"outputs/markov_simulation_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"✓ Results saved to: {output_file}")
    
    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    if result['recommended_bet'] != 'pass':
        print(f"\n✅ BET RECOMMENDED: {result['player_name']} {result['prop_type'].upper()} {result['recommended_bet'].upper()}")
        print(f"   Line: {result['market_line']}")
        print(f"   Edge: {result['best_edge_pct']:.2f}%")
        print(f"   Confidence: Tier {result['confidence_tier']}")
    else:
        print(f"\n❌ NO BET: Edge below threshold")
    
    print(f"\nThe Markov simulation modeled the game play-by-play, tracking:")
    print(f"  • {result['simulation_iterations']:,} game simulations")
    print(f"  • ~200 possessions per game")
    print(f"  • Individual player involvement on each play")
    print(f"  • Shot selection based on usage rates")
    print(f"  • Team context (pace, efficiency, defense)")
    
    print("\n" + "="*70)
    print("✅ Example complete! Check outputs/ for full results.")
    print("="*70)


if __name__ == "__main__":
    main()
