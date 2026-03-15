"""
Integration tests for BetRecorder and CalibrationLoader.

Validates:
- BetRecorder can record bets to daily JSON files
- CalibrationLoader can load calibration packs
- Module imports work correctly
- End-to-end integration of engine + calibration
"""

import json
import os
import tempfile

import pytest


class TestBetRecorder:
    """Test BetRecorder functionality with proper cleanup."""

    def test_record_and_retrieve(self, tmp_path, monkeypatch):
        from src.utilities.bet_recorder import BetRecorder

        # Redirect output to tmp_path so we don't leak artifacts
        monkeypatch.setattr(
            "src.utilities.bet_recorder._BET_DIR",
            str(tmp_path),
        )

        test_date = "2099-01-01"
        filepath = BetRecorder.record_bet(
            date=test_date,
            league="NBA",
            bet_id="test_bet_001",
            game_id="401234567",
            game_date=test_date,
            market_type="moneyline",
            recommendation="HOME",
            edge=0.055,
            model_probability=0.625,
            market_probability=0.570,
            stake=10.0,
            odds=-150,
            calibration_version="nba_v1.0",
            confidence="medium",
            metadata={"test": True},
        )

        assert os.path.exists(filepath)

        with open(filepath) as f:
            data = json.load(f)
        assert data["date"] == test_date
        assert data["league"] == "NBA"
        assert len(data["bets"]) >= 1
        assert data["bets"][-1]["bet_id"] == "test_bet_001"
        assert abs(data["bets"][-1]["edge"] - 0.055) < 0.001

    def test_append_to_same_date(self, tmp_path, monkeypatch):
        from src.utilities.bet_recorder import BetRecorder

        monkeypatch.setattr(
            "src.utilities.bet_recorder._BET_DIR",
            str(tmp_path),
        )

        test_date = "2099-01-01"
        fp1 = BetRecorder.record_bet(
            date=test_date, league="NBA", bet_id="bet_a",
            game_id="1", game_date=test_date, market_type="moneyline",
            recommendation="HOME", edge=0.05, model_probability=0.6,
            market_probability=0.55, stake=10.0, odds=-150,
        )
        fp2 = BetRecorder.record_bet(
            date=test_date, league="NBA", bet_id="bet_b",
            game_id="2", game_date=test_date, market_type="spread",
            recommendation="AWAY", edge=0.04, model_probability=0.56,
            market_probability=0.52, stake=7.5, odds=-110, line=-3.5,
        )
        assert fp1 == fp2

        with open(fp1) as f:
            data = json.load(f)
        assert len(data["bets"]) == 2


class TestCalibrationLoader:
    """Test CalibrationLoader functionality."""

    def test_load_nba_calibration(self):
        from src.foundation.calibration_loader import CalibrationLoader

        cal = CalibrationLoader("NBA")
        version = cal.get_version()
        assert isinstance(version, str)

    def test_edge_thresholds(self):
        from src.foundation.calibration_loader import CalibrationLoader

        cal = CalibrationLoader("NBA")
        ml_threshold = cal.get_edge_threshold("moneyline")
        assert 0.0 < ml_threshold < 1.0

        spread_threshold = cal.get_edge_threshold("spread")
        assert 0.0 < spread_threshold < 1.0

    def test_kelly_parameters(self):
        from src.foundation.calibration_loader import CalibrationLoader

        cal = CalibrationLoader("NBA")
        kelly = cal.get_kelly_fraction()
        assert 0.0 < kelly <= 1.0

        policy = cal.get_kelly_policy()
        assert isinstance(policy, (str, dict))

    def test_probability_transform(self):
        from src.foundation.calibration_loader import CalibrationLoader

        cal = CalibrationLoader("NBA")
        transform = cal.get_probability_transform("moneyline")
        if transform is not None:
            adjusted = transform(0.65)
            assert 0.0 < adjusted < 1.0


class TestModuleImports:
    """Verify active modules import without breaking each other."""

    def test_new_modules(self):
        from src.utilities.bet_recorder import BetRecorder
        from src.foundation.calibration_loader import CalibrationLoader

    def test_existing_utilities(self):
        from src.utilities.data_logging import log_bet_recommendation, get_log_directory

    def test_betting_modules(self):
        from src.betting.odds_eval import edge_percentage, implied_probability
        from src.betting.kelly_staking import recommend_stake


class TestIntegration:
    """End-to-end: calibration loader → odds eval → bet recorder."""

    def test_calibrated_bet_workflow(self, tmp_path, monkeypatch):
        from src.utilities.bet_recorder import BetRecorder
        from src.foundation.calibration_loader import CalibrationLoader
        from src.betting.odds_eval import implied_probability

        monkeypatch.setattr(
            "src.utilities.bet_recorder._BET_DIR",
            str(tmp_path),
        )

        cal = CalibrationLoader("NBA")
        edge_threshold = cal.get_edge_threshold("moneyline")
        kelly_frac = cal.get_kelly_fraction()

        market_odds = -150
        model_prob = 0.65

        transform = cal.get_probability_transform("moneyline")
        adjusted_prob = transform(model_prob) if transform else model_prob

        market_prob = implied_probability(market_odds)
        edge = adjusted_prob - market_prob

        assert edge_threshold > 0
        assert kelly_frac > 0

        if edge >= edge_threshold:
            filepath = BetRecorder.record_bet(
                date="2099-01-01",
                league="NBA",
                bet_id="integration_test_001",
                game_id="401234569",
                game_date="2099-01-01",
                market_type="moneyline",
                recommendation="HOME",
                edge=edge,
                model_probability=adjusted_prob,
                market_probability=market_prob,
                stake=5.0,
                odds=market_odds,
                edge_threshold=edge_threshold,
                kelly_fraction=kelly_frac,
                confidence="medium",
                calibration_version=cal.get_version(),
            )
            assert os.path.exists(filepath)
