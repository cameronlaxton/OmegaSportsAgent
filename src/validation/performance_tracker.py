"""
Performance Tracker Module

Tracks all predictions vs actual outcomes to enable autonomous calibration.
Records are stored persistently and used for continuous improvement.
"""

from __future__ import annotations
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class PredictionType(Enum):
    """Types of predictions tracked by the system."""
    MONEYLINE = "moneyline"
    SPREAD = "spread"
    TOTAL = "total"
    PLAYER_PROP = "player_prop"
    TEAM_PROP = "team_prop"
    PARLAY = "parlay"
    MARKOV_SIMULATION = "markov_simulation"
    MONTE_CARLO_SIMULATION = "monte_carlo_simulation"


@dataclass
class PredictionRecord:
    """
    Record of a single prediction and its outcome.
    
    Attributes:
        prediction_id: Unique identifier
        timestamp: When prediction was made
        prediction_type: Type of prediction
        league: Sport league (NBA, NFL, etc.)
        model_version: Version of model used
        predicted_value: What the model predicted
        predicted_probability: Probability assigned by model
        actual_value: Actual outcome
        actual_result: Win/Loss/Push
        confidence_tier: A/B/C tier
        edge_pct: Edge percentage claimed
        stake_amount: How much was recommended to bet
        profit_loss: Actual profit or loss
        parameters_used: Dict of model parameters used
        metadata: Additional context
    """
    prediction_id: str
    timestamp: str
    prediction_type: str
    league: str
    model_version: str
    predicted_value: float
    predicted_probability: float
    actual_value: Optional[float]
    actual_result: Optional[str]
    confidence_tier: str
    edge_pct: float
    stake_amount: float
    profit_loss: Optional[float]
    parameters_used: Dict[str, Any]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PredictionRecord:
        """Create from dictionary."""
        return cls(**data)


class PerformanceTracker:
    """
    Tracks all predictions and outcomes for autonomous calibration.
    
    This is the foundation of the self-enhancement system. Every prediction
    is logged along with its outcome, enabling the system to learn which
    parameters and strategies work best.
    """
    
    def __init__(self, storage_path: str = "data/logs/predictions.json"):
        """
        Initialize the performance tracker.
        
        Args:
            storage_path: Path to JSON file for storing prediction records
        """
        self.storage_path = storage_path
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        
        if not os.path.exists(storage_path):
            self._initialize_storage()
    
    def _initialize_storage(self) -> None:
        """Initialize empty prediction log."""
        with open(self.storage_path, 'w') as f:
            json.dump([], f, indent=2)
    
    def log_prediction(
        self,
        prediction_type: str,
        league: str,
        predicted_value: float,
        predicted_probability: float,
        confidence_tier: str,
        edge_pct: float,
        stake_amount: float,
        parameters_used: Dict[str, Any],
        model_version: str = "1.0",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a new prediction.
        
        Returns:
            prediction_id for later updating with actual outcome
        """
        prediction_id = f"{league}_{prediction_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        record = PredictionRecord(
            prediction_id=prediction_id,
            timestamp=datetime.now().isoformat(),
            prediction_type=prediction_type,
            league=league,
            model_version=model_version,
            predicted_value=predicted_value,
            predicted_probability=predicted_probability,
            actual_value=None,
            actual_result=None,
            confidence_tier=confidence_tier,
            edge_pct=edge_pct,
            stake_amount=stake_amount,
            profit_loss=None,
            parameters_used=parameters_used,
            metadata=metadata or {}
        )
        
        # Load existing records
        records = self._load_records()
        records.append(record.to_dict())
        
        # Save updated records
        with open(self.storage_path, 'w') as f:
            json.dump(records, f, indent=2, default=str)
        
        return prediction_id
    
    def update_outcome(
        self,
        prediction_id: str,
        actual_value: float,
        actual_result: str,
        profit_loss: float
    ) -> None:
        """
        Update a prediction with its actual outcome.
        
        Args:
            prediction_id: ID returned from log_prediction
            actual_value: Actual outcome value
            actual_result: "Win", "Loss", or "Push"
            profit_loss: Actual profit or loss amount
        """
        records = self._load_records()
        
        for record in records:
            if record['prediction_id'] == prediction_id:
                record['actual_value'] = actual_value
                record['actual_result'] = actual_result
                record['profit_loss'] = profit_loss
                break
        
        with open(self.storage_path, 'w') as f:
            json.dump(records, f, indent=2, default=str)
    
    def _load_records(self) -> List[Dict[str, Any]]:
        """Load all prediction records from storage."""
        try:
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def get_records(
        self,
        prediction_type: Optional[str] = None,
        league: Optional[str] = None,
        settled_only: bool = False,
        limit: Optional[int] = None
    ) -> List[PredictionRecord]:
        """
        Retrieve prediction records with optional filtering.
        
        Args:
            prediction_type: Filter by prediction type
            league: Filter by league
            settled_only: Only return records with actual outcomes
            limit: Maximum number of records to return
        
        Returns:
            List of PredictionRecord objects
        """
        records = self._load_records()
        
        # Filter
        filtered = []
        for record_dict in records:
            # Skip if filtering by type and doesn't match
            if prediction_type and record_dict.get('prediction_type') != prediction_type:
                continue
            
            # Skip if filtering by league and doesn't match
            if league and record_dict.get('league') != league:
                continue
            
            # Skip if settled_only and no actual result
            if settled_only and not record_dict.get('actual_result'):
                continue
            
            filtered.append(PredictionRecord.from_dict(record_dict))
        
        # Apply limit
        if limit:
            filtered = filtered[-limit:]
        
        return filtered
    
    def get_performance_summary(
        self,
        prediction_type: Optional[str] = None,
        league: Optional[str] = None,
        recent_n: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get performance summary statistics.
        
        Returns:
            Dict with win rate, ROI, Brier score, etc.
        """
        records = self.get_records(
            prediction_type=prediction_type,
            league=league,
            settled_only=True
        )
        
        if recent_n:
            records = records[-recent_n:]
        
        if not records:
            return {
                "total_predictions": 0,
                "settled_predictions": 0,
                "message": "No settled predictions to analyze"
            }
        
        wins = sum(1 for r in records if r.actual_result == "Win")
        losses = sum(1 for r in records if r.actual_result == "Loss")
        pushes = sum(1 for r in records if r.actual_result == "Push")
        
        total_staked = sum(r.stake_amount for r in records)
        total_profit = sum(r.profit_loss or 0 for r in records)
        
        # Calculate Brier score for probability calibration
        brier_scores = []
        for r in records:
            if r.actual_result in ("Win", "Loss"):
                outcome = 1.0 if r.actual_result == "Win" else 0.0
                brier_scores.append((r.predicted_probability - outcome) ** 2)
        
        avg_brier = sum(brier_scores) / len(brier_scores) if brier_scores else 0.0
        
        # Note: Win rate excludes pushes from denominator (industry standard)
        # Win% = Wins / (Wins + Losses), not including pushes
        
        return {
            "total_predictions": len(records),
            "settled_predictions": wins + losses + pushes,
            "wins": wins,
            "losses": losses,
            "pushes": pushes,
            "win_rate": wins / (wins + losses) if (wins + losses) > 0 else 0.0,
            "total_staked": total_staked,
            "total_profit": total_profit,
            "roi": (total_profit / total_staked * 100) if total_staked > 0 else 0.0,
            "brier_score": avg_brier,
            "calibration_quality": "Good" if avg_brier < 0.15 else "Needs Improvement"
        }
    
    def get_parameter_performance(
        self,
        parameter_name: str,
        prediction_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze performance by parameter value.
        
        This helps identify which parameter values lead to best outcomes.
        
        Args:
            parameter_name: Name of parameter to analyze
            prediction_type: Optional filter by prediction type
        
        Returns:
            Dict mapping parameter values to performance metrics
        """
        records = self.get_records(
            prediction_type=prediction_type,
            settled_only=True
        )
        
        # Group by parameter value
        performance_by_value: Dict[Any, List[PredictionRecord]] = {}
        for record in records:
            value = record.parameters_used.get(parameter_name)
            if value is not None:
                if value not in performance_by_value:
                    performance_by_value[value] = []
                performance_by_value[value].append(record)
        
        # Calculate metrics for each value
        results = {}
        for param_value, param_records in performance_by_value.items():
            wins = sum(1 for r in param_records if r.actual_result == "Win")
            losses = sum(1 for r in param_records if r.actual_result == "Loss")
            total_profit = sum(r.profit_loss or 0 for r in param_records)
            total_staked = sum(r.stake_amount for r in param_records)
            
            results[str(param_value)] = {
                "count": len(param_records),
                "wins": wins,
                "losses": losses,
                "win_rate": wins / (wins + losses) if (wins + losses) > 0 else 0.0,
                "roi": (total_profit / total_staked * 100) if total_staked > 0 else 0.0,
                "avg_edge": sum(r.edge_pct for r in param_records) / len(param_records)
            }
        
        return results
