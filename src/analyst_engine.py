from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from collections.abc import Callable

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
        games_provider: Optional[Callable[[str], List[Dict[str, Any]]]] = None,
    ) -> None:
        self.bankroll = bankroll
        self.edge_threshold = edge_threshold
        self.n_iterations = n_iterations
        self.calibration_method = calibration_method
        self.shrink_factor = shrink_factor
        self.cap_max = cap_max
        self.cap_min = cap_min
        self.engine = OmegaSimulationEngine()
        # Allow web-derived or external game feeds (scraped, cached, API).
        self.games_provider = games_provider or get_todays_games

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
        games: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        games_feed = games if games is not None else self.games_provider(league)
        edges: List[EdgeResult] = []

        for game in games_feed:
            home = self._extract_team_name(game, "home_team") or self._extract_team_name(game, "home")
            away = self._extract_team_name(game, "away_team") or self._extract_team_name(game, "away")
            if not home or not away:
                # Skip malformed records from scraped sources (ESPN, Rotowire, others)
                continue

            market_odds = self._extract_market_odds(game)

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

    @staticmethod
    def _extract_team_name(game: Dict[str, Any], key: str) -> Optional[str]:
        """
        Safely extract a team name from scraped or API data.
        Supports dict payloads ({'name': ..}) and direct string values.
        """
        team = game.get(key)
        if not team:
            return None
        if isinstance(team, dict):
            return team.get("name") or team.get("team") or team.get("full_name")
        if isinstance(team, str):
            return team
        return None

    @staticmethod
    def _extract_market_odds(game: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract odds from flexible scraped structures.
        Looks for 'odds' first, then common fallbacks like 'markets' or 'book'.
        """
        if "odds" in game and isinstance(game["odds"], dict):
            return game["odds"]
        if "markets" in game and isinstance(game["markets"], dict):
            return game["markets"]
        if "book" in game and isinstance(game["book"], dict):
            return game["book"]
        return {}


def analyze_edges(
    leagues: List[str],
    bankroll: float,
    edge_threshold: float = 0.03,
    n_iterations: int = 1000,
    calibration_method: str = "combined",
    calibration_map: Optional[Dict[float, float]] = None,
    games_by_league: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    games_provider: Optional[Callable[[str], List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """
    Convenience function to run the Analyst Engine across multiple leagues.

    Supports injected game data (scraped/web-derived) via games_by_league or
    a custom games_provider callable to keep the pipeline data-source agnostic.
    """
    engine = AnalystEngine(
        bankroll=bankroll,
        edge_threshold=edge_threshold,
        n_iterations=n_iterations,
        calibration_method=calibration_method,
        games_provider=games_provider,
    )

    results: Dict[str, Any] = {"leagues": {}, "generated_by": "AnalystEngine"}
    for league in leagues:
        league_games = games_by_league.get(league) if games_by_league else None
        results["leagues"][league.upper()] = engine.analyze_league(
            league, calibration_map, games=league_games
        )
    return results
