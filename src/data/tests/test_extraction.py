"""Tests for the extractor layer."""

import pytest
from datetime import datetime

from agent.models import GatherSlot
from src.data.models.facts import SourceAttribution
from src.data.extractors.stats_extractor import StatsExtractor
from src.data.extractors.odds_extractor import OddsExtractor
from src.data.extractors.injury_extractor import InjuryExtractor
from src.data.extractors.schedule_extractor import ScheduleExtractor
from src.data.extractors.game_log_extractor import GameLogExtractor
from src.data.extractors.base_extractor import get_extractor


def _make_attribution():
    return SourceAttribution(
        source_name="test",
        source_url="https://test.com",
        fetched_at=datetime.utcnow(),
        trust_tier=3,
        confidence=0.8,
    )


def _make_slot(data_type: str, entity: str = "Lakers", league: str = "NBA"):
    return GatherSlot(
        key=f"test.{data_type}",
        data_type=data_type,
        entity=entity,
        league=league,
    )


class TestStatsExtractor:
    def test_extracts_off_rating(self):
        ext = StatsExtractor()
        attr = _make_attribution()
        slot = _make_slot("team_stat")
        text = "The Lakers have an Offensive Rating: 115.2 and Defensive Rating: 108.5 this season."
        facts = ext.extract_rule_based(text, slot, attr)
        keys = {f.key for f in facts}
        assert "off_rating" in keys
        assert "def_rating" in keys
        off = next(f for f in facts if f.key == "off_rating")
        assert off.value == 115.2

    def test_extracts_pace(self):
        ext = StatsExtractor()
        attr = _make_attribution()
        slot = _make_slot("team_stat")
        text = "Pace: 100.5 possessions per game"
        facts = ext.extract_rule_based(text, slot, attr)
        assert any(f.key == "pace" and f.value == 100.5 for f in facts)

    def test_empty_text_returns_empty(self):
        ext = StatsExtractor()
        attr = _make_attribution()
        slot = _make_slot("team_stat")
        facts = ext.extract("", slot, attr)
        assert facts == []

    def test_schema_hint_team(self):
        ext = StatsExtractor()
        slot = _make_slot("team_stat")
        schema = ext.schema_hint(slot)
        assert "off_rating" in schema
        assert "def_rating" in schema

    def test_schema_hint_player(self):
        ext = StatsExtractor()
        slot = _make_slot("player_stat")
        schema = ext.schema_hint(slot)
        assert "pts_mean" in schema


class TestOddsExtractor:
    def test_extracts_moneylines(self):
        ext = OddsExtractor()
        attr = _make_attribution()
        slot = _make_slot("odds")
        text = "Lakers -150 Warriors +130 Spread: -3.5 Total: 224.5"
        facts = ext.extract_rule_based(text, slot, attr)
        keys = {f.key for f in facts}
        assert "moneyline_home" in keys
        assert "moneyline_away" in keys
        assert "spread_home" in keys
        assert "total" in keys

    def test_extracts_total(self):
        ext = OddsExtractor()
        attr = _make_attribution()
        slot = _make_slot("odds")
        text = "O/U 221.5"
        facts = ext.extract_rule_based(text, slot, attr)
        assert any(f.key == "total" and f.value == 221.5 for f in facts)


class TestScheduleExtractor:
    def test_extracts_matchup(self):
        ext = ScheduleExtractor()
        attr = _make_attribution()
        slot = _make_slot("schedule", entity="Lakers")
        text = "Lakers vs Warriors at 7:30 PM"
        facts = ext.extract_rule_based(text, slot, attr)
        assert len(facts) >= 2
        keys = {f.key for f in facts}
        assert "home_team" in keys or "away_team" in keys


class TestInjuryExtractor:
    def test_extracts_injury_status(self):
        ext = InjuryExtractor()
        attr = _make_attribution()
        slot = _make_slot("injury", entity="Lakers")
        text = "Lakers injury report: Anthony Davis (knee) - Questionable for tonight"
        facts = ext.extract_rule_based(text, slot, attr)
        # Should extract player_name, status, injury_type
        keys = {f.key for f in facts}
        assert "status" in keys or "player_name" in keys


class TestGameLogExtractor:
    def test_extracts_points(self):
        ext = GameLogExtractor()
        attr = _make_attribution()
        slot = _make_slot("player_game_log", entity="LeBron James")
        text = "LeBron scored 28 points, 32 points, 25 points in last three games"
        facts = ext.extract_rule_based(text, slot, attr)
        assert any(f.key == "pts_mean" for f in facts)


class TestExtractorFactory:
    def test_get_extractor_team_stat(self):
        ext = get_extractor("team_stat")
        assert ext is not None
        assert isinstance(ext, StatsExtractor)

    def test_get_extractor_odds(self):
        ext = get_extractor("odds")
        assert ext is not None
        assert isinstance(ext, OddsExtractor)

    def test_get_extractor_unknown(self):
        ext = get_extractor("unknown_type")
        assert ext is None
