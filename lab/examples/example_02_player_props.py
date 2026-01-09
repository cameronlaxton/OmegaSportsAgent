#!/usr/bin/env python3
"""
Database Integration Example 2: Player Props and Statistics
===========================================================

This example demonstrates how to work with player props and statistics
stored in the database.

Prerequisites:
    - Run data collection with player props:
      python scripts/collect_historical_sqlite.py --sports NBA --start-year 2023 --end-year 2024

What You'll Learn:
    1. How to query player props
    2. How to analyze player performance
    3. How to calculate prop hit rates
    4. How to identify valuable prop bets
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db_manager import DatabaseManager
from collections import defaultdict


def main():
    print("=" * 80)
    print("Database Integration Example 2: Player Props and Statistics")
    print("=" * 80)
    print()

    # Step 1: Connect to the database
    print("Step 1: Connecting to database...")
    db = DatabaseManager("data/sports_data.db")
    conn = db.get_connection()
    cursor = conn.cursor()
    print("✓ Connected to data/sports_data.db")
    print()

    # Step 2: Count player props
    print("Step 2: Getting player props statistics...")
    cursor.execute("SELECT COUNT(*) FROM player_props")
    total_props = cursor.fetchone()[0]
    print(f"Total player props in database: {total_props:,}")

    if total_props == 0:
        print()
        print("=" * 80)
        print("NOTE: No player props data found in database.")
        print("=" * 80)
        print()
        print("To collect player props data, run:")
        print("  python scripts/collect_historical_sqlite.py \\")
        print("      --sports NBA --start-year 2023 --end-year 2024")
        print()
        print("This example requires player props data to demonstrate:")
        print("  - Player prop analysis")
        print("  - Hit rate calculations")
        print("  - Performance trends")
        print()
        print("For now, this example will exit. Run data collection first.")
        print("=" * 80)
        return

    # Count by prop type
    cursor.execute("""
        SELECT prop_type, COUNT(*) as count 
        FROM player_props 
        GROUP BY prop_type 
        ORDER BY count DESC
    """)
    print("\nProps by type:")
    for row in cursor.fetchall():
        print(f"  {row['prop_type']:15s}: {row['count']:,} props")
    print()

    # Step 3: Query player props for a specific player
    print("Step 3: Querying props for a specific player...")
    player_name = "LeBron James"  # Change this to any player
    
    cursor.execute("""
        SELECT date, player_team, opponent_team, prop_type, 
               over_line, actual_value
        FROM player_props
        WHERE player_name = ?
        ORDER BY date DESC
        LIMIT 10
    """, (player_name,))

    print(f"\nRecent props for {player_name}:")
    print(f"{'Date':<12} {'Team':<10} {'Opponent':<10} {'Prop Type':<15} {'Line':<8} {'Actual':<8}")
    print("-" * 80)
    for row in cursor.fetchall():
        actual = f"{row['actual_value']}" if row['actual_value'] is not None else "N/A"
        line = f"{row['over_line']:.1f}" if row['over_line'] is not None else "N/A"
        print(
            f"{row['date']:<12} {row['player_team']:<10} {row['opponent_team']:<10} "
            f"{row['prop_type']:<15} {line:<8} {actual:<8}"
        )
    print()

    # Step 4: Calculate hit rate for a player's props
    print("Step 4: Calculating prop hit rates...")
    
    cursor.execute("""
        SELECT prop_type, 
               COUNT(*) as total,
               SUM(CASE WHEN actual_value > over_line THEN 1 ELSE 0 END) as overs,
               SUM(CASE WHEN actual_value < over_line THEN 1 ELSE 0 END) as unders,
               AVG(actual_value) as avg_actual,
               AVG(over_line) as avg_line
        FROM player_props
        WHERE player_name = ?
          AND actual_value IS NOT NULL
        GROUP BY prop_type
    """, (player_name,))

    print(f"\nHit rates for {player_name}:")
    print(f"{'Prop Type':<15} {'Total':<8} {'Over %':<10} {'Under %':<10} {'Avg Actual':<12} {'Avg Line':<12}")
    print("-" * 80)
    for row in cursor.fetchall():
        total = row['total']
        over_pct = (row['overs'] / total * 100) if total > 0 else 0
        under_pct = (row['unders'] / total * 100) if total > 0 else 0
        print(
            f"{row['prop_type']:<15} {total:<8} {over_pct:<10.1f} {under_pct:<10.1f} "
            f"{row['avg_actual']:<12.1f} {row['avg_line']:<12.1f}"
        )
    print()

    # Step 5: Find best performing players on a specific prop type
    print("Step 5: Finding top performers for a specific prop type...")
    prop_type = "points"  # Change to rebounds, assists, etc.
    
    cursor.execute("""
        SELECT player_name, 
               COUNT(*) as games,
               AVG(actual_value) as avg_value,
               MAX(actual_value) as max_value
        FROM player_props
        WHERE prop_type = ?
          AND actual_value IS NOT NULL
        GROUP BY player_name
        HAVING games >= 10
        ORDER BY avg_value DESC
        LIMIT 10
    """, (prop_type,))

    print(f"\nTop {prop_type} performers (min 10 games):")
    print(f"{'Player':<30} {'Games':<8} {'Avg':<10} {'Max':<10}")
    print("-" * 60)
    for row in cursor.fetchall():
        print(
            f"{row['player_name']:<30} {row['games']:<8} "
            f"{row['avg_value']:<10.1f} {row['max_value']:<10.0f}"
        )
    print()

    # Step 6: Analyze prop accuracy by type
    print("Step 6: Analyzing prop line accuracy...")
    
    cursor.execute("""
        SELECT prop_type,
               COUNT(*) as total_props,
               AVG(ABS(actual_value - over_line)) as avg_error,
               AVG((actual_value - over_line)) as avg_bias
        FROM player_props
        WHERE actual_value IS NOT NULL
        GROUP BY prop_type
        ORDER BY total_props DESC
    """)

    print("\nProp line accuracy analysis:")
    print(f"{'Prop Type':<15} {'Count':<10} {'Avg Error':<12} {'Avg Bias':<12}")
    print("-" * 55)
    for row in cursor.fetchall():
        bias_direction = "Over" if row['avg_bias'] > 0 else "Under"
        print(
            f"{row['prop_type']:<15} {row['total_props']:<10} "
            f"{row['avg_error']:<12.2f} {row['avg_bias']:<12.2f}"
        )
    print()

    # Step 7: Find games with multiple props available
    print("Step 7: Finding games with multiple player props...")
    
    cursor.execute("""
        SELECT g.date, g.home_team, g.away_team, COUNT(pp.prop_id) as prop_count
        FROM games g
        JOIN player_props pp ON g.game_id = pp.game_id
        WHERE g.sport = 'NBA'
        GROUP BY g.game_id
        ORDER BY prop_count DESC
        LIMIT 10
    """)

    print("\nGames with most player props:")
    print(f"{'Date':<12} {'Home Team':<25} {'Away Team':<25} {'Props':<8}")
    print("-" * 75)
    for row in cursor.fetchall():
        print(
            f"{row['date']:<12} {row['home_team']:<25} {row['away_team']:<25} {row['prop_count']:<8}"
        )
    print()

    print("=" * 80)
    print("Example completed successfully!")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  - Try analyzing different players or prop types")
    print("  - See example_03_backtesting.py for strategy testing")
    print("  - Build your own prop analysis queries")
    print()


if __name__ == "__main__":
    main()
