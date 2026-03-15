"""
Prediction Store — ledger for backtesting and calibration.

Every formal edge the system outputs is logged here with the market
snapshot at prediction time, enabling later settlement and walk-forward
validation.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from src.db.schema import Prediction

logger = logging.getLogger("omega.storage.prediction_store")


def record_prediction(
    session: Session,
    execution_run_id: Optional[str],
    game_id: Optional[str],
    league: str,
    prediction_type: str,
    prediction: Dict[str, Any],
    market_snapshot: Optional[Dict[str, Any]] = None,
    data_quality_score: float = 0.0,
) -> Optional[str]:
    """Record a prediction. Returns the prediction ID or None on failure."""
    pred_id = str(uuid4())
    try:
        row = Prediction(
            id=pred_id,
            execution_run_id=execution_run_id,
            game_id=game_id,
            league=league,
            prediction_type=prediction_type,
            prediction=prediction,
            market_snapshot=market_snapshot,
            data_quality_score=data_quality_score,
            created_at=datetime.utcnow(),
        )
        session.add(row)
        session.commit()
        logger.debug("Recorded prediction %s", pred_id)
        return pred_id
    except Exception as exc:
        logger.warning("Failed to record prediction: %s", exc)
        session.rollback()
        return None


def settle_prediction(
    session: Session,
    prediction_id: str,
    outcome: str,
) -> bool:
    """Set outcome and settled_at on an existing prediction. Returns True on success."""
    try:
        row = session.query(Prediction).filter(Prediction.id == prediction_id).first()
        if row is None:
            logger.warning("Prediction %s not found", prediction_id)
            return False
        row.outcome = outcome
        row.settled_at = datetime.utcnow()
        session.commit()
        return True
    except Exception as exc:
        logger.warning("Failed to settle prediction %s: %s", prediction_id, exc)
        session.rollback()
        return False


def get_unsettled_predictions(
    session: Session,
    league: Optional[str] = None,
) -> List[Prediction]:
    """Return predictions where outcome IS NULL, optionally filtered by league."""
    try:
        query = session.query(Prediction).filter(Prediction.outcome.is_(None))
        if league:
            query = query.filter(Prediction.league == league)
        return query.order_by(Prediction.created_at.desc()).all()
    except Exception as exc:
        logger.warning("Failed to get unsettled predictions: %s", exc)
        return []
