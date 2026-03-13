"""
Analyst Engine: Search -> Simulate -> Calibrate -> Report.

This is one of two analysis paths in the system:

    1. analyst_engine.py (this file) — Provider-injected orchestration.
       Used by: agent/, main.py --daily, any caller that fetches or injects data.
       Supports data providers, config loading, edge filtering.

    2. src/contracts/service.py — JSON-in/JSON-out service layer.
       Used by: FastAPI (server/app.py).
       Caller supplies all context; no data fetching, no config loading.

Both share the same simulation engine (OmegaSimulationEngine) and calibration
logic (probability_calibration). This is intentional, not duplication.

Public API:
    find_daily_edges() — canonical programmatic entrypoint (multi-league, filtered, standardized output)
    analyze_edges()    — lower-level multi-league wrapper (no filtering, no config loading)
    AnalystEngine      — single-league engine (inject your own providers)
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from collections.abc import Callable

import yaml

from src.data.schedule_api import get_todays_games
from src.simulation.simulation_engine import OmegaSimulationEngine
from src.betting.odds_eval import implied_probability, edge_percentage, expected_value_percent
from src.betting.kelly_staking import recommend_stake
from src.validation.probability_calibration import calibrate_probability, should_apply_calibration
from src.data.providers import (
    GamesProvider,
    TeamContextProvider,
    PlayerContextProvider,
    OddsProvider,
    WeatherNewsProvider,
)

logger = logging.getLogger(__name__)

_CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")


def _load_league_calibrations() -> Dict[str, Any]:
    """Load league_calibrations.yaml; returns empty dict on failure."""
    path = os.path.join(_CONFIG_DIR, "league_calibrations.yaml")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        logger.warning("Could not load league_calibrations.yaml; using defaults")
        return {}


@dataclass
class EdgeFilter:
    """Controls which edges are returned by find_daily_edges."""
    min_edge_pct: Optional[float] = None        # override per-league threshold
    max_edges_per_league: Optional[int] = None   # cap output volume
    markets: Optional[List[str]] = None          # e.g. ["spread", "moneyline"]
    min_confidence: Optional[str] = None         # "A", "B", or "C" — minimum tier
    max_units: Optional[float] = None            # cap recommended stake

    _TIER_ORDER = {"A": 0, "B": 1, "C": 2}

    def passes(self, edge: Dict[str, Any]) -> bool:
        if self.min_confidence:
            edge_tier = edge.get("confidence_tier", "C")
            if self._TIER_ORDER.get(edge_tier, 2) > self._TIER_ORDER.get(self.min_confidence, 2):
                return False
        return True


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
        games_provider: Optional[GamesProvider] = None,
        team_context_provider: Optional[TeamContextProvider] = None,
        player_context_provider: Optional[PlayerContextProvider] = None,
        odds_provider: Optional[OddsProvider] = None,
        weather_news_provider: Optional[WeatherNewsProvider] = None,
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
        self.team_context_provider = team_context_provider
        self.player_context_provider = player_context_provider
        self.odds_provider = odds_provider
        self.weather_news_provider = weather_news_provider

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

        if abs(edge) <= self.edge_threshold * 100:
            return None

        # Tiering based on iterations & calibration confidence
        tier = "A" if sim_result.get("iterations", 0) >= self.n_iterations else "B"
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


def find_daily_edges(
    leagues: Optional[List[str]] = None,
    bankroll: float = 1000.0,
    n_iterations: int = 1000,
    calibration_method: str = "combined",
    edge_filter: Optional[EdgeFilter] = None,
    games_by_league: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    games_provider: Optional[GamesProvider] = None,
    team_context_provider: Optional[TeamContextProvider] = None,
    player_context_provider: Optional[PlayerContextProvider] = None,
    odds_provider: Optional[OddsProvider] = None,
    weather_news_provider: Optional[WeatherNewsProvider] = None,
) -> Dict[str, Any]:
    """
    Canonical programmatic entrypoint: find today's betting edges across leagues.

    Loads per-league config from league_calibrations.yaml for edge thresholds,
    shrinkage factors, and market restrictions. Applies EdgeFilter for output
    control (caps, confidence tiers, market filters).

    Returns a standardized dict:
        {
            "generated_at": "...",
            "leagues": {
                "NBA": {
                    "edges": [...],
                    "config_used": {...},
                },
                ...
            },
            "summary": {
                "total_edges": N,
                "leagues_scanned": N,
            },
        }

    Each edge dict includes:
        matchup, selection, true_prob, calibrated_prob, market_implied,
        edge_pct, ev_pct, recommended_units, confidence_tier,
        predicted_spread, predicted_total, factors (list of strings).
    """
    league_configs = _load_league_calibrations()
    filt = edge_filter or EdgeFilter()

    # Default to leagues that have config entries
    if leagues is None:
        leagues = list(league_configs.keys()) if league_configs else ["NBA", "NFL"]

    output: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "leagues": {},
        "summary": {"total_edges": 0, "leagues_scanned": 0},
    }

    for league in leagues:
        lc = league_configs.get(league.upper(), {})
        league_upper = league.upper()

        # Per-league edge threshold: filter override > config edge_threshold > global default
        if filt.min_edge_pct is not None:
            edge_threshold = filt.min_edge_pct
        else:
            edge_threshold = lc.get("edge_threshold", 0.03)

        shrink_factor = lc.get("shrinkage_factor", 0.7)
        calibration_factors = lc.get("calibration_factors") or None
        # Convert calibration_factors dict keys to float if present
        cal_map = None
        if calibration_factors and isinstance(calibration_factors, dict) and calibration_factors:
            try:
                cal_map = {float(k): float(v) for k, v in calibration_factors.items()}
            except (ValueError, TypeError):
                cal_map = None

        engine = AnalystEngine(
            bankroll=bankroll,
            edge_threshold=edge_threshold,
            n_iterations=n_iterations,
            calibration_method=calibration_method,
            shrink_factor=shrink_factor,
            games_provider=games_provider,
            team_context_provider=team_context_provider,
            player_context_provider=player_context_provider,
            odds_provider=odds_provider,
            weather_news_provider=weather_news_provider,
        )

        league_games = games_by_league.get(league_upper) if games_by_league else None
        raw_edges = engine.analyze_league(league, cal_map, games=league_games)

        # Apply filters
        filtered = []
        for edge in raw_edges:
            if not filt.passes(edge):
                continue
            if filt.max_units is not None and edge.get("recommended_units", 0) > filt.max_units:
                edge["recommended_units"] = filt.max_units
            # Add factors summary
            edge["factors"] = _build_factors(edge)
            filtered.append(edge)

        if filt.max_edges_per_league is not None:
            filtered = filtered[: filt.max_edges_per_league]

        output["leagues"][league_upper] = {
            "edges": filtered,
            "config_used": {
                "edge_threshold": edge_threshold,
                "shrinkage_factor": shrink_factor,
                "calibration_method": calibration_method,
                "n_iterations": n_iterations,
            },
        }
        output["summary"]["total_edges"] += len(filtered)
        output["summary"]["leagues_scanned"] += 1

    return output


def _build_factors(edge: Dict[str, Any]) -> List[str]:
    """Build concise human-readable factors list for an edge."""
    factors = []
    ep = edge.get("edge_pct", 0)
    if abs(ep) >= 8:
        factors.append(f"large edge ({ep:+.1f}%)")
    elif abs(ep) >= 5:
        factors.append(f"moderate edge ({ep:+.1f}%)")
    else:
        factors.append(f"small edge ({ep:+.1f}%)")

    ev = edge.get("ev_pct", 0)
    if ev > 0:
        factors.append(f"+EV ({ev:.1f}%)")

    spread = edge.get("predicted_spread")
    if spread is not None:
        factors.append(f"predicted spread {spread:+.1f}")

    return factors
