from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.data.schedule_api import get_todays_games
from src.simulation.simulation_engine import OmegaSimulationEngine
from src.betting.odds_eval import implied_probability, edge_percentage, expected_value_percent
from src.betting.kelly_staking import recommend_stake
from src.validation.probability_calibration import calibrate_probability, should_apply_calibration


@dataclass
class EdgeResult:
    matchup: str
    selection: str
    true_prob: float
    calibrated_prob: float
    market_implied: float
    edge_pct: float
    ev_pct: float
    recommended_units: float
    confidence_tier: str
    predicted_spread: float
    predicted_total: float
    meta: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "matchup": self.matchup,
            "selection": self.selection,
            "true_prob": self.true_prob,
            "calibrated_prob": self.calibrated_prob,
            "market_implied": self.market_implied,
            "edge_pct": self.edge_pct,
            "ev_pct": self.ev_pct,
            "recommended_units": self.recommended_units,
            "confidence_tier": self.confidence_tier,
            "predicted_spread": self.predicted_spread,
            "predicted_total": self.predicted_total,
            **self.meta,
        }


class AnalystEngine:
    """
    Analyst Engine orchestrates the Search → Simulate → Calibrate → Report loop.

    - Fetches scheduled games
    - Runs fast simulations
    - Calibrates probabilities to avoid extreme bias
    - Computes edge, EV%, and Kelly-based stake sizing
    """

    def __init__(
        self,
        bankroll: float,
        edge_threshold: float = 0.03,
        n_iterations: int = 1000,
        calibration_method: str = "combined",
        shrink_factor: float = 0.7,
        cap_max: float = 0.9,
        cap_min: float = 0.1,
    ) -> None:
        self.bankroll = bankroll
        self.edge_threshold = edge_threshold
        self.n_iterations = n_iterations
        self.calibration_method = calibration_method
        self.shrink_factor = shrink_factor
        self.cap_max = cap_max
        self.cap_min = cap_min
        self.engine = OmegaSimulationEngine()

    def _calibrate_prob(self, raw_prob: float, calibration_map: Optional[Dict[float, float]] = None) -> float:
        """
        Apply probability calibration using validation utilities.
        Defaults to combined shrinkage + cap to damp extremes.
        """
        if not should_apply_calibration(raw_prob, strict_cap=False) and not calibration_map:
            return raw_prob

        calibrated = calibrate_probability(
            raw_prob,
            method=self.calibration_method,
            shrink_factor=self.shrink_factor,
            cap_max=self.cap_max,
            cap_min=self.cap_min,
            calibration_map=calibration_map,
        )
        return calibrated["calibrated"]

    def _evaluate_market(
        self,
        home: str,
        away: str,
        league: str,
        sim_result: Dict[str, Any],
        market_odds: Dict[str, Any],
        calibration_map: Optional[Dict[float, float]] = None,
    ) -> Optional[EdgeResult]:
        true_prob_home = sim_result["home_win_prob"] / 100
        calibrated_prob_home = self._calibrate_prob(true_prob_home, calibration_map)

        spread_home = market_odds.get("spread_home")
        if spread_home is None:
            return None

        market_implied = implied_probability(spread_home)
        edge = edge_percentage(calibrated_prob_home, market_implied)

        if abs(edge) <= self.edge_threshold * 100:
            return None

        # Tiering based on iterations & calibration confidence
        tier = "A" if sim_result.get("iterations", 0) >= self.n_iterations else "B"
        ev_pct = expected_value_percent(calibrated_prob_home, spread_home)
        stake = recommend_stake(
            true_prob=calibrated_prob_home,
            odds=spread_home,
            bankroll=self.bankroll,
            confidence_tier=tier,
        )

        return EdgeResult(
            matchup=f"{away} @ {home}",
            selection=f"{home} spread",
            true_prob=round(true_prob_home, 3),
            calibrated_prob=round(calibrated_prob_home, 3),
            market_implied=round(market_implied, 3),
            edge_pct=round(edge, 1),
            ev_pct=round(ev_pct, 2),
            recommended_units=stake["units"],
            confidence_tier=tier,
            predicted_spread=sim_result["predicted_spread"],
            predicted_total=sim_result["predicted_total"],
            meta={
                "predicted_home_score": sim_result.get("predicted_home_score"),
                "predicted_away_score": sim_result.get("predicted_away_score"),
                "iterations": sim_result.get("iterations", self.n_iterations),
            },
        )

    def analyze_league(
        self,
        league: str,
        calibration_map: Optional[Dict[float, float]] = None,
    ) -> List[Dict[str, Any]]:
        games = get_todays_games(league)
        edges: List[EdgeResult] = []

        for game in games:
            home = game["home_team"]["name"]
            away = game["away_team"]["name"]
            market_odds = game.get("odds", {})

            sim_result = self.engine.run_fast_game_simulation(
                home_team=home,
                away_team=away,
                league=league,
                n_iterations=self.n_iterations,
            )
            if not sim_result.get("success"):
                continue

            edge_result = self._evaluate_market(home, away, league, sim_result, market_odds, calibration_map)
            if edge_result:
                edges.append(edge_result)

        return [e.to_dict() for e in sorted(edges, key=lambda x: abs(x.edge_pct), reverse=True)]


def analyze_edges(
    leagues: List[str],
    bankroll: float,
    edge_threshold: float = 0.03,
    n_iterations: int = 1000,
    calibration_method: str = "combined",
    calibration_map: Optional[Dict[float, float]] = None,
) -> Dict[str, Any]:
    """
    Convenience function to run the Analyst Engine across multiple leagues.
    """
    engine = AnalystEngine(
        bankroll=bankroll,
        edge_threshold=edge_threshold,
        n_iterations=n_iterations,
        calibration_method=calibration_method,
    )

    results: Dict[str, Any] = {"leagues": {}, "generated_by": "AnalystEngine"}
    for league in leagues:
        results["leagues"][league.upper()] = engine.analyze_league(league, calibration_map)
    return results
