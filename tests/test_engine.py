"""
Tests for the OmegaSports core engine: imports, schemas, simulation, betting, config, CLI.

Tests the PRODUCTION code paths (src.contracts.schemas, OmegaSimulationEngine).
"""

import subprocess
import sys

import pytest


class TestModuleImports:
    """Verify that the project's key modules can be imported without error."""

    def test_contracts_schemas(self):
        from src.contracts.schemas import (
            GameAnalysisRequest,
            MarketQuote,
            OddsInput,
            SlateAnalysisRequest,
        )

    def test_foundation_modules(self):
        from src.foundation.model_config import get_edge_thresholds
        from src.foundation.league_config import get_league_config
        from src.foundation.core_abstractions import Team

    def test_data_modules(self):
        from src.data.schedule_api import get_todays_games
        from src.data.stats_scraper import get_team_stats
        from src.data.odds_scraper import get_upcoming_games
        from src.data.providers import GamesProvider, TeamContextProvider

    def test_simulation_modules(self):
        from src.simulation.simulation_engine import OmegaSimulationEngine
        from src.simulation.correlated_simulation import simulate_correlated_markets

    def test_analyst_engine_modules(self):
        from src.analyst_engine import find_daily_edges, EdgeFilter, AnalystEngine, analyze_edges

    def test_betting_modules(self):
        from src.betting.odds_eval import edge_percentage, implied_probability
        from src.betting.kelly_staking import recommend_stake

    def test_utility_modules(self):
        from src.utilities.output_formatter import format_full_output
        from src.utilities.data_logging import log_bet_recommendation
        from src.utilities.sandbox_persistence import OmegaCacheLogger


class TestContractSchemas:
    """Test the production Pydantic schemas from src.contracts.schemas."""

    def test_game_analysis_request(self):
        from src.contracts.schemas import GameAnalysisRequest, OddsInput

        req = GameAnalysisRequest(
            home_team="Boston Celtics",
            away_team="Indiana Pacers",
            league="NBA",
            odds=OddsInput(
                moneyline_home=-150,
                moneyline_away=130,
                spread_home=-4.5,
                over_under=220.5,
            ),
            n_iterations=1000,
        )
        assert req.home_team == "Boston Celtics"
        assert req.away_team == "Indiana Pacers"
        assert req.league == "NBA"
        assert req.odds.moneyline_home == -150
        assert req.odds.spread_home == -4.5
        assert req.odds.over_under == 220.5

    def test_market_quote(self):
        from src.contracts.schemas import MarketQuote

        quote = MarketQuote(
            market_type="moneyline",
            selection="Home",
            price=-150,
        )
        assert quote.market_type == "moneyline"
        assert quote.price == -150

    def test_odds_input_with_markets(self):
        from src.contracts.schemas import MarketQuote, OddsInput

        odds = OddsInput(
            markets=[
                MarketQuote(market_type="moneyline", selection="Home", price=-150),
                MarketQuote(market_type="spread", selection="Home -4.5", price=-110, line=-4.5),
            ]
        )
        assert len(odds.markets) == 2
        assert odds.markets[0].price == -150
        assert odds.markets[1].line == -4.5


class TestSimulation:
    """Test the production simulation engine (OmegaSimulationEngine)."""

    def test_fast_game_simulation(self):
        from src.simulation.simulation_engine import OmegaSimulationEngine

        engine = OmegaSimulationEngine()
        result = engine.run_fast_game_simulation(
            home_team="Boston Celtics",
            away_team="Indiana Pacers",
            league="NBA",
            n_iterations=100,
        )

        assert isinstance(result, dict)
        # Should contain probability keys
        assert "home_win_pct" in result or "true_prob_a" in result or "skip_reason" in result


class TestBettingAnalysis:
    """Test betting evaluation modules."""

    def test_implied_probability(self):
        from src.betting.odds_eval import implied_probability

        prob = implied_probability(-150)
        assert 0 < prob < 1

    def test_edge_percentage(self):
        from src.betting.odds_eval import edge_percentage, implied_probability

        model_prob = 0.65
        impl_prob = implied_probability(-150)
        edge = edge_percentage(model_prob, impl_prob)
        assert isinstance(edge, (int, float))

    def test_expected_value(self):
        from src.betting.odds_eval import expected_value_percent

        ev = expected_value_percent(0.65, -150)
        assert isinstance(ev, (int, float))

    def test_edge_thresholds(self):
        from src.foundation.model_config import get_edge_thresholds

        thresholds = get_edge_thresholds()
        assert isinstance(thresholds, dict)
        assert "low" in thresholds
        assert "mid" in thresholds
        assert "high" in thresholds


class TestConfiguration:
    """Test configuration modules."""

    def test_model_config(self):
        from src.foundation.model_config import get_edge_thresholds, get_simulation_params

        thresholds = get_edge_thresholds()
        assert isinstance(thresholds, dict)

        params = get_simulation_params()
        assert "n_iterations" in params

    def test_league_config(self):
        from src.foundation.league_config import get_league_config

        nba = get_league_config("NBA")
        assert "periods" in nba
        assert nba["periods"] == 4


class TestMainCLI:
    """Test main.py CLI entry point."""

    def test_help_flag(self):
        result = subprocess.run(
            [sys.executable, "main.py", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Decision Support Engine" in result.stdout
