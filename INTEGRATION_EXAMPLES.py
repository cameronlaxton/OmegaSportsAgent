"""
Example Integration Code Snippets

These snippets show minimal code changes to integrate BetRecorder and CalibrationLoader
into existing workflows.

Copy and adapt these examples to your specific use case.
"""

from typing import Dict, Any
from datetime import datetime

# ============================================================================
# SNIPPET 1: Add to top of omega/workflows/morning_bets.py
# ============================================================================

"""
Add these imports at the top of the file:
"""

from outputs.bet_recorder import BetRecorder
from config.calibration_loader import CalibrationLoader


# ============================================================================
# SNIPPET 2: Modify evaluate_bet() function
# ============================================================================

"""
Original evaluate_bet() function uses static thresholds from model_config.
Enhanced version uses CalibrationLoader for dynamic thresholds and transforms.

OPTION A: Minimal change (keep existing function, add new one)
"""

def evaluate_bet_with_calibration(
    model_prob: float,
    market_odds: int,
    bet_type: str,
    league: str,
    calibration_loader: CalibrationLoader
) -> Dict[str, Any]:
    """
    Evaluate a single bet using calibrated parameters.
    
    Enhances evaluate_bet() with:
    - Probability transforms from calibration pack
    - Dynamic edge thresholds per market type
    - Calibrated Kelly fraction
    """
    # Apply probability transform
    transform = calibration_loader.get_probability_transform(bet_type)
    if transform:
        adjusted_prob = transform(model_prob)
    else:
        adjusted_prob = model_prob
    
    # Get dynamic edge threshold
    edge_threshold = calibration_loader.get_edge_threshold(bet_type)
    
    # Calculate edge using adjusted probability
    implied_prob = implied_probability(market_odds)
    edge_pct = (adjusted_prob - implied_prob) * 100.0
    ev_pct = expected_value_percent(adjusted_prob, market_odds)
    
    # Determine confidence tier (using existing tier logic)
    tiers = get_confidence_tier_caps()
    if edge_pct >= tiers["tier_a"]["min_edge_pct"] and ev_pct >= tiers["tier_a"]["min_ev_pct"]:
        confidence_tier = "A"
        max_units = tiers["tier_a"]["max_units"]
    elif edge_pct >= tiers["tier_b"]["min_edge_pct"] and ev_pct >= tiers["tier_b"]["min_ev_pct"]:
        confidence_tier = "B"
        max_units = tiers["tier_b"]["max_units"]
    elif edge_pct >= tiers["tier_c"]["min_edge_pct"] and ev_pct >= tiers["tier_c"]["min_ev_pct"]:
        confidence_tier = "C"
        max_units = tiers["tier_c"]["max_units"]
    else:
        confidence_tier = "Pass"
        max_units = 0.0
    
    # Check if bet qualifies using calibrated threshold
    is_qualified = edge_pct >= edge_threshold * 100.0  # Convert to percentage
    
    # Calculate stake using calibrated Kelly
    kelly_frac = calibration_loader.get_kelly_fraction()
    if is_qualified:
        stake_rec = recommend_stake(
            adjusted_prob, 
            market_odds, 
            bankroll=1000.0, 
            confidence_tier=confidence_tier
        )
    else:
        stake_rec = {"units": 0.0, "stake_amount": 0.0}
    
    return {
        "model_prob": adjusted_prob,
        "raw_model_prob": model_prob,
        "implied_prob": implied_prob,
        "edge_pct": edge_pct,
        "edge_threshold": edge_threshold,
        "ev_pct": ev_pct,
        "confidence_tier": confidence_tier,
        "max_units": max_units,
        "recommended_units": min(stake_rec.get("units", 0.0), max_units),
        "recommended_stake": stake_rec.get("stake_amount", 0.0),
        "is_qualified": is_qualified,
        "bet_type": bet_type,
        "kelly_fraction": kelly_frac
    }


# ============================================================================
# SNIPPET 3: Modify evaluate_game() to use calibration and record bets
# ============================================================================

"""
Enhanced evaluate_game() that loads calibration and records qualified bets.
"""

def evaluate_game(
    game: Dict[str, Any],
    league: str,
    n_iter: int = 10000
) -> Dict[str, Any]:
    """
    Evaluate a single game for betting opportunities.
    Enhanced with CalibrationLoader and BetRecorder.
    """
    # Load calibration pack for this league
    cal = CalibrationLoader(league)
    calibration_version = cal.get_version()
    
    game_id = game.get("game_id", game.get("id", "unknown"))
    home_team = game.get("home_team", {})
    away_team = game.get("away_team", {})
    
    home_name = home_team.get("name", home_team) if isinstance(home_team, dict) else str(home_team)
    away_name = away_team.get("name", away_team) if isinstance(away_team, dict) else str(away_team)
    
    # Get team stats and run simulation (existing code)
    home_stats = get_team_stats(home_name, league)
    away_stats = get_team_stats(away_name, league)
    
    home_off = home_stats.get("off_rating", 110.0) if home_stats else 110.0
    away_off = away_stats.get("off_rating", 108.0) if away_stats else 108.0
    
    projection = {
        "off_rating": {home_name: home_off, away_name: away_off},
        "league": league,
        "variance_scalar": 1.0
    }
    
    sim_results = run_game_simulation(projection, n_iter=n_iter, league=league)
    
    home_win_prob = sim_results.get("true_prob_a", 0.5)
    away_win_prob = sim_results.get("true_prob_b", 0.5)
    
    qualified_bets = []
    date = datetime.now().strftime("%Y-%m-%d")
    
    # Evaluate home moneyline
    home_ml_odds = game.get("home_ml_odds", -110)
    if isinstance(home_ml_odds, (int, float)):
        home_eval = evaluate_bet_with_calibration(
            home_win_prob, 
            int(home_ml_odds), 
            "moneyline",
            league,
            cal
        )
        
        if home_eval["is_qualified"]:
            bet_id = f"{game_id}_ml_home"
            
            # Record to Validation Lab format
            BetRecorder.record_bet(
                date=date,
                league=league,
                bet_id=bet_id,
                game_id=game_id,
                game_date=date,
                market_type="moneyline",
                recommendation="HOME",
                edge=home_eval["edge_pct"] / 100.0,
                model_probability=home_eval["model_prob"],
                market_probability=home_eval["implied_prob"],
                stake=home_eval["recommended_stake"],
                odds=home_ml_odds,
                edge_threshold=home_eval["edge_threshold"],
                kelly_fraction=home_eval["kelly_fraction"],
                confidence=home_eval["confidence_tier"].lower() if home_eval["confidence_tier"] != "Pass" else "low",
                calibration_version=calibration_version,
                metadata={
                    "home_team": home_name,
                    "away_team": away_name,
                    "matchup": f"{away_name} @ {home_name}"
                }
            )
            
            # Add to qualified_bets for output formatting
            home_eval.update({
                "game_id": game_id,
                "matchup": f"{away_name} @ {home_name}",
                "pick": f"{home_name} ML",
                "odds": home_ml_odds,
                "league": league,
                "date": date,
                "bet_id": bet_id
            })
            qualified_bets.append(home_eval)
    
    # Evaluate away moneyline (similar pattern)
    away_ml_odds = game.get("away_ml_odds", 110)
    if isinstance(away_ml_odds, (int, float)):
        away_eval = evaluate_bet_with_calibration(
            away_win_prob,
            int(away_ml_odds),
            "moneyline",
            league,
            cal
        )
        
        if away_eval["is_qualified"]:
            bet_id = f"{game_id}_ml_away"
            
            BetRecorder.record_bet(
                date=date,
                league=league,
                bet_id=bet_id,
                game_id=game_id,
                game_date=date,
                market_type="moneyline",
                recommendation="AWAY",
                edge=away_eval["edge_pct"] / 100.0,
                model_probability=away_eval["model_prob"],
                market_probability=away_eval["implied_prob"],
                stake=away_eval["recommended_stake"],
                odds=away_ml_odds,
                edge_threshold=away_eval["edge_threshold"],
                kelly_fraction=away_eval["kelly_fraction"],
                confidence=away_eval["confidence_tier"].lower() if away_eval["confidence_tier"] != "Pass" else "low",
                calibration_version=calibration_version,
                metadata={
                    "home_team": home_name,
                    "away_team": away_name,
                    "matchup": f"{away_name} @ {home_name}"
                }
            )
            
            away_eval.update({
                "game_id": game_id,
                "matchup": f"{away_name} @ {home_name}",
                "pick": f"{away_name} ML",
                "odds": away_ml_odds,
                "league": league,
                "date": date,
                "bet_id": bet_id
            })
            qualified_bets.append(away_eval)
    
    # Add similar logic for spreads and totals...
    
    return {
        "game_id": game_id,
        "matchup": f"{away_name} @ {home_name}",
        "league": league,
        "home_team": home_name,
        "away_team": away_name,
        "home_win_prob": home_win_prob,
        "away_win_prob": away_win_prob,
        "simulation_results": sim_results,
        "qualified_bets": qualified_bets,
        "evaluated_at": datetime.now().isoformat(),
        "calibration_version": calibration_version
    }


# ============================================================================
# SNIPPET 4: Simple stand-alone example
# ============================================================================

"""
Minimal stand-alone script showing the complete flow.
"""

def simple_example():
    from datetime import datetime
    from outputs.bet_recorder import BetRecorder
    from config.calibration_loader import CalibrationLoader
    from omega.betting.odds_eval import implied_probability
    
    # 1. Load calibration
    league = "NBA"
    cal = CalibrationLoader(league)
    print(f"Using {league} calibration version: {cal.get_version()}")
    
    # 2. Simulate a bet evaluation
    game_id = "401234567"
    market_type = "moneyline"
    market_odds = -150
    raw_model_prob = 0.65
    
    # 3. Apply probability transform
    transform = cal.get_probability_transform(market_type)
    if transform:
        model_prob = transform(raw_model_prob)
        print(f"Transform applied: {raw_model_prob:.3f} → {model_prob:.3f}")
    else:
        model_prob = raw_model_prob
    
    # 4. Calculate edge
    market_prob = implied_probability(market_odds)
    edge = model_prob - market_prob
    edge_threshold = cal.get_edge_threshold(market_type)
    
    print(f"Edge: {edge:.1%}, Threshold: {edge_threshold:.1%}")
    
    # 5. Check if qualifies
    if edge >= edge_threshold:
        print("✓ Bet qualifies!")
        
        # 6. Record bet
        date = datetime.now().strftime("%Y-%m-%d")
        bet_id = f"{game_id}_ml_home"
        
        filepath = BetRecorder.record_bet(
            date=date,
            league=league,
            bet_id=bet_id,
            game_id=game_id,
            game_date=date,
            market_type=market_type,
            recommendation="HOME",
            edge=edge,
            model_probability=model_prob,
            market_probability=market_prob,
            stake=10.0,
            odds=market_odds,
            edge_threshold=edge_threshold,
            kelly_fraction=cal.get_kelly_fraction(),
            confidence="medium",
            calibration_version=cal.get_version()
        )
        
        print(f"✓ Bet recorded to: {filepath}")
    else:
        print("✗ Bet does not qualify")


# ============================================================================
# SNIPPET 5: Backward compatibility - using both old and new systems
# ============================================================================

"""
Show how to use both old logging and new BetRecorder for transition period.
"""

def record_to_both_systems(bet_data: Dict[str, Any], league: str):
    """
    Record bet to both old and new systems during transition.
    """
    from omega.utilities.data_logging import log_bet_recommendation
    from outputs.bet_recorder import BetRecorder
    
    date = bet_data["date"]
    
    # Old system (for backward compatibility)
    log_bet_recommendation(date=date, bet_data=bet_data)
    
    # New system (for Validation Lab)
    BetRecorder.record_bet(
        date=date,
        league=league,
        bet_id=bet_data["bet_id"],
        game_id=bet_data["game_id"],
        game_date=date,
        market_type=bet_data["market_type"],
        recommendation=bet_data["recommendation"],
        edge=bet_data["edge"],
        model_probability=bet_data["model_prob"],
        market_probability=bet_data["market_prob"],
        stake=bet_data["stake"],
        odds=bet_data["odds"],
        calibration_version=bet_data.get("calibration_version", "unknown")
    )
    
    print(f"Bet {bet_data['bet_id']} recorded to both systems")


if __name__ == "__main__":
    # Run simple example
    simple_example()
