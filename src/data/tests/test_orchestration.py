"""Tests for the orchestration layer."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from agent.models import GatherSlot, GatheredFact, ProviderResult
from src.data.orchestration.retrieval_orchestrator import retrieve_facts, _fill_slot
from src.data.orchestration.search_planner import plan_searches
from src.data.orchestration.retry_strategy import with_retry
from src.data.cache.session_cache import SessionCache


class TestSearchPlanner:
    def test_team_stat_queries(self):
        slot = GatherSlot(
            key="home_team.off_rating",
            data_type="team_stat",
            entity="Lakers",
            league="NBA",
        )
        queries = plan_searches(slot)
        assert len(queries) >= 1
        assert any("Lakers" in q for q in queries)
        assert any("stats" in q.lower() for q in queries)

    def test_odds_queries(self):
        slot = GatherSlot(
            key="game.odds",
            data_type="odds",
            entity="Lakers",
            league="NBA",
        )
        queries = plan_searches(slot)
        assert len(queries) >= 1
        assert any("odds" in q.lower() for q in queries)

    def test_injury_queries(self):
        slot = GatherSlot(
            key="home_team.injuries",
            data_type="injury",
            entity="Lakers",
            league="NBA",
        )
        queries = plan_searches(slot)
        assert len(queries) >= 1
        assert any("injury" in q.lower() for q in queries)


class TestRetryStrategy:
    def test_succeeds_first_try(self):
        def fn():
            return 42
        assert with_retry(fn) == 42

    def test_retries_on_failure(self):
        call_count = 0
        def fn():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("fail")
            return "success"
        result = with_retry(fn, max_attempts=3, backoff_base=0.01)
        assert result == "success"
        assert call_count == 3

    def test_returns_none_after_max_attempts(self):
        def fn():
            raise ValueError("always fails")
        result = with_retry(fn, max_attempts=2, backoff_base=0.01)
        assert result is None


class TestSessionCache:
    def test_put_and_get(self):
        cache = SessionCache()
        cache.put("team_stat", "Lakers", "NBA", {"off_rating": 115.2})
        result = cache.get("team_stat", "Lakers", "NBA")
        assert result == {"off_rating": 115.2}

    def test_miss_returns_none(self):
        cache = SessionCache()
        result = cache.get("team_stat", "Warriors", "NBA")
        assert result is None

    def test_case_insensitive(self):
        cache = SessionCache()
        cache.put("team_stat", "Lakers", "NBA", {"off_rating": 115.2})
        result = cache.get("team_stat", "lakers", "nba")
        assert result == {"off_rating": 115.2}

    def test_lru_eviction(self):
        cache = SessionCache(max_size=2)
        cache.put("team_stat", "A", "NBA", 1)
        cache.put("team_stat", "B", "NBA", 2)
        cache.put("team_stat", "C", "NBA", 3)
        assert cache.get("team_stat", "A", "NBA") is None
        assert cache.get("team_stat", "B", "NBA") == 2
        assert cache.get("team_stat", "C", "NBA") == 3


class TestRetrieveFacts:
    @patch("src.data.orchestration.retrieval_orchestrator._try_direct_api")
    @patch("src.data.orchestration.retrieval_orchestrator.check_db_cache")
    def test_direct_api_path(self, mock_db_cache, mock_direct_api):
        """When direct API returns data, it should be used."""
        mock_db_cache.return_value = None
        mock_direct_api.return_value = ProviderResult(
            data={"off_rating": 115.2, "def_rating": 108.5},
            source="stats_scraper",
            fetched_at=datetime.utcnow(),
            confidence=0.90,
        )

        slot = GatherSlot(
            key="home_team.stats",
            data_type="team_stat",
            entity="Lakers",
            league="NBA",
        )
        results = retrieve_facts([slot])
        assert len(results) == 1
        assert results[0].filled is True
        assert results[0].result.source == "stats_scraper"

    @patch("src.data.orchestration.retrieval_orchestrator._try_web_search_pipeline")
    @patch("src.data.orchestration.retrieval_orchestrator._try_direct_api")
    @patch("src.data.orchestration.retrieval_orchestrator.check_db_cache")
    def test_fallback_to_web_search(self, mock_db_cache, mock_direct_api, mock_web):
        """When direct API returns None, falls back to web search."""
        mock_db_cache.return_value = None
        mock_direct_api.return_value = None
        mock_web.return_value = ProviderResult(
            data={"off_rating": 114.8},
            source="web_search:espn.com",
            fetched_at=datetime.utcnow(),
            confidence=0.75,
        )

        slot = GatherSlot(
            key="home_team.stats",
            data_type="team_stat",
            entity="Lakers",
            league="NBA",
        )
        results = retrieve_facts([slot])
        assert len(results) == 1
        assert results[0].filled is True
        assert "web_search" in results[0].result.source

    @patch("src.data.orchestration.retrieval_orchestrator._try_web_search_pipeline")
    @patch("src.data.orchestration.retrieval_orchestrator._try_direct_api")
    @patch("src.data.orchestration.retrieval_orchestrator.check_db_cache")
    def test_all_sources_exhausted(self, mock_db_cache, mock_direct_api, mock_web):
        """When all sources fail, returns unfilled."""
        mock_db_cache.return_value = None
        mock_direct_api.return_value = None
        mock_web.return_value = None

        slot = GatherSlot(
            key="home_team.stats",
            data_type="team_stat",
            entity="Lakers",
            league="NBA",
        )
        results = retrieve_facts([slot])
        assert len(results) == 1
        assert results[0].filled is False
        assert results[0].quality_score == 0.0

    @patch("src.data.orchestration.retrieval_orchestrator.check_db_cache")
    def test_db_cache_hit(self, mock_db_cache):
        """When DB cache has fresh data, it should be used."""
        mock_db_cache.return_value = ProviderResult(
            data={"off_rating": 115.0},
            source="schedule_api",
            fetched_at=datetime.utcnow(),
            confidence=0.95,
        )

        slot = GatherSlot(
            key="home_team.stats",
            data_type="team_stat",
            entity="Lakers",
            league="NBA",
        )
        results = retrieve_facts([slot])
        assert len(results) == 1
        assert results[0].filled is True
