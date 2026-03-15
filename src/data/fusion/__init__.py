"""Fusion layer — merge multi-source results with conflict resolution."""

from src.data.fusion.fact_fuser import fuse_facts
from src.data.fusion.confidence_scorer import score_confidence

__all__ = [
    "fuse_facts",
    "score_confidence",
]
