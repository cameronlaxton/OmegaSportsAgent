"""
Tests for find_daily_edges() — the canonical programmatic entrypoint.

Uses frozen team contexts (no network) to validate output shape,
filtering, and edge structure.
"""

import pytest

from src.analyst_engine import find_daily_edges, EdgeFilter


# Frozen NBA contexts for deterministic simulation
_FROZEN_GAMES = {
    "NBA": [
        {
            "home_team": "Lakers",
            "away_team": "Warriors",
            "odds": {
                "spread_home": -4.5,
                "spread_home_price": -110,
                "moneyline_home": -180,
                "moneyline_away": 155,
                "over_under": 224.5,
            },
        },
    ],
}

_FROZEN_CONTEXTS = {
    ("Lakers", "NBA"): {
        "name": "Lakers",
        "league": "NBA",
        "off_rating": 115.0,
        "def_rating": 106.0,
        "pace": 100.0,
    },
    ("Warriors", "NBA"): {
        "name": "Warriors",
        "league": "NBA",
        "off_rating": 108.0,
        "def_rating": 112.0,
        "pace": 100.0,
    },
}


def _team_context_provider(team, league):
    from src.data.providers import TeamContextInput

    ctx = _FROZEN_CONTEXTS.get((team, league.upper()))
    if ctx is None:
        return None
    return TeamContextInput(**ctx)


class TestFindDailyEdgesOutputShape:
    """Verify the return structure of find_daily_edges."""

    def _run(self, **kwargs):
        defaults = dict(
            leagues=["NBA"],
            bankroll=1000.0,
            n_iterations=200,
            games_by_league=_FROZEN_GAMES,
            team_context_provider=_team_context_provider,
        )
        defaults.update(kwargs)
        return find_daily_edges(**defaults)

    def test_top_level_keys(self):
        result = self._run()
        assert "generated_at" in result
        assert "leagues" in result
        assert "summary" in result
        assert isinstance(result["leagues"], dict)
        assert isinstance(result["summary"], dict)

    def test_summary_shape(self):
        result = self._run()
        summary = result["summary"]
        assert "total_edges" in summary
        assert "leagues_scanned" in summary
        assert isinstance(summary["total_edges"], int)
        assert isinstance(summary["leagues_scanned"], int)
        assert summary["leagues_scanned"] == 1

    def test_league_entry_shape(self):
        result = self._run()
        assert "NBA" in result["leagues"]
        nba = result["leagues"]["NBA"]
        assert "edges" in nba
        assert "config_used" in nba
        assert isinstance(nba["edges"], list)
        assert isinstance(nba["config_used"], dict)

    def test_config_used_keys(self):
        result = self._run()
        config = result["leagues"]["NBA"]["config_used"]
        assert "edge_threshold" in config
        assert "shrinkage_factor" in config
        assert "calibration_method" in config
        assert "n_iterations" in config

    def test_edge_required_fields(self):
        """If edges are returned, each must have the required fields."""
        result = self._run()
        edges = result["leagues"]["NBA"]["edges"]
        required = {
            "matchup", "selection", "true_prob", "calibrated_prob",
            "market_implied", "edge_pct", "ev_pct", "recommended_units",
            "confidence_tier", "predicted_spread", "predicted_total", "factors",
        }
        for edge in edges:
            missing = required - set(edge.keys())
            assert not missing, f"Edge missing fields: {missing}"

    def test_factors_is_list_of_strings(self):
        result = self._run()
        for edge in result["leagues"]["NBA"]["edges"]:
            assert isinstance(edge["factors"], list)
            for f in edge["factors"]:
                assert isinstance(f, str)

    def test_edge_pct_bounds(self):
        result = self._run()
        for edge in result["leagues"]["NBA"]["edges"]:
            assert -100 <= edge["edge_pct"] <= 100

    def test_prob_bounds(self):
        result = self._run()
        for edge in result["leagues"]["NBA"]["edges"]:
            assert 0 <= edge["true_prob"] <= 1
            assert 0 <= edge["calibrated_prob"] <= 1
            assert 0 <= edge["market_implied"] <= 1


class TestEdgeFilter:
    """Test EdgeFilter controls output correctly."""

    def _run(self, edge_filter=None, **kwargs):
        defaults = dict(
            leagues=["NBA"],
            bankroll=1000.0,
            n_iterations=200,
            games_by_league=_FROZEN_GAMES,
            team_context_provider=_team_context_provider,
            edge_filter=edge_filter,
        )
        defaults.update(kwargs)
        return find_daily_edges(**defaults)

    def test_max_edges_per_league(self):
        result = self._run(edge_filter=EdgeFilter(max_edges_per_league=0))
        assert result["leagues"]["NBA"]["edges"] == []
        assert result["summary"]["total_edges"] == 0

    def test_max_units_cap(self):
        result = self._run(edge_filter=EdgeFilter(max_units=0.5))
        for edge in result["leagues"]["NBA"]["edges"]:
            assert edge["recommended_units"] <= 0.5

    def test_min_confidence_filter(self):
        result = self._run(edge_filter=EdgeFilter(min_confidence="A"))
        for edge in result["leagues"]["NBA"]["edges"]:
            assert edge["confidence_tier"] == "A"

    def test_empty_leagues(self):
        result = self._run(leagues=[])
        assert result["summary"]["leagues_scanned"] == 0
        assert result["summary"]["total_edges"] == 0


class TestFindDailyEdgesNoGames:
    """Test behavior with no games or unknown leagues."""

    def test_unknown_league_returns_empty(self):
        result = find_daily_edges(
            leagues=["CURLING"],
            bankroll=1000.0,
            games_by_league={"CURLING": []},
        )
        assert result["leagues"]["CURLING"]["edges"] == []
