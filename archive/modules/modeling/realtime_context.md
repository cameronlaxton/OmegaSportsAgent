# Realtime Context Module

"""
Module Name: Realtime Context Module
Version: 1.0.0
Description: Normalizes live factors (weather, travel, rest, tempo) and returns quantitative modifiers for downstream models.
Functions:
    - normalize_realtime_inputs(raw_ctx: dict, league: str) -> RealTimeContext
    - derive_pace_bias(ctx: RealTimeContext, league: str) -> float
    - context_multipliers(ctx: RealTimeContext, league: str) -> dict
    - game_script_bias(probable_script: str, league: str) -> dict
Usage Notes:
    - Always call before projection modeling.
    - All numeric outputs are bounded to prevent runaway scaling.
"""

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class RealTimeContext:
    league: str
    weather: str = "indoor"
    temperature_f: float = 70.0
    wind_mph: float = 0.0
    precipitation: str = "none"
    roof_status: str = "closed"
    days_rest: int = 2
    is_back_to_back: bool = False
    travel_miles: int = 0
    timezone_shift: int = 0
    pace_delta: float = 0.0
    game_script: str = "neutral"

def normalize_realtime_inputs(raw_ctx: Dict[str, Any], league: str) -> RealTimeContext:
    defaults = RealTimeContext(league=league)
    payload = defaults.__dict__.copy()
    for key in payload:
        if key == "league":
            continue
        if key in raw_ctx:
            payload[key] = raw_ctx[key]
    payload["league"] = league.upper()
    payload["weather"] = str(payload["weather"]).lower()
    payload["precipitation"] = str(payload["precipitation"]).lower()
    payload["roof_status"] = str(payload["roof_status"]).lower()
    payload["game_script"] = str(payload["game_script"]).lower()
    return RealTimeContext(**payload)

def _rest_modifier(ctx: RealTimeContext) -> float:
    fatigue = 0.0
    fatigue -= 0.02 * max(0, 2 - ctx.days_rest)
    fatigue -= 0.03 if ctx.is_back_to_back else 0.0
    fatigue -= min(0.04, ctx.travel_miles / 3000.0)
    fatigue -= 0.02 * abs(ctx.timezone_shift)
    return max(-0.15, fatigue)

def derive_pace_bias(ctx: RealTimeContext, league: str) -> float:
    league = league.upper()
    base = ctx.pace_delta
    weather_penalty = 0.0
    if league in {"NFL", "NCAAF"}:
        weather_penalty -= 0.05 if ctx.precipitation in {"rain", "snow"} else 0.0
        weather_penalty -= 0.03 if ctx.wind_mph >= 15 else 0.0
    if league == "NBA":
        base += _rest_modifier(ctx) * -0.8
    if ctx.game_script == "run-heavy":
        base -= 0.05
    elif ctx.game_script == "fastbreak":
        base += 0.07
    return max(-0.2, min(0.2, base + weather_penalty))

def game_script_bias(probable_script: str, league: str) -> Dict[str, float]:
    script = probable_script.lower()
    bias = {"tempo": 0.0, "pass_rate": 0.0, "rush_rate": 0.0}
    if league.upper() in {"NFL", "NCAAF"}:
        if script == "shootout":
            bias["tempo"] = 0.08
            bias["pass_rate"] = 0.1
        elif script in {"run-heavy", "slow"}:
            bias["tempo"] = -0.07
            bias["rush_rate"] = 0.12
    if league.upper() == "NBA":
        if script == "fastbreak":
            bias["tempo"] = 0.1
        elif script == "half-court":
            bias["tempo"] = -0.08
    return bias

def context_multipliers(ctx: RealTimeContext, league: str) -> Dict[str, float]:
    pace_bias = derive_pace_bias(ctx, league)
    fatigue = _rest_modifier(ctx)
    weather_penalty = 0.0
    if league.upper() in {"NFL", "MLB"}:
        if ctx.wind_mph >= 15:
            weather_penalty -= min(0.08, ctx.wind_mph / 100.0)
        if ctx.precipitation != "none":
            weather_penalty -= 0.04
    roof_bonus = 0.03 if ctx.roof_status == "closed" and league.upper() in {"NFL", "NCAAF"} else 0.0
    return {
        "pace": 1.0 + pace_bias,
        "efficiency": 1.0 + fatigue + weather_penalty + roof_bonus,
        "scoring_variance": max(0.85, 1.0 + weather_penalty * 1.5),
        "turnover_rate": 1.0 + (0.02 if ctx.wind_mph >= 18 else 0.0) + (0.015 if ctx.is_back_to_back else 0.0)
    }
```

