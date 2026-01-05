"""
Bet Output Module - BetRecorder

Records daily bet recommendations to outputs/recommendations_YYYYMMDD.json
for integration with the Validation Lab calibration system.

Schema matches Validation Lab requirements:
- One file per date (ISO 8601: YYYYMMDD)
- Structured bet metadata including edge, probabilities, kelly, confidence
- Supports all market types: moneyline, spread, total, player props

Usage Example:
    from outputs.bet_recorder import BetRecorder
    
    BetRecorder.record_bet(
        date="2026-01-05",
        league="NBA",
        bet_id="game123_ml_home",
        game_id="401234567",
        game_date="2026-01-05",
        market_type="moneyline",
        recommendation="HOME",
        edge=0.055,
        model_probability=0.625,
        market_probability=0.570,
        stake=10.0,
        odds=-150,
        calibration_version="nba_v1.0"
    )
"""

from __future__ import annotations
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any


def _ensure_outputs_dir() -> str:
    """
    Ensures outputs/ directory exists.
    
    Returns:
        Path to outputs directory
    """
    outputs_dir = os.path.join(os.path.dirname(__file__))
    os.makedirs(outputs_dir, exist_ok=True)
    return outputs_dir


def _get_recommendations_filepath(date: str) -> str:
    """
    Get filepath for recommendations file for a given date.
    
    Args:
        date: Date string in YYYY-MM-DD format
    
    Returns:
        Full filepath to recommendations_YYYYMMDD.json
    """
    outputs_dir = _ensure_outputs_dir()
    # Convert YYYY-MM-DD to YYYYMMDD
    date_str = date.replace("-", "")
    filename = f"recommendations_{date_str}.json"
    return os.path.join(outputs_dir, filename)


def _load_recommendations_file(filepath: str) -> Dict[str, Any]:
    """
    Load existing recommendations file or create new structure.
    
    Args:
        filepath: Path to recommendations file
    
    Returns:
        Dict with date, league, calibration_version, and bets list
    """
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # If file is corrupted, start fresh
            pass
    
    # Return empty structure
    return {
        "date": "",
        "league": "",
        "calibration_version": "",
        "bets": []
    }


def _save_recommendations_file(filepath: str, data: Dict[str, Any]) -> None:
    """
    Save recommendations data to file.
    
    Args:
        filepath: Path to recommendations file
        data: Recommendations data structure
    """
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


class BetRecorder:
    """
    Records bet recommendations to daily JSON files matching Validation Lab schema.
    
    All methods are class methods for convenient stateless usage.
    """
    
    @classmethod
    def record_bet(
        cls,
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
        calibration_version: str = "default",
        line: Optional[float] = None,
        edge_threshold: Optional[float] = None,
        kelly_fraction: Optional[float] = None,
        confidence: Optional[str] = None,
        player_name: Optional[str] = None,
        prop_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record a bet recommendation to the daily recommendations file.
        
        Creates or appends to outputs/recommendations_YYYYMMDD.json.
        
        Args:
            date: Date string in YYYY-MM-DD format (for filename)
            league: League identifier (NBA, NFL, NCAAB, NCAAF, etc.)
            bet_id: Unique identifier for this bet
            game_id: ESPN/OddsAPI game identifier
            game_date: Game date in YYYY-MM-DD format
            market_type: Type of market (moneyline, spread, total, player_prop_points, etc.)
            recommendation: Bet recommendation (HOME, AWAY, OVER, UNDER, etc.)
            edge: Edge percentage (model_probability - market_probability)
            model_probability: Model's calculated probability (0.0 to 1.0)
            market_probability: Market-implied probability (0.0 to 1.0)
            stake: Stake amount in units
            odds: American odds
            calibration_version: Version of calibration pack used
            line: Line value for spread/total (optional)
            edge_threshold: Edge threshold applied (optional)
            kelly_fraction: Kelly fraction used for staking (optional)
            confidence: Confidence tier (high, medium, low) (optional)
            player_name: Player name for props (optional)
            prop_type: Prop type descriptor (optional)
            metadata: Additional metadata (optional)
        
        Returns:
            Path to the recommendations file
        """
        # Validate edge calculation
        calculated_edge = model_probability - market_probability
        if abs(edge - calculated_edge) > 0.001:
            # Allow small floating point differences
            edge = calculated_edge
        
        filepath = _get_recommendations_filepath(date)
        data = _load_recommendations_file(filepath)
        
        # Update file-level metadata (first bet or if empty)
        if not data.get("date") or len(data.get("bets", [])) == 0:
            data["date"] = date
            data["league"] = league
            data["calibration_version"] = calibration_version
        
        # Create bet entry
        bet_entry = {
            "bet_id": bet_id,
            "game_id": game_id,
            "game_date": game_date,
            "market_type": market_type,
            "recommendation": recommendation,
            "edge": round(edge, 6),
            "model_probability": round(model_probability, 6),
            "market_probability": round(market_probability, 6),
            "stake": round(stake, 2),
            "odds": odds,
            "line": line,
            "edge_threshold": edge_threshold,
            "kelly_fraction": kelly_fraction,
            "confidence": confidence,
            "player_name": player_name,
            "prop_type": prop_type,
            "metadata": metadata or {}
        }
        
        # Append bet to list
        data["bets"].append(bet_entry)
        
        # Save file
        _save_recommendations_file(filepath, data)
        
        return filepath
    
    @classmethod
    def get_bets_for_date(cls, date: str) -> List[Dict[str, Any]]:
        """
        Retrieve all bets recorded for a given date.
        
        Args:
            date: Date string in YYYY-MM-DD format
        
        Returns:
            List of bet entries
        """
        filepath = _get_recommendations_filepath(date)
        data = _load_recommendations_file(filepath)
        return data.get("bets", [])
    
    @classmethod
    def get_file_for_date(cls, date: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the full recommendations file for a given date.
        
        Args:
            date: Date string in YYYY-MM-DD format
        
        Returns:
            Full recommendations data structure or None if file doesn't exist
        """
        filepath = _get_recommendations_filepath(date)
        if not os.path.exists(filepath):
            return None
        return _load_recommendations_file(filepath)
