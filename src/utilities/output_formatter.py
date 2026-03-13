"""
Output formatting for analysis results.

Converts analysis dicts into human-readable text or structured formats.
"""

from __future__ import annotations

import json
from typing import Any, Dict


def format_full_output(analysis: Dict[str, Any], fmt: str = "text") -> str:
    """Format an analysis result dict for display.

    Args:
        analysis: Analysis dict from AnalystEngine or service layer.
        fmt: "text" for human-readable, "json" for JSON string.

    Returns:
        Formatted string.
    """
    if fmt == "json":
        return json.dumps(analysis, indent=2, default=str)

    lines = []
    matchup = analysis.get("matchup", "Unknown")
    league = analysis.get("league", "")
    lines.append(f"{'='*60}")
    lines.append(f"  {matchup}  ({league})")
    lines.append(f"{'='*60}")

    sim = analysis.get("simulation", {})
    if sim:
        lines.append(f"  Iterations:       {sim.get('iterations', 'N/A')}")
        lines.append(f"  Home Win Prob:    {sim.get('home_win_prob', 'N/A')}%")
        lines.append(f"  Away Win Prob:    {sim.get('away_win_prob', 'N/A')}%")
        spread = sim.get("predicted_spread")
        if spread is not None:
            lines.append(f"  Predicted Spread: {spread:+.1f}")
        total = sim.get("predicted_total")
        if total is not None:
            lines.append(f"  Predicted Total:  {total:.1f}")

    edge_analysis = analysis.get("edge_analysis", {})
    if edge_analysis:
        lines.append(f"\n{'-'*60}")
        lines.append("  EDGE ANALYSIS")
        lines.append(f"{'-'*60}")
        for side, data in edge_analysis.items():
            if isinstance(data, dict):
                team = data.get("team", side)
                edge = data.get("edge_pct", 0)
                units = data.get("recommended_units", 0)
                lines.append(f"  {team}: edge {edge:+.1f}%  |  {units:.2f} units")

    lines.append(f"{'='*60}\n")
    return "\n".join(lines)
