# Injury Adjustments Module

"""
Module Name: Injury Adjustments
Version: 2.0.0
Description: Applies league-aware injury redistributions for both team-level and player-level projections.
Functions:
    - gtd_scalar(status: str) -> float
    - nba_usage_redistribution(baseline_usage: dict, injuries: list) -> dict
    - nfl_backfield_shift(rush_shares: dict, injuries: list) -> dict
    - apply_injury_adjustments(metrics: dict, injury_report: list, league: str) -> dict
    - extract_player_usage_rates(baseline_usage: dict, injury_report: list, league: str) -> dict
Usage Notes:
    - Supports NBA usage reallocations, NFL RB/WR cascading, fallback generic multiplier.
    - Supply injury_report entries with keys: name, role, status, impact.
    - Use `extract_player_usage_rates` to get injury-adjusted usage dict for `projection_model.compute_player_projections`.
    - The same injury logic drives both team-level and player-level projections.
"""

```python
from __future__ import annotations
from typing import Dict, List

def gtd_scalar(status: str) -> float:
    status = status.lower()
    if status in {"out", "injured reserve"}:
        return 0.0
    if status in {"doubtful"}:
        return 0.25
    if status in {"questionable", "game-time decision", "gtd"}:
        return 0.55
    if status in {"probable", "limited"}:
        return 0.85
    return 1.0

def nba_usage_redistribution(baseline_usage: Dict[str, float], injuries: List[Dict]) -> Dict[str, float]:
    usage = baseline_usage.copy()
    pool = 0.0
    for player, rate in baseline_usage.items():
        for report in injuries:
            if report["name"].lower() == player.lower():
                scalar = gtd_scalar(report["status"])
                pool += rate * (1 - scalar)
                usage[player] = rate * scalar
    if pool <= 0:
        return usage
    healthy_players = [p for p in usage if usage[p] > 0]
    if not healthy_players:
        return usage
    total_usage = sum(usage[p] for p in healthy_players)
    for player in healthy_players:
        usage[player] += pool * (usage[player] / total_usage)
    return usage

def nfl_backfield_shift(rush_shares: Dict[str, float], injuries: List[Dict]) -> Dict[str, float]:
    shares = rush_shares.copy()
    base_pool = 0.0
    for role in list(shares.keys()):
        for report in injuries:
            if report.get("role", "").lower() == role.lower():
                scalar = gtd_scalar(report["status"])
                base_pool += shares[role] * (1 - scalar)
                shares[role] *= scalar
    if base_pool <= 0:
        return shares
    rb_roles = [r for r in shares if r.startswith("RB")]
    wr_roles = [r for r in shares if r.startswith("WR")]
    if rb_roles:
        shares[rb_roles[-1]] += base_pool * 0.7
    if wr_roles:
        shares[wr_roles[-1]] += base_pool * 0.3
    return shares

def apply_injury_adjustments(metrics: Dict[str, float], injury_report: List[Dict], league: str) -> Dict[str, float]:
    adjusted = metrics.copy()
    league = league.upper()
    impact_factor = 0.0
    for report in injury_report:
        scalar = gtd_scalar(report["status"])
        impact = report.get("impact", 0.02)
        impact_factor += (1 - scalar) * impact
    if league == "NBA":
        usage = nba_usage_redistribution(metrics.get("usage_rates", {}), injury_report)
        adjusted["usage_rates"] = usage
        adjusted["off_rating"] = metrics.get("off_rating", 110) * (1 - impact_factor)
    elif league == "NFL":
        adjusted["rush_shares"] = nfl_backfield_shift(metrics.get("rush_shares", {}), injury_report)
        adjusted["pass_rate"] = metrics.get("pass_rate", 0.55) * (1 - 0.5 * impact_factor)
    else:
        adjusted["efficiency"] = metrics.get("efficiency", 1.0) * (1 - impact_factor)
    adjusted["injury_penalty"] = impact_factor
    return adjusted

def extract_player_usage_rates(baseline_usage: Dict[str, float], injury_report: List[Dict], league: str) -> Dict[str, float]:
    """
    Extracts injury-adjusted player usage rates for use in player projections.
    
    This is a convenience function that applies league-specific injury logic
    and returns a dict mapping player names to adjusted usage rates.
    This dict can be passed directly to `projection_model.compute_player_projections`.
    
    Args:
        baseline_usage: Dict mapping player names to baseline usage rates
        injury_report: List of injury dicts with keys: name, role, status, impact
        league: League identifier (e.g., "NBA", "NFL")
    
    Returns:
        Dict mapping player names to injury-adjusted usage rates
    """
    league = league.upper()
    
    if league == "NBA":
        return nba_usage_redistribution(baseline_usage, injury_report)
    elif league == "NFL":
        # For NFL, we need to handle role-based shifts
        # Convert role-based shares to player-level usage if needed
        # For now, apply the same logic as NBA but note that NFL may need
        # additional mapping from roles to player names
        return nba_usage_redistribution(baseline_usage, injury_report)
    else:
        # Fallback: apply GTD scalars directly
        adjusted = baseline_usage.copy()
        for player in adjusted:
            for report in injury_report:
                if report.get("name", "").lower() == player.lower():
                    scalar = gtd_scalar(report.get("status", "probable"))
                    adjusted[player] *= scalar
        return adjusted
```

