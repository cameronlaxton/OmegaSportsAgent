"""Tests for the fusion layer."""

import pytest
from datetime import datetime

from src.data.models.facts import FactBundle, SourceAttribution, SportsFact
from src.data.fusion.fact_fuser import fuse_facts
from src.data.fusion.confidence_scorer import score_confidence


def _make_fact(key, value, source_name="test", trust_tier=3, confidence=0.8):
    return SportsFact(
        key=key,
        value=value,
        data_type="team_stat",
        entity="Lakers",
        league="NBA",
        attribution=SourceAttribution(
            source_name=source_name,
            fetched_at=datetime.utcnow(),
            trust_tier=trust_tier,
            confidence=confidence,
        ),
    )


class TestFactFuser:
    def test_single_source(self):
        bundle = FactBundle(
            slot_key="test.off_rating",
            data_type="team_stat",
            entity="Lakers",
            league="NBA",
            facts=[_make_fact("off_rating", 115.2)],
        )
        result = fuse_facts(bundle)
        assert result["off_rating"] == 115.2

    def test_agreeing_sources_averaged(self):
        bundle = FactBundle(
            slot_key="test.off_rating",
            data_type="team_stat",
            entity="Lakers",
            league="NBA",
            facts=[
                _make_fact("off_rating", 115.0, "espn", trust_tier=3, confidence=0.8),
                _make_fact("off_rating", 115.4, "bbref", trust_tier=2, confidence=0.9),
            ],
        )
        result = fuse_facts(bundle)
        # Should be weighted average (close to both values)
        assert 114.5 < result["off_rating"] < 116.0

    def test_disagreeing_sources_prefer_higher_tier(self):
        bundle = FactBundle(
            slot_key="test.off_rating",
            data_type="team_stat",
            entity="Lakers",
            league="NBA",
            facts=[
                _make_fact("off_rating", 115.0, "bbref", trust_tier=2, confidence=0.9),
                _make_fact("off_rating", 130.0, "random_site", trust_tier=4, confidence=0.5),
            ],
        )
        result = fuse_facts(bundle)
        # Should prefer tier 2 source
        assert result["off_rating"] == 115.0

    def test_empty_bundle(self):
        bundle = FactBundle(
            slot_key="test",
            data_type="team_stat",
            entity="Lakers",
            league="NBA",
        )
        result = fuse_facts(bundle)
        assert result == {}

    def test_multiple_keys(self):
        bundle = FactBundle(
            slot_key="test",
            data_type="team_stat",
            entity="Lakers",
            league="NBA",
            facts=[
                _make_fact("off_rating", 115.2),
                _make_fact("def_rating", 108.5),
                _make_fact("pace", 100.1),
            ],
        )
        result = fuse_facts(bundle)
        assert "off_rating" in result
        assert "def_rating" in result
        assert "pace" in result


class TestConfidenceScorer:
    def test_high_confidence_single_source(self):
        bundle = FactBundle(
            slot_key="test",
            data_type="team_stat",
            entity="Lakers",
            league="NBA",
            facts=[_make_fact("off_rating", 115.2, trust_tier=1, confidence=0.95)],
        )
        score = score_confidence(bundle)
        assert 0.5 < score <= 1.0

    def test_empty_bundle_zero_confidence(self):
        bundle = FactBundle(
            slot_key="test",
            data_type="team_stat",
            entity="Lakers",
            league="NBA",
        )
        score = score_confidence(bundle)
        assert score == 0.0

    def test_multi_source_agreement_boosts(self):
        bundle_single = FactBundle(
            slot_key="test",
            data_type="team_stat",
            entity="Lakers",
            league="NBA",
            facts=[_make_fact("off_rating", 115.2, "espn", trust_tier=3, confidence=0.8)],
        )
        bundle_multi = FactBundle(
            slot_key="test",
            data_type="team_stat",
            entity="Lakers",
            league="NBA",
            facts=[
                _make_fact("off_rating", 115.2, "espn", trust_tier=3, confidence=0.8),
                _make_fact("off_rating", 115.4, "bbref", trust_tier=2, confidence=0.9),
            ],
        )
        score_single = score_confidence(bundle_single)
        score_multi = score_confidence(bundle_multi)
        # Multi-source with agreement should score higher
        assert score_multi >= score_single
