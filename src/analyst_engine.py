from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from collections.abc import Callable

from src.data.schedule_api import get_todays_games
from src.simulation.simulation_engine import OmegaSimulationEngine
from src.betting.odds_eval import implied_probability, edge_percentage, expected_value_percent
from src.betting.kelly_staking import recommend_stake
from src.validation.probability_calibration import calibrate_probability, should_apply_calibration
from src.validation.auto_calibrator import get_global_calibrator, AutoCalibrator
from src.data.providers import (
    GamesProvider,
    TeamContextProvider,
    PlayerContextProvider,
    OddsProvider,
    WeatherNewsProvider,
)

logger = logging.getLogger(__name__)

# Performance thresholds for dynamic edge adjustment
BRIER_SCORE_COLD_THRESHOLD = 0.25  # Model is underperforming
BRIER_SCORE_HOT_THRESHOLD = 0.20   # Model is performing well
EDGE_THRESHOLD_CONSERVATIVE = 0.05  # 5% edge required when cold
EDGE_THRESHOLD_STANDARD = 0.03      # 3% edge in normal conditions


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
    - Dynamically adjusts edge thresholds based on model performance (feedback loop)

    CALIBRATION INTEGRATION:
    - Queries AutoCalibrator.get_performance_summary() before evaluating markets
    - If Brier Score > 0.25 (model is "cold"): increases edge threshold to 5%
    - If Brier Score < 0.20 (model is "hot"): allows standard 3% threshold
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
        games_provider: Optional[GamesProvider] = None,
        team_context_provider: Optional[TeamContextProvider] = None,
        player_context_provider: Optional[PlayerContextProvider] = None,
        odds_provider: Optional[OddsProvider] = None,
        weather_news_provider: Optional[WeatherNewsProvider] = None,
        use_dynamic_edge: bool = True,
        calibrator: Optional[AutoCalibrator] = None,
    ) -> None:
        self.bankroll = bankroll
        self._base_edge_threshold = edge_threshold
        self.edge_threshold = edge_threshold
        self.n_iterations = n_iterations
        self.calibration_method = calibration_method
        self.shrink_factor = shrink_factor
        self.cap_max = cap_max
        self.cap_min = cap_min
        self.engine = OmegaSimulationEngine()

        # Allow web-derived or external game feeds (scraped, cached, API).
        self.games_provider = games_provider or get_todays_games
        self.team_context_provider = team_context_provider
        self.player_context_provider = player_context_provider
        self.odds_provider = odds_provider
        self.weather_news_provider = weather_news_provider

        # Calibration integration
        self.use_dynamic_edge = use_dynamic_edge
        self._calibrator = calibrator
        self._last_performance_check: Optional[Dict[str, Any]] = None

    @property
    def calibrator(self) -> AutoCalibrator:
        """Get or create the calibrator instance."""
        if self._calibrator is None:
            self._calibrator = get_global_calibrator()
        return self._calibrator

    def _get_dynamic_edge_threshold(self, league: Optional[str] = None) -> float:
        """
        Get the dynamic edge threshold based on recent model performance.

        When the model is "cold" (Brier Score > 0.25), we become more conservative
        and require a higher edge to place bets. When "hot" (< 0.20), we use
        standard sizing.

        Args:
            league: Optional league to filter performance

        Returns:
            Edge threshold (0.03 standard, 0.05 conservative)
        """
        if not self.use_dynamic_edge:
            return self._base_edge_threshold

        try:
            performance = self.calibrator.get_performance_summary(league=league)
            self._last_performance_check = performance

            brier_score = performance.get("brier_score", 0.22)
            settled_predictions = performance.get("settled_predictions", 0)

            # Need minimum sample size for reliable adjustment
            if settled_predictions < 20:
                logger.debug(
                    f"Insufficient samples ({settled_predictions}) for dynamic edge, "
                    f"using base threshold: {self._base_edge_threshold}"
                )
                return self._base_edge_threshold

            # Model is "cold" - be more conservative
            if brier_score > BRIER_SCORE_COLD_THRESHOLD:
                logger.info(
                    f"Model is COLD (Brier={brier_score:.3f} > {BRIER_SCORE_COLD_THRESHOLD}), "
                    f"increasing edge threshold to {EDGE_THRESHOLD_CONSERVATIVE*100:.0f}%"
                )
                return EDGE_THRESHOLD_CONSERVATIVE

            # Model is "hot" - allow standard sizing
            elif brier_score < BRIER_SCORE_HOT_THRESHOLD:
                logger.info(
                    f"Model is HOT (Brier={brier_score:.3f} < {BRIER_SCORE_HOT_THRESHOLD}), "
                    f"using standard threshold {EDGE_THRESHOLD_STANDARD*100:.0f}%"
                )
                return EDGE_THRESHOLD_STANDARD

            # Normal performance
            else:
                return self._base_edge_threshold

        except Exception as e:
            logger.warning(f"Error getting dynamic edge threshold: {e}")
            return self._base_edge_threshold

    def get_model_status(self, league: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current model performance status.

        Returns:
            Dict with model health indicators
        """
        performance = self.calibrator.get_performance_summary(league=league)
        brier_score = performance.get("brier_score", 0.22)

        if brier_score > BRIER_SCORE_COLD_THRESHOLD:
            status = "COLD"
            recommendation = "Increase edge threshold, reduce position sizes"
        elif brier_score < BRIER_SCORE_HOT_THRESHOLD:
            status = "HOT"
            recommendation = "Model performing well, standard sizing OK"
        else:
            status = "NORMAL"
            recommendation = "Use standard parameters"

        return {
            "status": status,
            "brier_score": brier_score,
            "roi": performance.get("roi", 0),
            "settled_predictions": performance.get("settled_predictions", 0),
            "recommendation": recommendation,
            "current_edge_threshold": self._get_dynamic_edge_threshold(league),
            "base_edge_threshold": self._base_edge_threshold
        }

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
        """
        Evaluate a market for edge using simulation results and calibration.

        CALIBRATION FEEDBACK LOOP:
        - Queries model performance before evaluating
        - Adjusts edge threshold dynamically based on Brier score
        - Cold model (Brier > 0.25) -> 5% edge required
        - Hot model (Brier < 0.20) -> 3% edge (standard)
        """
        true_prob_home = sim_result["home_win_prob"] / 100
        calibrated_prob_home = self._calibrate_prob(true_prob_home, calibration_map)

        # Spread value (points) is separate from pricing (odds/juice).
        spread_home = market_odds.get("spread_home") or market_odds.get("spread")
        spread_price = (
            market_odds.get("spread_home_price")
            or market_odds.get("spread_price")
            or market_odds.get("spread_odds")
            or -110  # default book juice if missing
        )

        if spread_home is None:
            return None

        market_implied = implied_probability(spread_price)
        edge = edge_percentage(calibrated_prob_home, market_implied)

        # Get DYNAMIC edge threshold based on model performance
        dynamic_threshold = self._get_dynamic_edge_threshold(league)

        if abs(edge) <= dynamic_threshold * 100:
            return None

        # Determine confidence tier based on:
        # 1. Simulation iterations
        # 2. Model performance (hot/cold)
        # 3. Edge magnitude
        tier = self._determine_confidence_tier(sim_result, edge, league)

        ev_pct = expected_value_percent(calibrated_prob_home, spread_price)
        stake = recommend_stake(
            true_prob=calibrated_prob_home,
            odds=spread_price,
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
                "dynamic_edge_threshold": dynamic_threshold,
                "model_performance": self._last_performance_check,
            },
        )

    def _determine_confidence_tier(
        self,
        sim_result: Dict[str, Any],
        edge: float,
        league: str
    ) -> str:
        """
        Determine confidence tier based on multiple factors.

        Tier A: High confidence
        - Sufficient iterations
        - Model is HOT (low Brier score)
        - Large edge

        Tier B: Medium confidence
        - Normal model performance
        - Moderate edge

        Tier C: Low confidence
        - Model is COLD
        - Small edge
        - Insufficient data

        Returns:
            Confidence tier (A, B, or C)
        """
        iterations = sim_result.get("iterations", 0)

        # Base tier from iterations
        if iterations >= self.n_iterations:
            base_tier = "A"
        elif iterations >= self.n_iterations // 2:
            base_tier = "B"
        else:
            base_tier = "C"

        # Adjust based on model performance
        try:
            performance = self.calibrator.get_performance_summary(league=league)
            brier_score = performance.get("brier_score", 0.22)

            if brier_score > BRIER_SCORE_COLD_THRESHOLD:
                # Model is cold - downgrade tier
                if base_tier == "A":
                    return "B"
                elif base_tier == "B":
                    return "C"
                return "C"

            elif brier_score < BRIER_SCORE_HOT_THRESHOLD and abs(edge) > 5:
                # Model is hot AND large edge - keep/upgrade tier
                return base_tier

        except Exception:
            pass

        return base_tier

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
            if self.odds_provider:
                provided_odds = self.odds_provider(game, league)
                if provided_odds:
                    # provider may return OddsQuote or dict
                    provided = provided_odds.to_dict() if hasattr(provided_odds, "to_dict") else provided_odds
                    market_odds.update({k: v for k, v in provided.items() if v is not None})

            home_ctx = None
            away_ctx = None
            if self.team_context_provider:
                home_ctx = self.team_context_provider(home, league)
                away_ctx = self.team_context_provider(away, league)

            sim_result = self.engine.run_fast_game_simulation(
                home_team=home,
                away_team=away,
                league=league,
                n_iterations=self.n_iterations,
                home_context=home_ctx.to_dict() if hasattr(home_ctx, "to_dict") else home_ctx,
                away_context=away_ctx.to_dict() if hasattr(away_ctx, "to_dict") else away_ctx,
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
    games_provider: Optional[GamesProvider] = None,
    team_context_provider: Optional[TeamContextProvider] = None,
    player_context_provider: Optional[PlayerContextProvider] = None,
    odds_provider: Optional[OddsProvider] = None,
    weather_news_provider: Optional[WeatherNewsProvider] = None,
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
        team_context_provider=team_context_provider,
        player_context_provider=player_context_provider,
        odds_provider=odds_provider,
        weather_news_provider=weather_news_provider,
    )

    results: Dict[str, Any] = {"leagues": {}, "generated_by": "AnalystEngine"}
    for league in leagues:
        league_games = games_by_league.get(league) if games_by_league else None
        results["leagues"][league.upper()] = engine.analyze_league(
            league, calibration_map, games=league_games
        )
    return results
