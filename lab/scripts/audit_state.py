#!/usr/bin/env python3
"""
Data Architecture Audit Script

Inspects sports_data.db and generates a comprehensive status report including:
- Row counts for all tables
- Data quality metrics (enrichment completeness)
- Missing data identification

Usage:
    python scripts/audit_state.py
    python scripts/audit_state.py --verbose
"""

import os
import sys
import sqlite3
import json
from datetime import datetime
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class DatabaseAuditor:
    """Audit sports_data.db for completeness and data quality."""
    
    def __init__(self, db_path: str = "data/sports_data.db"):
        """
        Initialize auditor.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database not found: {db_path}")
        
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        
    def get_table_count(self, table: str) -> int:
        """Get row count for a table."""
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        return cursor.fetchone()[0]
    
    def get_table_exists(self, table: str) -> bool:
        """Check if table exists."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table,))
        return cursor.fetchone() is not None
    
    def audit_games_table(self) -> Dict[str, Any]:
        """Audit games table for data quality."""
        cursor = self.conn.cursor()
        
        results = {
            'total_games': 0,
            'completed_games': 0,
            'with_scores': 0,
            'with_player_stats': 0,
            'player_stats_percentage': 0.0,
            'with_odds': 0,
            'odds_percentage': 0.0,
            'with_perplexity': 0,
            'by_sport': {},
            'by_season': {},
            'missing_scores': 0,
            'missing_player_stats_ids': []
        }
        
        # Total counts
        results['total_games'] = self.get_table_count('games')
        
        # Games by status
        cursor.execute("SELECT COUNT(*) FROM games WHERE status = 'Final'")
        results['completed_games'] = cursor.fetchone()[0]
        
        # Games with scores
        cursor.execute("""
            SELECT COUNT(*) FROM games 
            WHERE home_score IS NOT NULL AND away_score IS NOT NULL
        """)
        results['with_scores'] = cursor.fetchone()[0]
        
        # Games with player stats (flag or JSON populated)
        cursor.execute("""
            SELECT COUNT(*) FROM games 
            WHERE has_player_stats = 1 
            OR (player_stats IS NOT NULL AND player_stats != '' AND player_stats != '[]')
        """)
        results['with_player_stats'] = cursor.fetchone()[0]
        
        if results['completed_games'] > 0:
            results['player_stats_percentage'] = (
                results['with_player_stats'] / results['completed_games'] * 100
            )
        
        # Games with odds
        cursor.execute("SELECT COUNT(*) FROM games WHERE has_odds = 1")
        results['with_odds'] = cursor.fetchone()[0]
        
        if results['total_games'] > 0:
            results['odds_percentage'] = results['with_odds'] / results['total_games'] * 100
        
        # Games with perplexity enrichment
        cursor.execute("SELECT COUNT(*) FROM games WHERE has_perplexity = 1")
        results['with_perplexity'] = cursor.fetchone()[0]
        
        # Breakdown by sport
        cursor.execute("""
            SELECT sport, COUNT(*) as count
            FROM games
            GROUP BY sport
            ORDER BY count DESC
        """)
        for row in cursor.fetchall():
            results['by_sport'][row[0]] = row[1]
        
        # Breakdown by season
        cursor.execute("""
            SELECT sport, season, COUNT(*) as count
            FROM games
            WHERE season IS NOT NULL
            GROUP BY sport, season
            ORDER BY sport, season DESC
        """)
        for row in cursor.fetchall():
            key = f"{row[0]}_{row[1]}"
            results['by_season'][key] = row[2]
        
        # Missing scores (completed games)
        cursor.execute("""
            SELECT COUNT(*) FROM games 
            WHERE status = 'Final' 
            AND (home_score IS NULL OR away_score IS NULL)
        """)
        results['missing_scores'] = cursor.fetchone()[0]
        
        # Sample of games missing player stats (limit to 10)
        cursor.execute("""
            SELECT game_id, date, home_team, away_team
            FROM games
            WHERE status = 'Final'
            AND (has_player_stats = 0 OR has_player_stats IS NULL)
            AND (player_stats IS NULL OR player_stats = '' OR player_stats = '[]')
            ORDER BY date DESC
            LIMIT 10
        """)
        results['missing_player_stats_ids'] = [
            {
                'game_id': row[0],
                'date': row[1],
                'matchup': f"{row[2]} vs {row[3]}"
            }
            for row in cursor.fetchall()
        ]
        
        return results
    
    def audit_odds_table(self) -> Dict[str, Any]:
        """Audit odds_history table."""
        if not self.get_table_exists('odds_history'):
            return {'exists': False}
        
        cursor = self.conn.cursor()
        
        results = {
            'exists': True,
            'total_odds': self.get_table_count('odds_history'),
            'by_bookmaker': {},
            'by_market_type': {},
            'date_range': {}
        }
        
        # Odds by bookmaker
        cursor.execute("""
            SELECT bookmaker, COUNT(*) as count
            FROM odds_history
            GROUP BY bookmaker
            ORDER BY count DESC
            LIMIT 10
        """)
        for row in cursor.fetchall():
            results['by_bookmaker'][row[0]] = row[1]
        
        # Odds by market type
        cursor.execute("""
            SELECT market_type, COUNT(*) as count
            FROM odds_history
            GROUP BY market_type
            ORDER BY count DESC
        """)
        for row in cursor.fetchall():
            results['by_market_type'][row[0]] = row[1]
        
        # Date range
        cursor.execute("""
            SELECT MIN(timestamp), MAX(timestamp)
            FROM odds_history
        """)
        row = cursor.fetchone()
        if row[0] and row[1]:
            results['date_range'] = {
                'earliest': row[0],
                'latest': row[1]
            }
        
        # Games with associated odds
        cursor.execute("""
            SELECT COUNT(DISTINCT game_id) 
            FROM odds_history
        """)
        results['unique_games_with_odds'] = cursor.fetchone()[0]
        
        return results
    
    def audit_props_table(self) -> Dict[str, Any]:
        """Audit player_props table."""
        if not self.get_table_exists('player_props'):
            return {'exists': False}
        
        cursor = self.conn.cursor()
        
        results = {
            'exists': True,
            'total_props': self.get_table_count('player_props'),
            'by_prop_type': {},
            'with_actual_values': 0
        }
        
        # Props by type
        cursor.execute("""
            SELECT prop_type, COUNT(*) as count
            FROM player_props
            GROUP BY prop_type
            ORDER BY count DESC
        """)
        for row in cursor.fetchall():
            results['by_prop_type'][row[0]] = row[1]
        
        # Props with actual values (for validation)
        cursor.execute("""
            SELECT COUNT(*) FROM player_props
            WHERE actual_value IS NOT NULL
        """)
        results['with_actual_values'] = cursor.fetchone()[0]
        
        return results
    
    def audit_perplexity_cache(self) -> Dict[str, Any]:
        """Audit perplexity_cache table."""
        if not self.get_table_exists('perplexity_cache'):
            return {'exists': False}
        
        cursor = self.conn.cursor()
        
        results = {
            'exists': True,
            'total_entries': self.get_table_count('perplexity_cache'),
            'expired': 0,
            'valid': 0
        }
        
        # Check for expired entries (timestamp + ttl < now)
        cursor.execute("""
            SELECT COUNT(*) FROM perplexity_cache
            WHERE timestamp + ttl < ?
        """, (int(datetime.now().timestamp()),))
        results['expired'] = cursor.fetchone()[0]
        
        results['valid'] = results['total_entries'] - results['expired']
        
        return results
    
    def print_report(self, verbose: bool = False):
        """Print comprehensive audit report."""
        print("=" * 80)
        print("📊 OMEGASPORTS DATABASE AUDIT REPORT")
        print("=" * 80)
        print(f"Database: {self.db_path}")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # File size
        file_size_mb = os.path.getsize(self.db_path) / (1024 * 1024)
        print(f"💾 Database Size: {file_size_mb:.2f} MB")
        print()
        
        # ============================================================
        # GAMES TABLE
        # ============================================================
        print("=" * 80)
        print("🏀 GAMES TABLE")
        print("=" * 80)
        
        games_audit = self.audit_games_table()
        
        print(f"Total Games:      {games_audit['total_games']:,}")
        print(f"Completed Games:  {games_audit['completed_games']:,}")
        print(f"With Scores:      {games_audit['with_scores']:,}")
        print()
        
        print("📈 ENRICHMENT STATUS")
        print("-" * 80)
        print(f"Player Stats:     {games_audit['with_player_stats']:,} / {games_audit['completed_games']:,} "
              f"({games_audit['player_stats_percentage']:.1f}%)")
        print(f"Odds Data:        {games_audit['with_odds']:,} / {games_audit['total_games']:,} "
              f"({games_audit['odds_percentage']:.1f}%)")
        print(f"Perplexity Cache: {games_audit['with_perplexity']:,}")
        print()
        
        # Quality warnings
        if games_audit['missing_scores'] > 0:
            print(f"⚠️  WARNING: {games_audit['missing_scores']} completed games missing scores!")
            print()
        
        if games_audit['player_stats_percentage'] < 100:
            missing_count = games_audit['completed_games'] - games_audit['with_player_stats']
            print(f"⚠️  WARNING: {missing_count:,} completed games missing player stats!")
            
            if games_audit['missing_player_stats_ids'] and verbose:
                print("\n   Sample of games missing player stats:")
                for game in games_audit['missing_player_stats_ids'][:5]:
                    print(f"   - {game['game_id']} ({game['date']}): {game['matchup']}")
            print()
        
        # Breakdown by sport
        if games_audit['by_sport']:
            print("📊 BY SPORT")
            print("-" * 80)
            for sport, count in sorted(games_audit['by_sport'].items(), key=lambda x: -x[1]):
                print(f"{sport:15s} {count:,}")
            print()
        
        # Breakdown by season
        if games_audit['by_season'] and verbose:
            print("📅 BY SEASON")
            print("-" * 80)
            for key, count in sorted(games_audit['by_season'].items()):
                print(f"{key:20s} {count:,}")
            print()
        
        # ============================================================
        # ODDS HISTORY TABLE
        # ============================================================
        print("=" * 80)
        print("💰 ODDS HISTORY TABLE")
        print("=" * 80)
        
        odds_audit = self.audit_odds_table()
        
        if not odds_audit['exists']:
            print("⚠️  Table does not exist")
        else:
            print(f"Total Odds Records: {odds_audit['total_odds']:,}")
            print(f"Unique Games:       {odds_audit.get('unique_games_with_odds', 0):,}")
            print()
            
            if odds_audit['by_market_type']:
                print("📊 BY MARKET TYPE")
                print("-" * 80)
                for market_type, count in sorted(odds_audit['by_market_type'].items(), key=lambda x: -x[1]):
                    print(f"{market_type:15s} {count:,}")
                print()
            
            if odds_audit['by_bookmaker'] and verbose:
                print("🏦 TOP BOOKMAKERS")
                print("-" * 80)
                for bookmaker, count in list(odds_audit['by_bookmaker'].items())[:5]:
                    print(f"{bookmaker:25s} {count:,}")
                print()
            
            if odds_audit.get('date_range'):
                print("📅 DATE RANGE")
                print("-" * 80)
                print(f"Earliest: {odds_audit['date_range']['earliest']}")
                print(f"Latest:   {odds_audit['date_range']['latest']}")
                print()
        
        # ============================================================
        # PLAYER PROPS TABLE
        # ============================================================
        print("=" * 80)
        print("🎯 PLAYER PROPS TABLE")
        print("=" * 80)
        
        props_audit = self.audit_props_table()
        
        if not props_audit['exists']:
            print("⚠️  Table does not exist")
        else:
            print(f"Total Props:        {props_audit['total_props']:,}")
            print(f"With Actual Values: {props_audit['with_actual_values']:,}")
            print()
            
            if props_audit['by_prop_type']:
                print("📊 BY PROP TYPE")
                print("-" * 80)
                for prop_type, count in sorted(props_audit['by_prop_type'].items(), key=lambda x: -x[1]):
                    print(f"{prop_type:20s} {count:,}")
                print()
        
        # ============================================================
        # PERPLEXITY CACHE TABLE
        # ============================================================
        print("=" * 80)
        print("🧠 PERPLEXITY CACHE TABLE")
        print("=" * 80)
        
        perp_audit = self.audit_perplexity_cache()
        
        if not perp_audit['exists']:
            print("⚠️  Table does not exist")
        else:
            print(f"Total Entries:  {perp_audit['total_entries']:,}")
            print(f"Valid Entries:  {perp_audit['valid']:,}")
            print(f"Expired:        {perp_audit['expired']:,}")
            print()
        
        # ============================================================
        # SUMMARY & RECOMMENDATIONS
        # ============================================================
        print("=" * 80)
        print("📋 SUMMARY & RECOMMENDATIONS")
        print("=" * 80)
        
        recommendations = []
        
        # Check if migration needed
        if games_audit['total_games'] == 0:
            recommendations.append("❌ CRITICAL: No games in database - run finalize_migration.py")
        elif games_audit['total_games'] < 1000:
            recommendations.append("⚠️  Low game count - consider running finalize_migration.py")
        
        # Check player stats enrichment
        if games_audit['player_stats_percentage'] < 100:
            missing = games_audit['completed_games'] - games_audit['with_player_stats']
            recommendations.append(
                f"⚠️  {missing:,} games missing player stats - run enrich_stats.py"
            )
        else:
            recommendations.append("✅ All completed games have player stats")
        
        # Check odds data
        if not odds_audit['exists'] or odds_audit['total_odds'] == 0:
            recommendations.append("⚠️  No odds history - run finalize_migration.py to import odds_cache/")
        else:
            recommendations.append(f"✅ Odds history populated ({odds_audit['total_odds']:,} records)")
        
        # Check props
        if not props_audit['exists'] or props_audit['total_props'] == 0:
            recommendations.append("ℹ️  Player props table empty - add if needed for prop betting analysis")
        
        # Check perplexity cache
        if perp_audit['exists'] and perp_audit['expired'] > 100:
            recommendations.append(f"ℹ️  {perp_audit['expired']:,} expired cache entries - consider cleanup")
        
        if not recommendations:
            recommendations.append("✅ Database in good shape - no immediate actions needed")
        
        for rec in recommendations:
            print(rec)
        
        print()
        print("=" * 80)
        print("✅ Audit Complete")
        print("=" * 80)
    
    def close(self):
        """Close database connection."""
        self.conn.close()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Audit sports_data.db")
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed breakdowns'
    )
    parser.add_argument(
        '--db-path',
        default='data/sports_data.db',
        help='Path to database (default: data/sports_data.db)'
    )
    
    args = parser.parse_args()
    
    try:
        auditor = DatabaseAuditor(db_path=args.db_path)
        auditor.print_report(verbose=args.verbose)
        auditor.close()
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
