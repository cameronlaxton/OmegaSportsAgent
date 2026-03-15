"""Tests for the normalizer layer."""

import pytest

from src.data.normalizers.name_normalizer import normalize_entity_name
from src.data.normalizers.odds_normalizer import (
    american_to_decimal,
    american_to_implied_prob,
    decimal_to_american,
    normalize_odds_value,
)
from src.data.normalizers.stat_normalizer import normalize_stat_value


class TestNameNormalizer:
    def test_normalize_team_abbreviation(self):
        result = normalize_entity_name("lakers", "team", "NBA")
        assert result == "Los Angeles Lakers"

    def test_normalize_team_code(self):
        result = normalize_entity_name("gsw", "team", "NBA")
        assert result == "Golden State Warriors"

    def test_normalize_player_name(self):
        result = normalize_entity_name("  LeBron  James  ", "player", "NBA")
        assert result == "LeBron James"

    def test_unknown_type_strips(self):
        result = normalize_entity_name("  test  ", "unknown", "NBA")
        assert result == "test"


class TestOddsNormalizer:
    def test_american_to_decimal_favorite(self):
        result = american_to_decimal(-150)
        assert abs(result - 1.667) < 0.01

    def test_american_to_decimal_underdog(self):
        result = american_to_decimal(130)
        assert abs(result - 2.3) < 0.01

    def test_american_to_implied_prob_favorite(self):
        result = american_to_implied_prob(-150)
        assert abs(result - 0.6) < 0.01

    def test_american_to_implied_prob_underdog(self):
        result = american_to_implied_prob(130)
        assert abs(result - 0.4348) < 0.01

    def test_decimal_to_american_favorite(self):
        result = decimal_to_american(1.667)
        assert result == -150 or abs(result - (-150)) <= 1

    def test_decimal_to_american_underdog(self):
        result = decimal_to_american(2.3)
        assert result == 130

    def test_normalize_odds_value_string(self):
        assert normalize_odds_value("+130") == 130
        assert normalize_odds_value("-150") == -150

    def test_normalize_odds_value_passthrough(self):
        assert normalize_odds_value(130) == 130
        assert normalize_odds_value(-150) == -150


class TestStatNormalizer:
    def test_percentage_normalization(self):
        # 48.5% should become 0.485
        result = normalize_stat_value("fg_pct", 48.5)
        assert abs(result - 0.485) < 0.001

    def test_already_decimal(self):
        # 0.485 should stay as 0.485
        result = normalize_stat_value("fg_pct", 0.485)
        assert abs(result - 0.485) < 0.001

    def test_non_pct_passthrough(self):
        result = normalize_stat_value("off_rating", 115.2)
        assert result == 115.2

    def test_string_conversion(self):
        result = normalize_stat_value("off_rating", "115.2")
        assert result == 115.2

    def test_none_passthrough(self):
        result = normalize_stat_value("fg_pct", None)
        assert result is None
