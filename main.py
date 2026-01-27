#!/usr/bin/env python3
"""
OmegaSportsAgent - Decision Support Engine

An on-demand analysis library for sports analytics. This module demonstrates
how to use the simulation engine programmatically.

This is NOT a scheduled script or betting bot. It is a library that calculates
probabilities and identifies edges for human decision-makers.

Example Usage:
    python main.py                          # Run example simulation
    python main.py --home "Lakers" --away "Warriors"
    python main.py --league NFL --home "Chiefs" --away "Bills"
    python main.py --json                   # Pure JSON output for machines
"""

import argparse
import json
import logging
import sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("omega")


def run_example_simulation(
    home_team: str,
    away_team: str,
    league: str = "NBA",
    json_output: bool = False,
) -> dict:
    """
    Run a single Monte Carlo game simulation and return structured analysis.

    This demonstrates the canonical way an LLM or external caller should use
    the OmegaSimulationEngine. Set json_output=True to suppress formatted
    printing and emit pure JSON to stdout.
    """
    from src.simulation.simulation_engine import OmegaSimulationEngine
    from src.betting.odds_eval import implied_probability, edge_percentage
    from src.betting.kelly_staking import recommend_stake

    engine = OmegaSimulationEngine()

    if not json_output:
        print(f"\n{'='*60}")
        print("OmegaSportsAgent - Decision Support Engine")
        print(f"{'='*60}")
        print(f"Matchup: {away_team} @ {home_team}")
        print(f"League:  {league}")
        print(f"Time:    {datetime.now().isoformat()}")
        print(f"{'='*60}\n")
        print("[1/3] Running Monte Carlo simulation...")

    sim_result = engine.run_fast_game_simulation(
        home_team=home_team,
        away_team=away_team,
        league=league,
        n_iterations=1000,
    )

    if not sim_result.get("success"):
        if not json_output:
            print(f"\n[SKIPPED] {sim_result.get('skip_reason', 'Unknown error')}")
            print("This game was skipped due to incomplete data.")
            print("The engine does NOT simulate with default values.\n")
        else:
            sys.stdout.write(json.dumps(sim_result, default=str) + "\n")
        return sim_result

    if not json_output:
        print("[2/3] Calculating probabilities...")

    true_prob_home = sim_result["home_win_prob"] / 100
    true_prob_away = sim_result["away_win_prob"] / 100

    example_odds_home = -150
    example_odds_away = +130

    market_implied_home = implied_probability(example_odds_home)
    market_implied_away = implied_probability(example_odds_away)

    edge_home = edge_percentage(true_prob_home, market_implied_home)
    edge_away = edge_percentage(true_prob_away, market_implied_away)

    if not json_output:
        print("[3/3] Applying Kelly Criterion...")

    example_bankroll = 1000.0
    stake_home = recommend_stake(
        true_prob=true_prob_home,
        odds=example_odds_home,
        bankroll=example_bankroll,
        confidence_tier="B",
    )
    stake_away = recommend_stake(
        true_prob=true_prob_away,
        odds=example_odds_away,
        bankroll=example_bankroll,
        confidence_tier="B",
    )

    analysis = {
        "matchup": f"{away_team} @ {home_team}",
        "league": league,
        "simulation": {
            "iterations": sim_result["iterations"],
            "home_win_prob": sim_result["home_win_prob"],
            "away_win_prob": sim_result["away_win_prob"],
            "predicted_spread": sim_result["predicted_spread"],
            "predicted_total": sim_result["predicted_total"],
            "predicted_home_score": sim_result["predicted_home_score"],
            "predicted_away_score": sim_result["predicted_away_score"],
        },
        "edge_analysis": {
            "home": {
                "team": home_team,
                "true_prob": round(true_prob_home, 3),
                "market_implied": round(market_implied_home, 3),
                "edge_pct": round(edge_home, 1),
                "example_odds": example_odds_home,
                "recommended_units": stake_home["units"],
                "kelly_fraction": stake_home["kelly_fraction"],
            },
            "away": {
                "team": away_team,
                "true_prob": round(true_prob_away, 3),
                "market_implied": round(market_implied_away, 3),
                "edge_pct": round(edge_away, 1),
                "example_odds": example_odds_away,
                "recommended_units": stake_away["units"],
                "kelly_fraction": stake_away["kelly_fraction"],
            },
        },
        "context": {
            "home_context": sim_result.get("home_context", {}),
            "away_context": sim_result.get("away_context", {}),
        },
        "metadata": {
            "analyzed_at": datetime.now().isoformat(),
            "engine_version": "2.0-dse",
            "note": "This is decision support data. Human makes final decision.",
        },
    }

    if not json_output:
        print(f"\n{'-'*60}")
        print("SIMULATION RESULTS")
        print(f"{'-'*60}")
        print(f"Iterations:        {analysis['simulation']['iterations']}")
        print(f"Home Win Prob:     {analysis['simulation']['home_win_prob']}%")
        print(f"Away Win Prob:     {analysis['simulation']['away_win_prob']}%")
        print(f"Predicted Spread:  {analysis['simulation']['predicted_spread']:+.1f}")
        print(f"Predicted Total:   {analysis['simulation']['predicted_total']:.1f}")

        print(f"\n{'-'*60}")
        print("EDGE ANALYSIS (vs example market odds)")
        print(f"{'-'*60}")

        for side in ["home", "away"]:
            edge_data = analysis["edge_analysis"][side]
            print(f"\n{edge_data['team']} ({side.upper()}):")
            print(f"  True Probability:   {edge_data['true_prob']*100:.1f}%")
            print(f"  Market Implied:     {edge_data['market_implied']*100:.1f}%")
            print(f"  Edge:               {edge_data['edge_pct']:+.1f}%")
            print(f"  Example Odds:       {edge_data['example_odds']:+d}")
            print(f"  Recommended Units:  {edge_data['recommended_units']:.2f}")

        print(f"\n{'-'*60}")
        print("DECISION SUPPORT SUMMARY")
        print(f"{'-'*60}")

        if edge_home > 3:
            print(f"[+EV] {home_team} shows {edge_home:.1f}% edge vs market")
        elif edge_away > 3:
            print(f"[+EV] {away_team} shows {edge_away:.1f}% edge vs market")
        else:
            print("[NO EDGE] Neither side shows significant edge (>3%)")

        print(
            f"\nNOTE: Edge calculations use example odds ({example_odds_home}/{example_odds_away})."
        )
        print("      Replace with actual market odds for real analysis.")
        print(f"\n{'='*60}\n")
    else:
        sys.stdout.write(json.dumps(analysis, default=str) + "\n")

    return analysis


def main():
    """Main entry point demonstrating library usage."""
    parser = argparse.ArgumentParser(
        description="OmegaSportsAgent - Decision Support Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                                    # Default: Lakers vs Warriors
  python main.py --home "Celtics" --away "Heat"    # Custom NBA matchup
  python main.py --league NFL --home "Chiefs" --away "Bills"
  python main.py --json                            # Pure JSON output

This is a demonstration script. For programmatic usage:

  from src.simulation.simulation_engine import OmegaSimulationEngine
  engine = OmegaSimulationEngine()
  result = engine.run_fast_game_simulation("Lakers", "Warriors", "NBA")
""",
    )

    parser.add_argument(
        "--home", default="Lakers", help="Home team name (default: Lakers)"
    )
    parser.add_argument(
        "--away", default="Warriors", help="Away team name (default: Warriors)"
    )
    parser.add_argument(
        "--league", default="NBA", help="League: NBA, NFL, NCAAB, NCAAF (default: NBA)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON only (suppresses formatted report)",
    )

    args = parser.parse_args()

    run_example_simulation(
        home_team=args.home,
        away_team=args.away,
        league=args.league.upper(),
        json_output=args.json,
    )

    if args.json:
        return


if __name__ == "__main__":
    main()