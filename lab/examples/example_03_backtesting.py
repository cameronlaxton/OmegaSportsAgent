#!/usr/bin/env python3
"""
Database Integration Example 3: Simple Backtesting
==================================================

This example demonstrates how to use the database for simple backtesting
of betting strategies.

Prerequisites:
    - Run data collection:
      python scripts/collect_historical_sqlite.py --sports NBA --start-year 2023 --end-year 2024

What You'll Learn:
    1. How to backtest a simple betting strategy
    2. How to calculate ROI and win rate
    3. How to analyze betting performance by different criteria
    4. How to use historical data for validation
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db_manager import DatabaseManager


# Betting constants
# At -110 odds (standard sportsbook line), you risk $110 to win $100
# Payout ratio = 100/110 = 0.909 units profit per 1 unit risked
STANDARD_ODDS_PAYOUT = 0.909
UNIT_SIZE = 1.0  # Standard betting unit


def calculate_bet_result(actual_margin, spread_line):
    """
    Calculate if a spread bet won.
    
    Args:
        actual_margin: Actual home team margin (home_score - away_score)
        spread_line: Spread line (negative means home team favored)
    
    Returns:
        'WIN' if bet won, 'LOSS' if bet lost, 'PUSH' if push
    """
    # Bet on home team with spread
    cover_margin = actual_margin + spread_line
    
    if abs(cover_margin) < 0.5:  # Push
        return 'PUSH'
    elif cover_margin > 0:
        return 'WIN'
    else:
        return 'LOSS'


def main():
    print("=" * 80)
    print("Database Integration Example 3: Simple Backtesting")
    print("=" * 80)
    print()

    # Step 1: Connect to the database
    print("Step 1: Connecting to database...")
    db = DatabaseManager("data/sports_data.db")
    conn = db.get_connection()
    cursor = conn.cursor()
    print("✓ Connected to data/sports_data.db")
    print()

    # Step 2: Load games with spread lines
    print("Step 2: Loading games with betting lines...")
    cursor.execute("""
        SELECT game_id, date, home_team, away_team, 
               home_score, away_score,
               spread_line, spread_home_odds, spread_away_odds,
               total_line, total_over_odds, total_under_odds
        FROM games
        WHERE sport = 'NBA'
          AND home_score IS NOT NULL
          AND away_score IS NOT NULL
          AND spread_line IS NOT NULL
        ORDER BY date
    """)
    
    games = cursor.fetchall()
    print(f"Loaded {len(games):,} NBA games with complete data")
    print()

    # Step 3: Simple strategy - Always bet home team with spread
    print("Step 3: Testing Strategy 1 - Always bet home team with spread...")
    print("-" * 80)
    
    wins = 0
    losses = 0
    pushes = 0
    total_units = 0.0
    
    for game in games:
        actual_margin = game['home_score'] - game['away_score']
        spread_line = game['spread_line']
        
        # Calculate bet result
        result = calculate_bet_result(actual_margin, spread_line)
        
        if result == 'WIN':
            wins += 1
            # At -110 odds, winning $1 unit bet returns profit
            total_units += STANDARD_ODDS_PAYOUT * UNIT_SIZE
        elif result == 'LOSS':
            losses += 1
            total_units -= UNIT_SIZE
        else:  # PUSH
            pushes += 1
            # No change in units
    
    total_bets = wins + losses + pushes
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    roi = (total_units / total_bets * 100) if total_bets > 0 else 0
    
    print(f"Total bets: {total_bets:,}")
    print(f"Wins: {wins:,} ({win_rate:.2f}%)")
    print(f"Losses: {losses:,}")
    print(f"Pushes: {pushes:,}")
    print(f"Net units: {total_units:+.2f}")
    print(f"ROI: {roi:+.2f}%")
    print()

    # Step 4: Strategy 2 - Only bet favorites (negative spread)
    print("Step 4: Testing Strategy 2 - Only bet favorites...")
    print("-" * 80)
    
    wins = 0
    losses = 0
    pushes = 0
    total_units = 0.0
    
    for game in games:
        spread_line = game['spread_line']
        
        # Only bet when home team is favorite (negative spread)
        if spread_line >= 0:
            continue
        
        actual_margin = game['home_score'] - game['away_score']
        result = calculate_bet_result(actual_margin, spread_line)
        
        if result == 'WIN':
            wins += 1
            total_units += STANDARD_ODDS_PAYOUT * UNIT_SIZE
        elif result == 'LOSS':
            losses += 1
            total_units -= UNIT_SIZE
        else:
            pushes += 1
    
    total_bets = wins + losses + pushes
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    roi = (total_units / total_bets * 100) if total_bets > 0 else 0
    
    print(f"Total bets: {total_bets:,} (only favorites)")
    print(f"Wins: {wins:,} ({win_rate:.2f}%)")
    print(f"Losses: {losses:,}")
    print(f"Pushes: {pushes:,}")
    print(f"Net units: {total_units:+.2f}")
    print(f"ROI: {roi:+.2f}%")
    print()

    # Step 5: Strategy 3 - Only bet underdogs (positive spread)
    print("Step 5: Testing Strategy 3 - Only bet underdogs...")
    print("-" * 80)
    
    wins = 0
    losses = 0
    pushes = 0
    total_units = 0.0
    
    for game in games:
        spread_line = game['spread_line']
        
        # Only bet when away team is underdog (home team has negative spread)
        # We bet away team, so we invert the spread
        if spread_line >= 0:
            continue
        
        actual_margin = game['home_score'] - game['away_score']
        # Invert spread for away team bet
        result = calculate_bet_result(-actual_margin, -spread_line)
        
        if result == 'WIN':
            wins += 1
            total_units += STANDARD_ODDS_PAYOUT * UNIT_SIZE
        elif result == 'LOSS':
            losses += 1
            total_units -= UNIT_SIZE
        else:
            pushes += 1
    
    total_bets = wins + losses + pushes
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    roi = (total_units / total_bets * 100) if total_bets > 0 else 0
    
    print(f"Total bets: {total_bets:,} (only underdogs)")
    print(f"Wins: {wins:,} ({win_rate:.2f}%)")
    print(f"Losses: {losses:,}")
    print(f"Pushes: {pushes:,}")
    print(f"Net units: {total_units:+.2f}")
    print(f"ROI: {roi:+.2f}%")
    print()

    # Step 6: Analyze results by month
    print("Step 6: Analyzing results by month...")
    print("-" * 80)
    
    cursor.execute("""
        SELECT strftime('%Y-%m', date) as month,
               COUNT(*) as games,
               AVG(CASE 
                   WHEN (home_score - away_score + spread_line) > 0 THEN 1.0
                   WHEN ABS(home_score - away_score + spread_line) < 0.5 THEN 0.0
                   ELSE -1.0
               END) as avg_result
        FROM games
        WHERE sport = 'NBA'
          AND home_score IS NOT NULL
          AND away_score IS NOT NULL
          AND spread_line IS NOT NULL
        GROUP BY month
        ORDER BY month
    """)
    
    print(f"{'Month':<10} {'Games':<10} {'Avg Result':<15}")
    print("-" * 40)
    for row in cursor.fetchall():
        avg_result = row['avg_result'] * 100 if row['avg_result'] else 0
        print(f"{row['month']:<10} {row['games']:<10} {avg_result:+.2f}%")
    print()

    print("=" * 80)
    print("Example completed successfully!")
    print("=" * 80)
    print()
    print("Key Insights:")
    print("  - Simple strategies rarely beat the house edge (-110 odds = ~4.5% edge)")
    print("  - Need to hit 52.4% to break even at -110 odds")
    print("  - This demonstrates the importance of edge detection")
    print()
    print("Next steps:")
    print("  - Implement more sophisticated strategies")
    print("  - Use Module 1 for edge threshold calibration")
    print("  - Test with Kelly Criterion for optimal bet sizing")
    print()


if __name__ == "__main__":
    main()
