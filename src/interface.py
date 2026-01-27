from typing import List, Dict, Any, Optional

from src.data.schedule_api import get_todays_games
from src.simulation.simulation_engine import OmegaSimulationEngine
from src.betting.odds_eval import implied_probability, edge_percentage
from src.betting.kelly_staking import recommend_stake


def find_daily_edges(
    league: str,
    bankroll: float,
    edge_threshold: float = 0.03,
    n_iterations: int = 1000,
    engine: Optional[OmegaSimulationEngine] = None,
) -> List[Dict[str, Any]]:
    """
    Canonical Search → Sim → Report loop for AI agents.

    Returns a list of edge dicts sorted by absolute edge descending. Each entry includes:
    matchup, selection, true_prob, market_implied, edge_pct, recommended_units,
    confidence_tier, predicted_spread, predicted_total.
    """
    sim_engine = engine or OmegaSimulationEngine()
    games = get_todays_games(league)
    edges: List[Dict[str, Any]] = []

    for game in games:
        home = game["home_team"]["name"]
        away = game["away_team"]["name"]
        market_odds = game.get("odds", {})

        sim_result = sim_engine.run_fast_game_simulation(
            home_team=home,
            away_team=away,
            league=league,
            n_iterations=n_iterations,
        )
        if not sim_result.get("success"):
            continue

        true_prob_home = sim_result["home_win_prob"] / 100

        if market_odds.get("spread_home"):
            market_implied = implied_probability(market_odds["spread_home"])
            edge = edge_percentage(true_prob_home, market_implied)

            if abs(edge) > edge_threshold * 100:
                tier = "A" if sim_result.get("iterations", 0) >= n_iterations else "B"

                stake = recommend_stake(
                    true_prob=true_prob_home,
                    odds=market_odds["spread_home"],
                    bankroll=bankroll,
                    confidence_tier=tier,
                )

                edges.append(
                    {
                        "matchup": f"{away} @ {home}",
                        "selection": f"{home} spread",
                        "true_prob": round(true_prob_home, 3),
                        "market_implied": round(market_implied, 3),
                        "edge_pct": round(edge, 1),
                        "recommended_units": stake["units"],
                        "confidence_tier": tier,
                        "predicted_spread": sim_result["predicted_spread"],
                        "predicted_total": sim_result["predicted_total"],
                    }
                )

    return sorted(edges, key=lambda x: abs(x["edge_pct"]), reverse=True)
