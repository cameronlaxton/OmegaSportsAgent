# Output Formatter Module

"""
Module Name: Output Formatter
Version: 1.0.0
Description: Generates standardized output tables and narrative structure per Required Output Format requirements.
Functions:
    - format_full_suggested_bets_table(bets: list) -> str
    - format_straight_bets_table(bets: list) -> str
    - format_props_only_table(bets: list) -> str
    - format_clv_tracking_table(clv_data: list) -> str
    - format_rejected_bets_log(rejected_bets: list) -> str
    - format_context_drivers_table(context_data: dict) -> str
    - format_risk_stake_table(stake_data: dict) -> str
    - format_simulation_summary_table(sim_results: dict) -> str
    - format_narrative_analysis(bet_data: dict, context_data: dict, sim_results: dict) -> str
    - format_full_output(bet_data: dict, context_data: dict, sim_results: dict, stake_data: dict) -> str
Usage Notes:
    - All functions return markdown-formatted strings ready for LLM output
    - Designed for LLM sandbox environment (no external dependencies)
    - Tables follow exact column specifications from Required Output Format
"""

```python
from __future__ import annotations
from typing import Dict, List, Optional, Any

def format_full_suggested_bets_table(bets: List[Dict[str, Any]]) -> str:
    """
    Formats: Full Suggested Summary Table (all markets)
    Columns: Date | League | GameID | Pick | OddsAmerican | ImpliedProb | ModelProb | Edge | ConfidenceTier | Result | Final Box Score | Factors
    """
    if not bets:
        return "**1. Full Suggested Summary Table (all markets)**\n\n| Date | League | GameID | Pick | OddsAmerican | ImpliedProb | ModelProb | Edge | ConfidenceTier | Result | Final Box Score | Factors |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n| *No qualifying bets* | - | - | - | - | - | - | - | - | - | - | - |\n"
    
    lines = [
        "**1. Full Suggested Summary Table (all markets)**",
        "",
        "| Date | League | GameID | Pick | OddsAmerican | ImpliedProb | ModelProb | Edge | ConfidenceTier | Result | Final Box Score | Factors |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    ]
    
    for bet in bets:
        date = bet.get("date", "N/A")
        league = bet.get("league", "N/A")
        game_id = bet.get("game_id", bet.get("gameID", "N/A"))
        pick = bet.get("pick", bet.get("market", "N/A"))
        odds = bet.get("odds_american", bet.get("odds", "N/A"))
        implied_prob = bet.get("implied_prob", 0.0)
        model_prob = bet.get("model_prob", bet.get("true_prob", 0.0))
        edge = bet.get("edge", bet.get("edge_pct", 0.0))
        tier = bet.get("confidence_tier", "N/A")
        result = bet.get("result", "-")
        box_score = bet.get("final_box_score", bet.get("box_score", "-"))
        factors = bet.get("factors", "-")
        
        lines.append(f"| {date} | {league} | {game_id} | {pick} | {odds} | {implied_prob:.3f} | {model_prob:.3f} | {edge:+.2f}% | {tier} | {result} | {box_score} | {factors} |")
    
    return "\n".join(lines) + "\n"

def format_straight_bets_table(bets: List[Dict[str, Any]]) -> str:
    """
    Formats: Game Bets Table (spread/total/ML only/Game Props)
    Columns: Date | League | GameID | Pick | OddsAmerican | ImpliedProb | ModelProb | Edge | ConfidenceTier | PredictedOutcome | Result | Final Box Score | Factors
    """
    # Filter to only spread/total/ML bets
    straight_bets = [b for b in bets if b.get("market_type") in ["spread", "total", "moneyline", "ML"] or 
                     any(x in str(b.get("pick", "")).upper() for x in ["-", "+", "OVER", "UNDER", "O ", "U "])]
    
    if not straight_bets:
        return "**1a. Game Bets Table (spread/total/ML only/Game Props)**\n\n| Date | League | GameID | Pick | OddsAmerican | ImpliedProb | ModelProb | Edge | ConfidenceTier | PredictedOutcome | Result | Final Box Score | Factors |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n| *No straight bets* | - | - | - | - | - | - | - | - | - | - | - | - |\n"
    
    lines = [
        "**1a. Game Bets Table (spread/total/ML only/Game Props)**",
        "",
        "| Date | League | GameID | Pick | OddsAmerican | ImpliedProb | ModelProb | Edge | ConfidenceTier | PredictedOutcome | Result | Final Box Score | Factors |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    ]
    
    for bet in straight_bets:
        date = bet.get("date", "N/A")
        league = bet.get("league", "N/A")
        game_id = bet.get("game_id", bet.get("gameID", "N/A"))
        pick = bet.get("pick", bet.get("market", "N/A"))
        odds = bet.get("odds_american", bet.get("odds", "N/A"))
        implied_prob = bet.get("implied_prob", 0.0)
        model_prob = bet.get("model_prob", bet.get("true_prob", 0.0))
        edge = bet.get("edge", bet.get("edge_pct", 0.0))
        tier = bet.get("confidence_tier", "N/A")
        predicted = bet.get("predicted_outcome", bet.get("prediction", "-"))
        result = bet.get("result", "-")
        box_score = bet.get("final_box_score", bet.get("box_score", "-"))
        factors = bet.get("factors", "-")
        
        lines.append(f"| {date} | {league} | {game_id} | {pick} | {odds} | {implied_prob:.3f} | {model_prob:.3f} | {edge:+.2f}% | {tier} | {predicted} | {result} | {box_score} | {factors} |")
    
    return "\n".join(lines) + "\n"

def format_props_only_table(bets: List[Dict[str, Any]]) -> str:
    """
    Formats: Player Props Table
    Columns: Date | League | GameID | Player Prop | OddsAmerican | ImpliedProb | ModelProb | Edge | ConfidenceTier | PredictedStat | Result | Final Box Score | Factors
    """
    # Filter to only prop bets
    prop_bets = [b for b in bets if b.get("market_type") == "prop" or 
                 "prop" in str(b.get("pick", "")).lower() or
                 any(x in str(b.get("pick", "")).upper() for x in ["POINTS", "REBOUNDS", "ASSISTS", "YARDS", "TD", "GOALS"])]
    
    if not prop_bets:
        return "**1b. Player Props Table**\n\n| Date | League | GameID | Player Prop | OddsAmerican | ImpliedProb | ModelProb | Edge | ConfidenceTier | PredictedStat | Result | Final Box Score | Factors |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n| *No prop bets* | - | - | - | - | - | - | - | - | - | - | - | - |\n"
    
    lines = [
        "**1b. Player Props Table**",
        "",
        "| Date | League | GameID | Player Prop | OddsAmerican | ImpliedProb | ModelProb | Edge | ConfidenceTier | PredictedStat | Result | Final Box Score | Factors |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    ]
    
    for bet in prop_bets:
        date = bet.get("date", "N/A")
        league = bet.get("league", "N/A")
        game_id = bet.get("game_id", bet.get("gameID", "N/A"))
        prop = bet.get("player_prop", bet.get("pick", bet.get("market", "N/A")))
        odds = bet.get("odds_american", bet.get("odds", "N/A"))
        implied_prob = bet.get("implied_prob", 0.0)
        model_prob = bet.get("model_prob", bet.get("true_prob", 0.0))
        edge = bet.get("edge", bet.get("edge_pct", 0.0))
        tier = bet.get("confidence_tier", "N/A")
        predicted_stat = bet.get("predicted_stat", bet.get("prediction", "-"))
        result = bet.get("result", "-")
        box_score = bet.get("final_box_score", bet.get("box_score", "-"))
        factors = bet.get("factors", "-")
        
        lines.append(f"| {date} | {league} | {game_id} | {prop} | {odds} | {implied_prob:.3f} | {model_prob:.3f} | {edge:+.2f}% | {tier} | {predicted_stat} | {result} | {box_score} | {factors} |")
    
    return "\n".join(lines) + "\n"

def format_clv_tracking_table(clv_data: List[Dict[str, Any]]) -> str:
    """
    Formats: CLV Tracking Table (optional, if applicable)
    Columns: Date | League | GameID | Pick | YourLine | ClosingLine | CLV | Notes
    """
    if not clv_data:
        return ""  # Don't show table if no CLV data
    
    lines = [
        "**CLV Tracking Table**",
        "",
        "| Date | League | GameID | Pick | YourLine | ClosingLine | CLV | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |"
    ]
    
    for entry in clv_data:
        date = entry.get("date", "N/A")
        league = entry.get("league", "N/A")
        game_id = entry.get("game_id", entry.get("gameID", "N/A"))
        pick = entry.get("pick", "N/A")
        your_line = entry.get("your_line", entry.get("open_line", "N/A"))
        closing_line = entry.get("closing_line", "N/A")
        clv = entry.get("clv", entry.get("CLV", 0.0))
        notes = entry.get("notes", "-")
        
        lines.append(f"| {date} | {league} | {game_id} | {pick} | {your_line} | {closing_line} | {clv:+.3f} | {notes} |")
    
    return "\n".join(lines) + "\n"

def format_rejected_bets_log(rejected_bets: List[Dict[str, Any]]) -> str:
    """
    Formats: Rejected Bets Log (optional, if applicable)
    Columns: Game | Market | Book Line | ImpliedProb | ModelProb | Edge | ReasonRejected
    """
    if not rejected_bets:
        return "**Rejected Bets Log**\n\n| Game | Market | Book Line | ImpliedProb | ModelProb | Edge | ReasonRejected |\n| --- | --- | --- | --- | --- | --- | --- |\n| *No rejected bets* | - | - | - | - | - | - |\n"
    
    lines = [
        "**Rejected Bets Log**",
        "",
        "| Game | Market | Book Line | ImpliedProb | ModelProb | Edge | ReasonRejected |",
        "| --- | --- | --- | --- | --- | --- | --- |"
    ]
    
    for bet in rejected_bets:
        game = bet.get("game", bet.get("game_id", "N/A"))
        market = bet.get("market", bet.get("pick", "N/A"))
        book_line = bet.get("book_line", bet.get("odds", "N/A"))
        implied_prob = bet.get("implied_prob", 0.0)
        model_prob = bet.get("model_prob", bet.get("true_prob", 0.0))
        edge = bet.get("edge", bet.get("edge_pct", 0.0))
        reason = bet.get("reason_rejected", bet.get("reason", "Sub-threshold edge"))
        
        lines.append(f"| {game} | {market} | {book_line} | {implied_prob:.3f} | {model_prob:.3f} | {edge:+.2f}% | {reason} |")
    
    return "\n".join(lines) + "\n"

def format_context_drivers_table(context_data: Dict[str, Any]) -> str:
    """
    Formats Context Drivers table with columns: Factor, Value, Impact Note
    
    Args:
        context_data: Dictionary containing context factors:
            - weather: dict with keys like "temperature", "wind", "precipitation", "roof_status"
            - rest: dict with "days_rest", "back_to_back", "travel_miles", "timezone_shift"
            - pace: dict with "pace_delta", "game_script_bias"
            - injuries: dict with "key_injuries", "usage_redistribution"
            - venue: dict with "home_advantage", "altitude", etc.
    
    Returns:
        Markdown table string
    """
    lines = ["**Context Drivers**", "", "| Factor | Value | Impact Note |", "| --- | --- | --- |"]
    
    factors = []
    
    # Weather factors
    if "weather" in context_data:
        weather = context_data["weather"]
        if "temperature" in weather:
            temp = weather["temperature"]
            impact = "Cold reduces scoring" if temp < 40 else "Normal conditions" if temp < 80 else "Heat may affect pace"
            factors.append(("Temperature (°F)", f"{temp:.0f}", impact))
        if "wind" in weather:
            wind = weather["wind"]
            impact = "Strong wind affects passing/kicking" if wind > 15 else "Minimal wind impact"
            factors.append(("Wind (mph)", f"{wind:.0f}", impact))
        if "precipitation" in weather:
            precip = weather["precipitation"]
            impact = "Precipitation reduces scoring efficiency" if precip > 0 else "Clear conditions"
            factors.append(("Precipitation", f"{precip:.2f}\"" if precip > 0 else "None", impact))
        if "roof_status" in weather:
            roof = weather["roof_status"]
            factors.append(("Roof Status", roof, "Dome eliminates weather impact" if roof == "closed" else "Open to elements"))
    
    # Rest factors
    if "rest" in context_data:
        rest = context_data["rest"]
        if "days_rest" in rest:
            days = rest["days_rest"]
            impact = "Optimal rest" if 2 <= days <= 3 else "Potential fatigue" if days < 2 else "Extended rest may reduce sharpness"
            factors.append(("Days Rest", f"{days:.1f}", impact))
        if "back_to_back" in rest:
            b2b = rest["back_to_back"]
            factors.append(("Back-to-Back", "Yes" if b2b else "No", "Fatigue factor" if b2b else "Normal schedule"))
        if "travel_miles" in rest:
            travel = rest["travel_miles"]
            impact = "Significant travel fatigue" if travel > 2000 else "Minimal travel impact" if travel < 500 else "Moderate travel"
            factors.append(("Travel Miles", f"{travel:.0f}", impact))
        if "timezone_shift" in rest:
            tz = rest["timezone_shift"]
            impact = "Significant jet lag" if abs(tz) >= 3 else "Minimal timezone impact"
            factors.append(("Timezone Shift", f"{tz:+.0f} hrs", impact))
    
    # Pace factors
    if "pace" in context_data:
        pace = context_data["pace"]
        if "pace_delta" in pace:
            delta = pace["delta"]
            impact = f"Pace {'increased' if delta > 0 else 'decreased'} by {abs(delta):.1f} possessions"
            factors.append(("Pace Delta", f"{delta:+.1f}", impact))
        if "game_script_bias" in pace:
            bias = pace["game_script_bias"]
            factors.append(("Game Script Bias", bias, "Affects late-game scoring patterns"))
    
    # Injury factors
    if "injuries" in context_data:
        injuries = context_data["injuries"]
        if "key_injuries" in injuries:
            key_inj = injuries["key_injuries"]
            factors.append(("Key Injuries", f"{len(key_inj)} players", "Usage redistribution applied"))
        if "usage_redistribution" in injuries:
            redis = injuries["usage_redistribution"]
            factors.append(("Usage Redistribution", "Applied", f"Affects {len(redis)} positions"))
    
    # Venue factors
    if "venue" in context_data:
        venue = context_data["venue"]
        if "home_advantage" in venue:
            ha = venue["home_advantage"]
            factors.append(("Home Advantage", f"{ha:.1f} pts", "Standard home court/field advantage"))
        if "altitude" in venue:
            alt = venue["altitude"]
            if alt > 4000:
                factors.append(("Altitude", f"{alt:.0f} ft", "High altitude affects endurance"))
    
    if not factors:
        factors.append(("No Context Data", "-", "Standard conditions assumed"))
    
    for factor, value, impact in factors:
        lines.append(f"| {factor} | {value} | {impact} |")
    
    return "\n".join(lines) + "\n"

def format_risk_stake_table(stake_data: Dict[str, Any]) -> str:
    """
    Formats Risk & Stake table with columns: Bankroll Ref, Unit Size ($5 multiples), Kelly Fraction, Final Stake, Notes
    
    Args:
        stake_data: Dictionary containing:
            - bankroll: float (total bankroll)
            - unit_size: float (typically $5)
            - kelly_fraction: float (0-1, typically 0.25 for quarter-Kelly)
            - final_stake: float (dollar amount)
            - notes: str (additional context)
            - confidence_tier: str (for tier cap reference)
    
    Returns:
        Markdown table string
    """
    bankroll = stake_data.get("bankroll", 2000.0)
    unit_size = stake_data.get("unit_size", 5.0)
    kelly_frac = stake_data.get("kelly_fraction", 0.25)
    final_stake = stake_data.get("final_stake", 0.0)
    notes = stake_data.get("notes", "")
    tier = stake_data.get("confidence_tier", "N/A")
    
    units = final_stake / unit_size if unit_size > 0 else 0.0
    
    lines = [
        "**Risk & Stake**",
        "",
        "| Bankroll Ref | Unit Size ($5 multiples) | Kelly Fraction | Final Stake | Notes |",
        "| --- | --- | --- | --- | --- |",
        f"| ${bankroll:.2f} | {units:.2f} | {kelly_frac:.2f} | ${final_stake:.2f} | {notes} (Tier: {tier}) |"
    ]
    
    return "\n".join(lines) + "\n"

def format_simulation_summary_table(sim_results: Dict[str, Any]) -> str:
    """
    Formats Simulation Summary table with key simulation metrics
    
    Args:
        sim_results: Dictionary containing:
            - n_iterations: int
            - true_prob: float
            - confidence_interval: tuple (lower, upper) or dict
            - distribution_used: str
            - mean: float
            - variance: float
    
    Returns:
        Markdown table string
    """
    n_iter = sim_results.get("n_iterations", 0)
    true_prob = sim_results.get("true_prob", 0.0)
    dist = sim_results.get("distribution_used", "N/A")
    mean = sim_results.get("mean", 0.0)
    variance = sim_results.get("variance", 0.0)
    ci = sim_results.get("confidence_interval", None)
    
    ci_str = "N/A"
    if ci:
        if isinstance(ci, (list, tuple)) and len(ci) == 2:
            ci_str = f"[{ci[0]:.3f}, {ci[1]:.3f}]"
        elif isinstance(ci, dict):
            ci_str = f"[{ci.get('lower', 0):.3f}, {ci.get('upper', 1):.3f}]"
    
    lines = [
        "**Simulation Summary**",
        "",
        "| Iterations | True Prob | Distribution | Mean | Variance | 95% CI |",
        "| --- | --- | --- | --- | --- | --- |",
        f"| {n_iter:,} | {true_prob:.3f} | {dist} | {mean:.2f} | {variance:.2f} | {ci_str} |"
    ]
    
    return "\n".join(lines) + "\n"

def format_narrative_analysis(bet_data: Dict[str, Any], context_data: Dict[str, Any], sim_results: Dict[str, Any], module_citations: Optional[List[str]] = None) -> str:
    """
    Formats narrative analysis section that cites module functions and explains reasoning
    
    Args:
        bet_data: Bet evaluation data
        context_data: Context drivers data
        sim_results: Simulation results
        module_citations: List of module function calls made (e.g., ["simulation_engine.run_game_simulation", "odds_eval.expected_value_percent"])
    
    Returns:
        Formatted narrative string
    """
    narrative_parts = []
    
    # Opening statement
    market = bet_data.get("market", "N/A")
    league = bet_data.get("league", "N/A")
    narrative_parts.append(f"## Analysis: {market} ({league})")
    narrative_parts.append("")
    
    # Module citations
    if module_citations:
        narrative_parts.append("**Module Functions Executed:**")
        for citation in module_citations:
            narrative_parts.append(f"- `{citation}`")
        narrative_parts.append("")
    
    # Context summary
    narrative_parts.append("### Context Assessment")
    key_factors = []
    if "weather" in context_data:
        key_factors.append("weather conditions")
    if "rest" in context_data and context_data["rest"].get("back_to_back"):
        key_factors.append("back-to-back scheduling")
    if "rest" in context_data and context_data["rest"].get("travel_miles", 0) > 1000:
        key_factors.append("significant travel")
    if "injuries" in context_data and context_data["injuries"].get("key_injuries"):
        key_factors.append("key injury impacts")
    
    if key_factors:
        narrative_parts.append(f"Primary contextual drivers include: {', '.join(key_factors)}. These factors have been normalized and applied through the projection pipeline.")
    else:
        narrative_parts.append("Standard contextual conditions; no significant deviations from baseline expected.")
    narrative_parts.append("")
    
    # Simulation summary
    narrative_parts.append("### Simulation Results")
    true_prob = sim_results.get("true_prob", 0.0)
    n_iter = sim_results.get("n_iterations", 10000)
    dist = sim_results.get("distribution_used", "auto-selected")
    narrative_parts.append(f"Monte Carlo simulation ({n_iter:,} iterations) using {dist} distribution indicates a true win probability of {true_prob:.1%}.")
    
    ci = sim_results.get("confidence_interval")
    if ci:
        if isinstance(ci, (list, tuple)) and len(ci) == 2:
            ci_width = ci[1] - ci[0]
            narrative_parts.append(f"95% confidence interval: [{ci[0]:.1%}, {ci[1]:.1%}] (width: {ci_width:.1%}).")
    
    narrative_parts.append("")
    
    # Edge and EV analysis
    narrative_parts.append("### Edge & Value Assessment")
    true_prob_val = bet_data.get("true_prob", 0.0)
    implied_prob = bet_data.get("implied_prob", 0.0)
    edge_pct = bet_data.get("edge_pct", 0.0)
    ev_pct = bet_data.get("ev_pct", 0.0)
    tier = bet_data.get("confidence_tier", "Pass")
    
    narrative_parts.append(f"Market implied probability: {implied_prob:.1%}; model true probability: {true_prob_val:.1%}.")
    narrative_parts.append(f"Edge: {edge_pct:+.2f} percentage points; Expected Value: {ev_pct:+.2f}%.")
    
    # Threshold assessment
    edge_threshold = 3.0
    ev_threshold = 2.5
    if edge_pct >= edge_threshold and ev_pct >= ev_threshold:
        narrative_parts.append(f"**Thresholds satisfied** (edge ≥ {edge_threshold}%, EV ≥ {ev_threshold}%); confidence tier: {tier}.")
    else:
        narrative_parts.append(f"**Thresholds not met** (edge {edge_pct:.2f}% < {edge_threshold}% or EV {ev_pct:.2f}% < {ev_threshold}%); recommendation: **Pass (Sub-threshold)**.")
    
    narrative_parts.append("")
    
    # Risk caveats
    narrative_parts.append("### Risk Considerations")
    narrative_parts.append("All probabilities and edge calculations derived from module functions; no manual approximations used. Model assumes current injury status and contextual factors remain stable. Market efficiency and sharp action may impact closing line value.")
    
    return "\n".join(narrative_parts) + "\n"

def format_full_output(bet_data: Dict[str, Any], context_data: Dict[str, Any], sim_results: Dict[str, Any], stake_data: Optional[Dict[str, Any]] = None, module_citations: Optional[List[str]] = None, rejected_bets: Optional[List[Dict[str, Any]]] = None, clv_data: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Formats complete output following Required Output Format requirements
    
    Args:
        bet_data: Bet evaluation data (can be list for multiple bets)
        context_data: Context drivers data
        sim_results: Simulation results (can be list for multiple bets)
        stake_data: Stake recommendation data (optional)
        module_citations: List of module function calls made
        rejected_bets: List of rejected bet dictionaries (optional)
        clv_data: List of CLV tracking dictionaries (optional)
    
    Returns:
        Complete formatted output string
    """
    output_parts = []
    
    # Handle single bet vs multiple bets
    if isinstance(bet_data, list):
        bets = bet_data
    else:
        bets = [bet_data]
    
    if isinstance(sim_results, list):
        sims = sim_results
    else:
        sims = [sim_results]
    
    # Narrative analysis (comes first per protocol)
    if len(bets) == 1:
        output_parts.append(format_narrative_analysis(bets[0], context_data, sims[0] if sims else {}, module_citations))
    else:
        output_parts.append("## Multi-Bet Analysis\n")
        for i, (bet, sim) in enumerate(zip(bets, sims), 1):
            output_parts.append(f"### Bet {i}: {bet.get('market', 'N/A')}\n")
            output_parts.append(format_narrative_analysis(bet, context_data, sim, module_citations))
    
    # Required Output Format tables in order (1, 1a, 1b, then optional tables)
    output_parts.append(format_full_suggested_bets_table(bets))
    output_parts.append(format_straight_bets_table(bets))
    output_parts.append(format_props_only_table(bets))
    
    if clv_data:
        output_parts.append(format_clv_tracking_table(clv_data))
    
    if rejected_bets:
        output_parts.append(format_rejected_bets_log(rejected_bets))
    
    # Optional supporting tables (CLV, Rejected Bets, Context Drivers, Simulation Summary, Risk & Stake)
    output_parts.append(format_context_drivers_table(context_data))
    
    if len(sims) > 0 and sims[0]:
        output_parts.append(format_simulation_summary_table(sims[0]))
    
    if stake_data:
        output_parts.append(format_risk_stake_table(stake_data))
    
    return "\n\n".join(output_parts)

```

