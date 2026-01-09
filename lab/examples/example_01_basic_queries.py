#!/usr/bin/env python3
"""
Database Integration Example 1: Basic Queries
==============================================

This example demonstrates how to connect to and query the SQLite database
that stores historical sports data.

Prerequisites:
    - Run data collection first:
      python scripts/collect_historical_sqlite.py --sports NBA --start-year 2023 --end-year 2024

What You'll Learn:
    1. How to connect to the SQLite database
    2. How to query games by sport and date
    3. How to access game statistics
    4. How to work with betting lines data
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db_manager import DatabaseManager
from datetime import datetime, timedelta


def main():
    print("=" * 80)
    print("Database Integration Example 1: Basic Queries")
    print("=" * 80)
    print()

    # Step 1: Connect to the database
    print("Step 1: Connecting to database...")
    db = DatabaseManager("data/sports_data.db")
    print("✓ Connected to data/sports_data.db")
    print()

    # Step 2: Count total games
    print("Step 2: Getting database statistics...")
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM games")
    total_games = cursor.fetchone()[0]
    print(f"Total games in database: {total_games:,}")

    # Count by sport
    cursor.execute("""
        SELECT sport, COUNT(*) as count 
        FROM games 
        GROUP BY sport 
        ORDER BY count DESC
    """)
    print("\nGames by sport:")
    for row in cursor.fetchall():
        print(f"  {row['sport']:10s}: {row['count']:,} games")
    print()

    # Step 3: Query recent NBA games
    print("Step 3: Querying recent NBA games...")
    cursor.execute("""
        SELECT game_id, date, home_team, away_team, home_score, away_score
        FROM games
        WHERE sport = 'NBA'
        ORDER BY date DESC
        LIMIT 5
    """)

    print("\nMost recent NBA games:")
    print(f"{'Date':<12} {'Home Team':<25} {'Away Team':<25} {'Score':<10}")
    print("-" * 80)
    for row in cursor.fetchall():
        score = f"{row['home_score']}-{row['away_score']}" if row['home_score'] else "TBD"
        print(
            f"{row['date']:<12} {row['home_team']:<25} {row['away_team']:<25} {score:<10}"
        )
    print()

    # Step 4: Query games with betting lines
    print("Step 4: Querying games with betting lines...")
    cursor.execute("""
        SELECT game_id, date, home_team, away_team, 
               moneyline_home, moneyline_away, 
               spread_line, total_line
        FROM games
        WHERE sport = 'NBA' 
          AND moneyline_home IS NOT NULL
        ORDER BY date DESC
        LIMIT 5
    """)

    print("\nNBA games with betting lines:")
    print(
        f"{'Date':<12} {'Home Team':<20} {'ML':<8} {'Away Team':<20} {'ML':<8} {'Spread':<8} {'Total':<8}"
    )
    print("-" * 100)
    for row in cursor.fetchall():
        ml_home = row["moneyline_home"] if row["moneyline_home"] else "N/A"
        ml_away = row["moneyline_away"] if row["moneyline_away"] else "N/A"
        spread = f"{row['spread_line']:.1f}" if row["spread_line"] else "N/A"
        total = f"{row['total_line']:.1f}" if row["total_line"] else "N/A"
        print(
            f"{row['date']:<12} {row['home_team']:<20} {str(ml_home):<8} "
            f"{row['away_team']:<20} {str(ml_away):<8} {spread:<8} {total:<8}"
        )
    print()

    # Step 5: Query a specific team's games
    print("Step 5: Querying specific team (Los Angeles Lakers)...")
    cursor.execute(
        """
        SELECT date, home_team, away_team, home_score, away_score
        FROM games
        WHERE sport = 'NBA'
          AND (home_team LIKE '%Lakers%' OR away_team LIKE '%Lakers%')
        ORDER BY date DESC
        LIMIT 10
    """,
    )

    print("\nLos Angeles Lakers recent games:")
    print(f"{'Date':<12} {'Home':<25} {'Away':<25} {'Score':<10}")
    print("-" * 80)
    for row in cursor.fetchall():
        score = f"{row['home_score']}-{row['away_score']}" if row['home_score'] else "TBD"
        print(
            f"{row['date']:<12} {row['home_team']:<25} {row['away_team']:<25} {score:<10}"
        )
    print()

    # Step 6: Query games by date range
    print("Step 6: Querying games in a specific date range...")
    start_date = "2024-01-01"
    end_date = "2024-01-07"

    cursor.execute(
        """
        SELECT COUNT(*) as count
        FROM games
        WHERE sport = 'NBA'
          AND date BETWEEN ? AND ?
    """,
        (start_date, end_date),
    )
    count = cursor.fetchone()["count"]
    print(f"\nNBA games between {start_date} and {end_date}: {count}")
    print()

    # Step 7: Advanced query - Games with high totals
    print("Step 7: Advanced query - High-scoring games...")
    cursor.execute("""
        SELECT date, home_team, away_team, home_score, away_score,
               (home_score + away_score) as total_points
        FROM games
        WHERE sport = 'NBA'
          AND home_score IS NOT NULL
          AND away_score IS NOT NULL
        ORDER BY total_points DESC
        LIMIT 5
    """)

    print("\nHighest-scoring NBA games:")
    print(f"{'Date':<12} {'Home Team':<25} {'Away Team':<25} {'Total Points':<15}")
    print("-" * 85)
    for row in cursor.fetchall():
        print(
            f"{row['date']:<12} {row['home_team']:<25} {row['away_team']:<25} "
            f"{row['total_points']:<15} ({row['home_score']}-{row['away_score']})"
        )
    print()

    print("=" * 80)
    print("Example completed successfully!")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  - Try modifying the queries to explore different data")
    print("  - See example_02_player_props.py for player statistics")
    print("  - See example_03_backtesting.py for strategy testing")
    print()


if __name__ == "__main__":
    main()
