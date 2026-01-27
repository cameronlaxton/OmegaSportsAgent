"""
Validator-Lab Models

SQLAlchemy models for the Predict-Grade-Tune calibration loop.
Uses JSONB heavily to handle any market type without schema migrations.
"""

from __future__ import annotations
import enum
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from sqlalchemy import (
    Column, String, Float, DateTime, ForeignKey, Enum, Index, Boolean, Integer
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.db.schema import Base


class MarketType(enum.Enum):
    """Supported market types for prediction auditing."""
    MONEYLINE = "moneyline"
    SPREAD = "spread"
    TOTAL = "total"
    PLAYER_PROP = "player_prop"
    TEAM_TOTAL = "team_total"
    FIRST_HALF = "first_half"
    QUARTER = "quarter"
    LIVE = "live"


class AuditStatus(enum.Enum):
    """Status of a prediction audit record."""
    PENDING = "pending"          # Prediction made, awaiting outcome
    RESOLVED = "resolved"        # Outcome captured, metrics calculated
    GRADED = "graded"            # Calibration metrics computed
    INVALID = "invalid"          # Data issue, excluded from calibration


class PredictionAudit(Base):
    """
    The Prediction Audit Table.

    Captures the full probability distribution from simulations, not just
    the final pick. This enables proper calibration analysis.

    JSONB Strategy:
    - prediction_payload: Distribution parameters (mean, std, percentiles)
    - outcome_payload: Actual results and success flag
    - calibration_metrics: Computed grades (Brier, percentile rank)

    This schema handles ANY market type without migrations:
    - Moneyline: {"dist": "bernoulli", "win_prob": 0.58}
    - Spread: {"dist": "normal", "mean": -4.5, "std": 8.2, "cover_prob": 0.55}
    - Player Prop: {"dist": "normal", "mean": 24.5, "std": 5.2, "over_prob": 0.62}
    """
    __tablename__ = "prediction_audits"

    # Primary key as UUID for distributed systems
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Foreign key to games table (nullable for props without game context)
    game_id = Column(String, ForeignKey("games.id"), nullable=True, index=True)

    # Model versioning for A/B testing and regression detection
    model_version = Column(String, nullable=False, index=True)

    # Market classification
    market_type = Column(Enum(MarketType), nullable=False, index=True)

    # League for segmented calibration
    league = Column(String, nullable=False, index=True)

    # Status tracking
    status = Column(Enum(AuditStatus), default=AuditStatus.PENDING, index=True)

    # Timestamps
    predicted_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)
    graded_at = Column(DateTime, nullable=True)

    # === JSONB PAYLOADS ===

    # The full prediction distribution parameters
    # Examples:
    # Moneyline: {
    #   "dist": "bernoulli",
    #   "selection": "home",
    #   "win_prob": 0.58,
    #   "iterations": 10000,
    #   "confidence_interval": [0.55, 0.61]
    # }
    # Spread: {
    #   "dist": "normal",
    #   "selection": "home",
    #   "line": -4.5,
    #   "predicted_margin": -6.2,
    #   "margin_std": 8.5,
    #   "cover_prob": 0.58,
    #   "push_prob": 0.02,
    #   "percentiles": {"p10": -18.5, "p25": -11.2, "p50": -6.2, "p75": -1.1, "p90": 6.8}
    # }
    # Player Prop: {
    #   "dist": "normal",
    #   "player_id": "uuid-lebron",
    #   "player_name": "LeBron James",
    #   "stat_type": "pts",
    #   "line": 24.5,
    #   "selection": "over",
    #   "mean": 26.8,
    #   "std": 5.2,
    #   "over_prob": 0.62,
    #   "under_prob": 0.38,
    #   "percentiles": {"p10": 19.2, "p25": 23.1, "p50": 26.8, "p75": 30.5, "p90": 33.8}
    # }
    prediction_payload = Column(JSONB, nullable=False)

    # Market odds at time of prediction
    # {
    #   "odds": -110,
    #   "implied_prob": 0.524,
    #   "book": "DraftKings",
    #   "line": 24.5  # for spreads/totals
    # }
    market_payload = Column(JSONB, nullable=True)

    # The actual outcome after game completion
    # Examples:
    # Moneyline: {"winner": "home", "home_score": 112, "away_score": 105}
    # Spread: {"home_margin": -8, "covered": true, "push": false}
    # Player Prop: {"actual_value": 28, "hit": true, "player_played": true}
    outcome_payload = Column(JSONB, nullable=True)

    # Computed calibration metrics
    # {
    #   "brier_score": 0.21,
    #   "log_loss": 0.45,
    #   "percentile_rank": 0.72,  # where actual fell in our distribution
    #   "confidence_bin": "55-60",
    #   "calibration_error": 0.05,  # predicted 58%, bin hit rate 53%
    #   "edge_realized": true,  # did our edge materialize
    #   "clv": 0.03  # closing line value captured
    # }
    calibration_metrics = Column(JSONB, nullable=True)

    # Edge and stake information
    edge_pct = Column(Float, nullable=True)  # Denormalized for quick queries
    stake_units = Column(Float, nullable=True)

    # Result tracking
    result = Column(String, nullable=True)  # "WIN", "LOSS", "PUSH", "VOID"
    profit_units = Column(Float, nullable=True)

    # Indexes for calibration queries
    __table_args__ = (
        Index("idx_audit_league_market", "league", "market_type"),
        Index("idx_audit_status_predicted", "status", "predicted_at"),
        Index("idx_audit_model_league", "model_version", "league"),
        Index("idx_audit_prediction_gin", "prediction_payload", postgresql_using="gin"),
        Index("idx_audit_calibration_gin", "calibration_metrics", postgresql_using="gin"),
    )

    # Relationships
    game = relationship("Game", backref="prediction_audits")

    def __repr__(self) -> str:
        """
        Provide a concise debug representation of the PredictionAudit instance.
        
        Returns:
            A string formatted as "<PredictionAudit {id} {market_type} {status}>" containing the audit's id, market type value, and status value.
        """
        return f"<PredictionAudit {self.id} {self.market_type.value} {self.status.value}>"

    @property
    def predicted_prob(self) -> Optional[float]:
        """
        Return the primary predicted probability for this audit based on its market type.
        
        For MONEYLINE returns the `win_prob` from `prediction_payload`. For SPREAD returns `cover_prob`. For PLAYER_PROP uses `selection` from the payload (defaults to `"over"`) and returns the corresponding `"<selection>_prob"` if present, otherwise falls back to `over_prob`. For TOTAL uses `selection` (defaults to `"over"`) and returns `"<selection>_prob"`. Returns `None` if `prediction_payload` is missing or no applicable probability key exists.
        
        Returns:
            float or None: The predicted probability value, or `None` when unavailable.
        """
        if not self.prediction_payload:
            return None

        payload = self.prediction_payload
        if self.market_type == MarketType.MONEYLINE:
            return payload.get("win_prob")
        elif self.market_type == MarketType.SPREAD:
            return payload.get("cover_prob")
        elif self.market_type == MarketType.PLAYER_PROP:
            selection = payload.get("selection", "over")
            return payload.get(f"{selection}_prob") or payload.get("over_prob")
        elif self.market_type == MarketType.TOTAL:
            selection = payload.get("selection", "over")
            return payload.get(f"{selection}_prob")
        return None

    @property
    def outcome_success(self) -> Optional[bool]:
        """
        Determine whether the prediction outcome should be considered a success.
        
        Checks the instance's outcome_payload for the keys "hit", "covered", or "success" (in that order) and returns their boolean value if present; if none are present, falls back to the result field where "WIN" -> True, "LOSS" or "PUSH" -> False.
        
        Returns:
            `True` if the prediction succeeded, `False` if it failed, `None` if the outcome cannot be determined.
        """
        if not self.outcome_payload:
            return None

        payload = self.outcome_payload
        if "hit" in payload:
            return payload["hit"]
        if "covered" in payload:
            return payload["covered"]
        if "success" in payload:
            return payload["success"]

        # Derive from result field
        if self.result == "WIN":
            return True
        elif self.result in ("LOSS", "PUSH"):
            return False
        return None

    def to_calibration_record(self) -> Dict[str, Any]:
        """
        Export a flat dictionary representing this audit suitable for calibration analysis.
        
        Returns:
            dict: A dictionary with standardized calibration fields:
                - id (str): Audit UUID as a string.
                - league (str): League identifier.
                - market_type (str|None): Market type name, or `None` if unset.
                - model_version (str|None): Model version identifier.
                - predicted_prob (float|None): Primary predicted probability derived from the prediction payload.
                - outcome (float|None): `1.0` if the prediction succeeded, `0.0` if it failed, or `None` if unknown.
                - edge_pct (float|None): Recorded edge percentage, if present.
                - predicted_at (str|None): ISO-8601 timestamp of when the prediction was made, or `None`.
                - brier_score (float|None): Brier score from calibration metrics, if present.
                - confidence_bin (Any|None): Confidence bin from calibration metrics, if present.
        """
        return {
            "id": str(self.id),
            "league": self.league,
            "market_type": self.market_type.value if self.market_type else None,
            "model_version": self.model_version,
            "predicted_prob": self.predicted_prob,
            "outcome": 1.0 if self.outcome_success else 0.0 if self.outcome_success is False else None,
            "edge_pct": self.edge_pct,
            "predicted_at": self.predicted_at.isoformat() if self.predicted_at else None,
            "brier_score": self.calibration_metrics.get("brier_score") if self.calibration_metrics else None,
            "confidence_bin": self.calibration_metrics.get("confidence_bin") if self.calibration_metrics else None,
        }


class CalibrationSnapshot(Base):
    """
    Stores calibration state snapshots for trend analysis.

    Generated periodically by the CalibrationTuner to track
    how model accuracy evolves over time.
    """
    __tablename__ = "calibration_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Segmentation
    league = Column(String, nullable=False, index=True)
    market_type = Column(String, nullable=True)  # NULL = aggregate
    model_version = Column(String, nullable=True)  # NULL = all versions

    # Time window
    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Sample size
    n_predictions = Column(Integer, nullable=False)
    n_resolved = Column(Integer, nullable=False)

    # Aggregate metrics
    # {
    #   "brier_score": 0.215,
    #   "log_loss": 0.48,
    #   "ece": 0.042,  # Expected Calibration Error
    #   "mce": 0.08,   # Maximum Calibration Error
    #   "hit_rate": 0.534,
    #   "roi": -0.023,
    #   "calibration_factors": {
    #     "50-55": 0.92,
    #     "55-60": 0.88,
    #     "60-65": 0.85,
    #     "65-70": 0.82
    #   },
    #   "reliability_curve": [
    #     {"bin": "50-55", "predicted": 0.525, "actual": 0.512, "count": 245},
    #     {"bin": "55-60", "predicted": 0.575, "actual": 0.523, "count": 189}
    #   ]
    # }
    metrics = Column(JSONB, nullable=False)

    # Recommended calibration adjustments
    # Applied to config/league_calibrations.yaml
    recommended_adjustments = Column(JSONB, nullable=True)

    # Was this snapshot applied to config?
    applied = Column(Boolean, default=False)
    applied_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_calibration_snapshot_league", "league", "created_at"),
    )

    def __repr__(self) -> str:
        """
        Provide a concise developer-facing string representation of the CalibrationSnapshot.
        
        Returns:
            A string containing the snapshot's league, the `window_end` date, and the number of predictions (`n_predictions`).
        """
        return f"<CalibrationSnapshot {self.league} {self.window_end.date()} n={self.n_predictions}>"
