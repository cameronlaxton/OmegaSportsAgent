#!/usr/bin/env python3
"""
Check collection and enrichment status across all games.
"""

import sys
import sqlite3

def check_status(db_path='data/sports_data.db'):
    """Check collection and enrichment status."""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("📊 OMEGASPORTS DATA COLLECTION STATUS")
    print("="*80)
    
    # Overall stats
    cursor.execute("""
        SELECT 
            sport,
            season,
            COUNT(*) as total_games,
            SUM(has_player_stats) as with_stats,
            SUM(has_odds) as with_odds,
            MIN(date) as first_game,
            MAX(date) as last_game
        FROM games
        GROUP BY sport, season
        ORDER BY sport, season
    """)
    
    results = cursor.fetchall()
    
    if not results:
        print("\n❌ No games found in database\n")
        return
    
    # Print results
    print("\n{:<8} {:<8} {:<8} {:<20} {:<20} {:<12} {:<12}".format(
        'Sport', 'Season', 'Total', 'Stats', 'Odds', 'First', 'Last'
    ))
    print("-" * 100)
    
    for row in results:
        sport, season, total, stats, odds, first, last = row
        
        # Handle NULL values
        stats = stats or 0
        odds = odds or 0
        # Calculate percentages
        stats_pct = f"{stats}/{total} ({stats*100/total:.0f}%)" if total > 0 else "0/0"
        odds_pct = f"{odds}/{total} ({odds*100/total:.0f}%)" if total > 0 else "0/0"
        
        print("{:<8} {:<8} {:<8} {:<20} {:<20} {:<12} {:<12}".format(
            sport, season or 'N/A', total, stats_pct, odds_pct, first or 'N/A', last or 'N/A'
        ))
    
    # Summary by sport
    cursor.execute("""
        SELECT 
            sport,
            COUNT(*) as total_games,
            SUM(has_player_stats) as with_stats,
            SUM(CASE WHEN has_odds > 0 THEN 1 ELSE 0 END) as with_odds
        FROM games
        GROUP BY sport
    """)
    
    sport_summary = cursor.fetchall()
    
    print("\n" + "="*80)
    print("📈 SUMMARY BY SPORT")
    print("="*80)
    
    print("\n{:<8} {:<12} {:<20} {:<20} {:<20}".format(
        'Sport', 'Total', 'Stats', 'Odds', 'Complete'
    ))
    print("-" * 90)
    
    for row in sport_summary:
        sport, total, stats, odds = row
        complete = min(stats, odds) if total > 0 else 0
        complete_pct = f"{complete}/{total} ({complete*100/total:.0f}%)" if total > 0 else "0/0"
        
        print("{:<8} {:<12} {:<20} {:<20} {:<20}".format(
            sport,
            total,
            f"{stats} ({stats*100/total:.0f}%)" if total > 0 else "0",
            f"{odds} ({odds*100/total:.0f}%)" if total > 0 else "0",
            complete_pct
        ))
    
    # Check odds_history table
    cursor.execute("SELECT COUNT(*) FROM odds_history")
    odds_count = cursor.fetchone()[0]
    
    # Check player_props table
    cursor.execute("SELECT COUNT(*) FROM player_props")
    props_count = cursor.fetchone()[0]
    
    print("\n" + "="*80)
    print("📋 ADDITIONAL DATA")
    print("="*80)
    print(f"  • Odds History Records: {odds_count}")
    print(f"  • Player Props Records: {props_count}")
    print()
    
    conn.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Check data collection status')
    parser.add_argument('--db', default='data/sports_data.db', help='Database path')
    
    args = parser.parse_args()
    
    try:
        check_status(args.db)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
