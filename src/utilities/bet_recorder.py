"""
Bet Recorder — structured persistence for bet recommendations.

Records bets to daily JSON files for audit trails and backtesting.
Each date gets a single JSON file with a list of bets appended to it.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


# Output directory is at project root outputs/recommendations/
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_BET_DIR = os.path.join(_PROJECT_ROOT, "outputs", "recommendations")


class BetRecorder:
    """Static-method interface for recording and retrieving bet recommendations."""

    @staticmethod
    def _filepath(date: str) -> str:
        os.makedirs(_BET_DIR, exist_ok=True)
        return os.path.join(_BET_DIR, f"recs_{date}.json")

    @staticmethod
    def record_bet(
        date: str,
        league: str,
        bet_id: str,
        game_id: str,
        game_date: str,
        market_type: str,
        recommendation: str,
        edge: float,
        model_probability: float,
        market_probability: float,
        stake: float,
        odds: float,
        line: Optional[float] = None,
        calibration_version: Optional[str] = None,
        confidence: Optional[str] = None,
        edge_threshold: Optional[float] = None,
        kelly_fraction: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Append a bet to the date's recommendation file. Returns filepath."""
        filepath = BetRecorder._filepath(date)

        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"date": date, "league": league, "bets": []}

        entry: Dict[str, Any] = {
            "bet_id": bet_id,
            "game_id": game_id,
            "game_date": game_date,
            "market_type": market_type,
            "recommendation": recommendation,
            "edge": edge,
            "model_probability": model_probability,
            "market_probability": market_probability,
            "stake": stake,
            "odds": odds,
            "recorded_at": datetime.now().isoformat(),
        }
        if line is not None:
            entry["line"] = line
        if calibration_version is not None:
            entry["calibration_version"] = calibration_version
        if confidence is not None:
            entry["confidence"] = confidence
        if edge_threshold is not None:
            entry["edge_threshold"] = edge_threshold
        if kelly_fraction is not None:
            entry["kelly_fraction"] = kelly_fraction
        if metadata:
            entry["metadata"] = metadata

        data["bets"].append(entry)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        return filepath

    @staticmethod
    def get_bets_for_date(date: str) -> List[Dict[str, Any]]:
        """Return list of bet dicts for a given date, or empty list."""
        filepath = BetRecorder._filepath(date)
        if not os.path.exists(filepath):
            return []
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("bets", [])
