from typing import List, Dict, Any, Optional

from src.analyst_engine import AnalystEngine


def find_daily_edges(
    league: str,
    bankroll: float,
    edge_threshold: float = 0.03,
    n_iterations: int = 1000,
    calibration_method: str = "combined",
    calibration_map: Optional[Dict[float, float]] = None,
) -> List[Dict[str, Any]]:
    """
    Canonical Search → Sim → Report loop for AI agents.

    Returns a list of edge dicts sorted by absolute edge descending. Each entry includes:
    matchup, selection, true_prob, calibrated_prob, market_implied, edge_pct,
    recommended_units, confidence_tier, predicted_spread, predicted_total.
    """
    engine = AnalystEngine(
        bankroll=bankroll,
        edge_threshold=edge_threshold,
        n_iterations=n_iterations,
        calibration_method=calibration_method,
    )
    return engine.analyze_league(league, calibration_map)
