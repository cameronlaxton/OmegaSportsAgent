"""
Game Analysis Module

Comprehensive game analysis aggregating narratives, bets, props, and correlations.
"""

from omega.analysis.game_analysis import (
    GameAnalysisService,
    get_game_analysis
)
from omega.analysis.game_pipeline import (
    GameAnalysisPipeline,
    run_analysis
)
from omega.analysis.derivative_analyzer import (
    DerivativeEdgeAnalyzer,
    DerivativeEdge,
    SegmentScores,
    TeamDerivativeProfile,
    analyze_derivative_edges
)

__all__ = [
    "GameAnalysisService",
    "get_game_analysis",
    "GameAnalysisPipeline",
    "run_analysis",
    "DerivativeEdgeAnalyzer",
    "DerivativeEdge",
    "SegmentScores",
    "TeamDerivativeProfile",
    "analyze_derivative_edges"
]
