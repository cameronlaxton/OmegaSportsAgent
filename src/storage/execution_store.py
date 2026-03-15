"""
Execution Store — audit trail for agent query executions.

Records what the agent understood, planned, gathered, and produced
for every query, enabling debugging and pipeline improvement.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from agent.models import (
    AnswerPlan,
    ExecutionResult,
    GatheredFact,
    QueryUnderstanding,
)
from src.db.schema import ExecutionRun

logger = logging.getLogger("omega.storage.execution_store")


def record_execution(
    session: Session,
    query_text: str,
    understanding: QueryUnderstanding,
    plan: AnswerPlan,
    facts: List[GatheredFact],
    execution_result: ExecutionResult,
    duration_ms: int,
) -> Optional[str]:
    """Insert a complete execution_runs row. Returns the run ID or None on failure."""
    run_id = str(uuid4())

    # Extract providers used from gathered facts
    providers_used = sorted({
        f.result.source
        for f in facts
        if f.filled and f.result is not None
    })

    try:
        row = ExecutionRun(
            id=run_id,
            query_text=query_text,
            understanding=understanding.model_dump(mode="json"),
            plan=plan.model_dump(mode="json"),
            slots_requested=len(facts),
            slots_filled=sum(1 for f in facts if f.filled),
            data_quality_score=execution_result.data_quality_score,
            execution_mode=execution_result.mode.value,
            providers_used=providers_used,
            errors=[],
            duration_ms=duration_ms,
            created_at=datetime.utcnow(),
        )
        session.add(row)
        session.commit()
        logger.debug("Recorded execution run %s", run_id)
        return run_id
    except Exception as exc:
        logger.warning("Failed to record execution: %s", exc)
        session.rollback()
        return None


def get_recent_runs(
    session: Session,
    limit: int = 20,
) -> List[ExecutionRun]:
    """Return the N most recent execution_runs, ordered by created_at DESC."""
    try:
        return (
            session.query(ExecutionRun)
            .order_by(ExecutionRun.created_at.desc())
            .limit(limit)
            .all()
        )
    except Exception as exc:
        logger.warning("Failed to get recent runs: %s", exc)
        return []
