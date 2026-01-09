from typing import Any, Dict, List, Optional

import numpy as np


def _rankdata(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    sorted_vals = values[order]
    index = 0
    while index < len(values):
        next_index = index + 1
        while next_index < len(values) and sorted_vals[next_index] == sorted_vals[index]:
            next_index += 1
        average_rank = (index + 1 + next_index) / 2.0
        ranks[order[index:next_index]] = average_rank
        index = next_index
    return ranks


def _spearman_correlation(x: np.ndarray, y: np.ndarray) -> Optional[float]:
    if len(x) < 2 or len(y) < 2:
        return None
    x_rank = _rankdata(x)
    y_rank = _rankdata(y)
    if np.std(x_rank) == 0 or np.std(y_rank) == 0:
        return None
    return float(np.corrcoef(x_rank, y_rank)[0, 1])


def analyze_edge_correlation(bets: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not bets:
        return None

    edges = np.array([bet.get("edge", 0.0) for bet in bets], dtype=float)
    outcomes = np.array([bet.get("outcome", 0.0) for bet in bets], dtype=float)
    implied_probs = np.array([bet.get("prob", 0.0) for bet in bets], dtype=float)

    spearman = _spearman_correlation(edges, outcomes)
    mean_implied = float(np.mean(implied_probs)) if len(implied_probs) else 0.0
    mean_outcome = float(np.mean(outcomes)) if len(outcomes) else 0.0
    bias = mean_implied - mean_outcome

    if bias > 0.02:
        bias_label = "overconfidence"
    elif bias < -0.02:
        bias_label = "underconfidence"
    else:
        bias_label = "well_calibrated"

    return {
        "bet_count": int(len(bets)),
        "spearman_correlation": spearman,
        "mean_implied_prob": mean_implied,
        "mean_outcome": mean_outcome,
        "bias": float(bias),
        "bias_label": bias_label,
    }
