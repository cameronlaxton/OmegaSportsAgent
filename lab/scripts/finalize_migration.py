#!/usr/bin/env python3
"""
Grand Unification Migration Script

Consolidates all legacy data sources into sports_data.db:
1. Perplexity cache (perplexity.db) -> perplexity_cache table
2. Game results (data/historical/*.json) -> games table (with player_stats JSON)
3. Odds data (data/odds_cache/**/*.json) -> odds_history + player_props tables

Usage:
    python scripts/finalize_migration.py [--dry-run] [--skip-perplexity] [--skip-games] [--skip-odds]
"""

import os
import sys
import json
import glob
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.db_manager import DatabaseManager


class GrandUnificationMigrator:
    """Migrates all legacy data into unified sports_data.db."""
    
    def __init__(self, db_path: str = "data/sports_data.db", dry_run: bool = False):
        """
        Initialize migrator.
        
        Args:
            db_path: Path to target SQLite database
            dry_run: If True, simulate without writing
        """
        self.db_path = db_path
        self.db_manager = DatabaseManager(db_path)
        self.dry_run = dry_run
        
        self.stats = {
            'games_inserted': 0,
            'games_updated': 0,
            'games_skipped': 0,
            'odds_inserted': 0,
            'props_inserted': 0,
            'perplexity_inserted': 0,
            'errors': []
        }
        
        print("=" * 80)
        print("🚀 GRAND UNIFICATION MIGRATION")
        print("=" * 80)
        print(f"Target Database: {db_path}")
        print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will modify database)'}")
        print()
    
    def migrate_perplexity_cache(self, source_db: str = "data/cache/perplexity.db") -> int:
        """
        Migrate perplexity.db cache into unified database.
        
        Args:
            source_db: Path to legacy perplexity.db
            
        Returns:
            Number of records migrated
        """
        if not os.path.exists(source_db):
            print(f"⚠️  Perplexity cache not found: {source_db}")
            return 0
        
        print("=" * 80)
        print("🧠 MIGRATING PERPLEXITY CACHE")
        print("=" * 80)
        print(f"Source: {source_db}")
        print()
        
        try:
            # Connect to source database
            source_conn = sqlite3.connect(source_db)
            source_conn.row_factory = sqlite3.Row
            cursor = source_conn.cursor()
            
            # Check what tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"Found tables: {', '.join(tables)}")
            
            if 'perplexity_cache' in tables:
                table_name = 'perplexity_cache'
            elif 'cache' in tables:
                table_name = 'cache'
            else:
                print(f"⚠️  No recognized cache table found in {source_db}")
                source_conn.close()
                return 0
            
            # Get all cache entries
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            print(f"Found {len(rows)} cache entries")
            
            if self.dry_run:
                print(f"[DRY RUN] Would migrate {len(rows)} entries")
                source_conn.close()
                return len(rows)
            
            # Get target connection
            target_conn = self.db_manager.get_connection()
            target_cursor = target_conn.cursor()
            
            # Migrate each entry (avoid duplicates)
            migrated = 0
            for row in rows:
                row_dict = dict(row)
                
                # Check if already exists
                target_cursor.execute(
                    "SELECT 1 FROM perplexity_cache WHERE prompt_hash = ?",
                    (row_dict.get('prompt_hash'),)
                )
                
                if target_cursor.fetchone():
                    print(f"  Skipping duplicate: {row_dict.get('prompt_hash', 'unknown')[:20]}...")
                    continue
                
                # Insert into target
                target_cursor.execute("""
                    INSERT OR IGNORE INTO perplexity_cache
                    (query_hash, player_name, game_date, prop_type, response_json, timestamp, ttl)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    row_dict.get('query_hash') or row_dict.get('prompt_hash'),
                    row_dict.get('player_name'),
                    row_dict.get('game_date'),
                    row_dict.get('prop_type'),
                    row_dict.get('response_json') or row_dict.get('response'),
                    row_dict.get('timestamp') or row_dict.get('created_at'),
                    row_dict.get('ttl', 2592000)  # Default 30 days
                ))
                
                migrated += 1
            
            target_conn.commit()
            source_conn.close()
            
            self.stats['perplexity_inserted'] = migrated
            print(f"✅ Migrated {migrated} perplexity cache entries")
            print()
            
            return migrated
            
        except sqlite3.Error as e:
            error_msg = f"SQLite error migrating perplexity cache: {e}"
            print(f"❌ {error_msg}")
            self.stats['errors'].append(error_msg)
            return 0
        except Exception as e:
            error_msg = f"Error migrating perplexity cache: {e}"
            print(f"❌ {error_msg}")
            self.stats['errors'].append(error_msg)
            return 0
    
    def migrate_games_from_json(self, json_files: Optional[List[str]] = None) -> int:
        """
        Migrate game results from historical JSON files.
        
        CRITICAL: Preserves player_stats JSON blob from source files.
        
        Args:
            json_files: List of JSON file paths (default: data/historical/nba_*.json)
            
        Returns:
            Number of games migrated
        """
        if json_files is None:
            json_files = glob.glob("data/historical/nba_*.json")
        
        if not json_files:
            print("⚠️  No historical JSON files found in data/historical/")
            return 0
        
        print("=" * 80)
        print("🏀 MIGRATING GAME RESULTS FROM JSON")
        print("=" * 80)
        print(f"Found {len(json_files)} files:")
        for f in json_files:
            print(f"  - {f}")
        print()
        
        total_inserted = 0
        total_updated = 0
        total_skipped = 0
        
        for json_file in json_files:
            print(f"Processing: {json_file}")
            
            try:
                with open(json_file, 'r') as f:
                    games = json.load(f)
                
                if not isinstance(games, list):
                    print(f"  ⚠️  Expected list, got {type(games)}")
                    continue
                
                print(f"  Found {len(games)} games")
                
                for i, game in enumerate(games):
                    if self.dry_run and i < 3:
                        print(f"  [DRY RUN] Would process game: {game.get('game_id', 'unknown')}")
                        continue
                    
                    try:
                        # Insert or update game
                        result = self._upsert_game(game)
                        
                        if result == 'inserted':
                            total_inserted += 1
                        elif result == 'updated':
                            total_updated += 1
                        else:
                            total_skipped += 1
                        
                        # Progress indicator
                        if (i + 1) % 500 == 0:
                            print(f"  Progress: {i + 1}/{len(games)} games processed")
                    
                    except Exception as e:
                        error_msg = f"Error processing game {game.get('game_id', 'unknown')}: {e}"
                        print(f"  ⚠️  {error_msg}")
                        self.stats['errors'].append(error_msg)
                
                print(f"  ✅ Completed: {json_file}")
                print()
                
            except json.JSONDecodeError as e:
                error_msg = f"JSON parse error in {json_file}: {e}"
                print(f"  ❌ {error_msg}")
                self.stats['errors'].append(error_msg)
            except Exception as e:
                error_msg = f"Error processing {json_file}: {e}"
                print(f"  ❌ {error_msg}")
                self.stats['errors'].append(error_msg)
        
        self.stats['games_inserted'] = total_inserted
        self.stats['games_updated'] = total_updated
        self.stats['games_skipped'] = total_skipped
        
        print(f"✅ Games Migration Complete:")
        print(f"   Inserted: {total_inserted:,}")
        print(f"   Updated:  {total_updated:,}")
        print(f"   Skipped:  {total_skipped:,}")
        print()
        
        return total_inserted + total_updated
    
    def _upsert_game(self, game: Dict[str, Any]) -> str:
        """
        Insert or update a game record.
        
        Args:
            game: Game data dictionary
            
        Returns:
            'inserted', 'updated', or 'skipped'
        """
        if self.dry_run:
            return 'skipped'
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        game_id = game.get('game_id')
        if not game_id:
            return 'skipped'
        
        # Check if game exists
        cursor.execute("SELECT game_id FROM games WHERE game_id = ?", (game_id,))
        exists = cursor.fetchone()
        
        # Extract and serialize player_stats if present
        player_stats_json = None
        if 'player_stats' in game and game['player_stats']:
            if isinstance(game['player_stats'], (list, dict)):
                player_stats_json = json.dumps(game['player_stats'])
            elif isinstance(game['player_stats'], str):
                player_stats_json = game['player_stats']
        
        # Determine has_player_stats flag
        has_player_stats = 1 if player_stats_json and player_stats_json not in ('', '[]', '{}') else 0
        
        # Extract moneyline (handle different formats)
        moneyline = game.get('moneyline', {})
        if moneyline is None:
            moneyline = {}
        moneyline_home = moneyline.get('home')
        moneyline_away = moneyline.get('away')
        
        # Extract spread
        spread = game.get('spread', {})
        if spread is None:
            spread = {}
        spread_line = spread.get('line')
        spread_home_odds = spread.get('home_odds')
        spread_away_odds = spread.get('away_odds')
        
        # Extract total
        total = game.get('total', {})
        if total is None:
            total = {}
        total_line = total.get('line')
        total_over_odds = total.get('over_odds')
        total_under_odds = total.get('under_odds')
        
        # Determine has_odds flag
        has_odds = 1 if any([moneyline_home, spread_line, total_line]) else 0
        
        now = int(datetime.now().timestamp())
        
        if exists:
            # Update existing game (only if we have new data)
            cursor.execute("""
                UPDATE games
                SET date = ?,
                    sport = ?,
                    league = ?,
                    season = ?,
                    home_team = ?,
                    away_team = ?,
                    home_score = ?,
                    away_score = ?,
                    status = ?,
                    moneyline_home = COALESCE(?, moneyline_home),
                    moneyline_away = COALESCE(?, moneyline_away),
                    spread_line = COALESCE(?, spread_line),
                    spread_home_odds = COALESCE(?, spread_home_odds),
                    spread_away_odds = COALESCE(?, spread_away_odds),
                    total_line = COALESCE(?, total_line),
                    total_over_odds = COALESCE(?, total_over_odds),
                    total_under_odds = COALESCE(?, total_under_odds),
                    venue = COALESCE(?, venue),
                    player_stats = COALESCE(?, player_stats),
                    has_player_stats = CASE WHEN ? = 1 THEN 1 ELSE has_player_stats END,
                    has_odds = CASE WHEN ? = 1 THEN 1 ELSE has_odds END,
                    updated_at = ?
                WHERE game_id = ?
            """, (
                game.get('date'),
                game.get('sport', 'NBA'),
                game.get('league', 'NBA'),
                game.get('season'),
                game.get('home_team'),
                game.get('away_team'),
                game.get('home_score'),
                game.get('away_score'),
                game.get('status', 'Final'),
                moneyline_home,
                moneyline_away,
                spread_line,
                spread_home_odds,
                spread_away_odds,
                total_line,
                total_over_odds,
                total_under_odds,
                game.get('venue'),
                player_stats_json,
                has_player_stats,
                has_odds,
                now,
                game_id
            ))
            conn.commit()
            return 'updated'
        else:
            # Insert new game
            cursor.execute("""
                INSERT INTO games (
                    game_id, date, sport, league, season,
                    home_team, away_team, home_score, away_score, status,
                    moneyline_home, moneyline_away,
                    spread_line, spread_home_odds, spread_away_odds,
                    total_line, total_over_odds, total_under_odds,
                    venue, player_stats,
                    has_player_stats, has_odds,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                game_id,
                game.get('date'),
                game.get('sport', 'NBA'),
                game.get('league', 'NBA'),
                game.get('season'),
                game.get('home_team'),
                game.get('away_team'),
                game.get('home_score'),
                game.get('away_score'),
                game.get('status', 'Final'),
                moneyline_home,
                moneyline_away,
                spread_line,
                spread_home_odds,
                spread_away_odds,
                total_line,
                total_over_odds,
                total_under_odds,
                game.get('venue'),
                player_stats_json,
                has_player_stats,
                has_odds,
                now,
                now
            ))
            conn.commit()
            return 'inserted'
    
    def migrate_odds_cache(self, cache_dirs: Optional[List[str]] = None) -> int:
        """
        Migrate historical odds from odds_cache/ directories.
        
        Args:
            cache_dirs: List of cache directories (default: data/odds_cache/nba/)
            
        Returns:
            Number of odds records migrated
        """
        if cache_dirs is None:
            cache_dirs = glob.glob("data/odds_cache/nba/*/")
        
        if not cache_dirs:
            print("⚠️  No odds cache directories found")
            return 0
        
        print("=" * 80)
        print("💰 MIGRATING ODDS CACHE")
        print("=" * 80)
        print(f"Found {len(cache_dirs)} directories:")
        for d in sorted(cache_dirs):
            print(f"  - {d}")
        print()
        
        total_inserted = 0
        
        for cache_dir in sorted(cache_dirs):
            json_files = glob.glob(os.path.join(cache_dir, "*.json"))
            
            if not json_files:
                continue
            
            print(f"Processing: {cache_dir} ({len(json_files)} files)")
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r') as f:
                        odds_data = json.load(f)
                    
                    if not isinstance(odds_data, list):
                        odds_data = [odds_data]
                    
                    # Extract date from filename (format: YYYY-MM-DD.json)
                    filename = os.path.basename(json_file)
                    file_date = filename.replace('.json', '')
                    
                    for odds_entry in odds_data:
                        if self.dry_run:
                            continue
                        
                        inserted = self._insert_odds_entry(odds_entry, file_date)
                        if inserted:
                            total_inserted += 1
                
                except json.JSONDecodeError as e:
                    error_msg = f"JSON parse error in {json_file}: {e}"
                    print(f"  ⚠️  {error_msg}")
                    self.stats['errors'].append(error_msg)
                except Exception as e:
                    error_msg = f"Error processing {json_file}: {e}"
                    print(f"  ⚠️  {error_msg}")
                    self.stats['errors'].append(error_msg)
            
            print(f"  ✅ Completed: {cache_dir}")
        
        if self.dry_run:
            print(f"[DRY RUN] Would migrate odds from {len(cache_dirs)} directories")
        else:
            self.stats['odds_inserted'] = total_inserted
            print(f"\n✅ Odds Migration Complete: {total_inserted:,} records inserted")
        print()
        
        return total_inserted
    
    def _insert_odds_entry(self, odds: Dict[str, Any], file_date: str) -> bool:
        """
        Insert an odds entry into odds_history table.
        
        Args:
            odds: Odds data dictionary
            file_date: Date from filename
            
        Returns:
            True if inserted, False if skipped
        """
        if self.dry_run:
            return False
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            # Generate a pseudo game_id (match by teams + date)
            home_team = odds.get('home_team', '')
            away_team = odds.get('away_team', '')
            
            if not home_team or not away_team:
                return False
            
            # Try to find matching game in games table
            cursor.execute("""
                SELECT game_id FROM games
                WHERE date = ?
                AND (home_team = ? OR home_team LIKE ?)
                AND (away_team = ? OR away_team LIKE ?)
                LIMIT 1
            """, (file_date, home_team, f"%{home_team}%", away_team, f"%{away_team}%"))
            
            game_row = cursor.fetchone()
            game_id = game_row[0] if game_row else None
            
            if not game_id:
                # Create synthetic game_id for orphaned odds
                game_id = f"odds_{file_date}_{home_team.replace(' ', '_')}_{away_team.replace(' ', '_')}"
            
            # Insert for each bookmaker (if num_bookmakers provided)
            num_bookmakers = odds.get('num_bookmakers', 1)
                        bookmaker = f'aggregate_{num_bookmakers}'
            
            # Use commence_time or file_date for timestamp
            timestamp_str = odds.get('commence_time', f"{file_date}T12:00:00Z")
            
            
            # Convert to Unix timestamp if needed
            from datetime import datetime
            if 'T' in timestamp_str or 'Z' in timestamp_str:
                try:
                    dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    timestamp_int = int(dt.timestamp())
                except:
                    timestamp_int = int(datetime.now().timestamp())
            else:
                timestamp_int = int(datetime.now().timestamp())
            
            inserted_count = 0
            
            # Insert moneyline as separate row
            moneyline = odds.get('moneyline', {})
            if moneyline and (moneyline.get('home') or moneyline.get('away')):
                cursor.execute("""
                    INSERT OR IGNORE INTO odds_history (
                        game_id, bookmaker, market_type, timestamp,
                        home_odds, away_odds, line,
                        over_odds, under_odds, source
                    )
                    VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?)
                """, (
                    game_id, bookmaker, 'moneyline', timestamp_int,
                    moneyline.get('home'), moneyline.get('away'), 'oddsapi'
                ))
                inserted_count += 1
            
            # Insert spread as separate row
            spread = odds.get('spread', {})
            if spread and spread.get('line') is not None:
                cursor.execute("""
                    INSERT OR IGNORE INTO odds_history (
                        game_id, bookmaker, market_type, timestamp,
                        line, home_odds, away_odds,
                        over_odds, under_odds, source
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?)
                """, (
                    game_id, bookmaker, 'spread', timestamp_int,
                    spread.get('line'), spread.get('home_odds'), spread.get('away_odds'), 'oddsapi'
                ))
                inserted_count += 1
            
            # Insert total as separate row
            total = odds.get('total', {})
            if total and total.get('line') is not None:
                cursor.execute("""
                    INSERT OR IGNORE INTO odds_history (
                        game_id, bookmaker, market_type, timestamp,
                        line, home_odds, away_odds,
                        over_odds, under_odds, source
                    )
                    VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?)
                """, (
                    game_id, bookmaker, 'total', timestamp_int,
                    total.get('line'), total.get('over_odds'), total.get('under_odds'), 'oddsapi'
                ))
                inserted_count += 1
            conn.commit()
            return inserted_count > 0
            
        except sqlite3.IntegrityError:
            # Duplicate entry, skip
            return False
        except Exception as e:
            print(f"  ⚠️  Error inserting odds: {e}")
            return False
    
    def print_summary(self):
        """Print migration summary."""
        print("=" * 80)
        print("📊 MIGRATION SUMMARY")
        print("=" * 80)
        print()
        
        print("📈 RESULTS:")
        print(f"  Games Inserted:       {self.stats['games_inserted']:,}")
        print(f"  Games Updated:        {self.stats['games_updated']:,}")
        print(f"  Games Skipped:        {self.stats['games_skipped']:,}")
        print(f"  Odds Inserted:        {self.stats['odds_inserted']:,}")
        print(f"  Props Inserted:       {self.stats['props_inserted']:,}")
        print(f"  Perplexity Migrated:  {self.stats['perplexity_inserted']:,}")
        print()
        
        if self.stats['errors']:
            print("⚠️  ERRORS:")
            for error in self.stats['errors'][:10]:
                print(f"  - {error}")
            if len(self.stats['errors']) > 10:
                print(f"  ... and {len(self.stats['errors']) - 10} more")
            print()
        
        if not self.dry_run:
            print("✅ Migration Complete!")
            print()
            print("📋 NEXT STEPS:")
            print("  1. Run: python scripts/audit_state.py --verbose")
            print("  2. Run: python scripts/enrich_stats.py (if player stats missing)")
            print("  3. Run: python scripts/archive_legacy.py (to cleanup old files)")
        else:
            print("ℹ️  This was a DRY RUN - no changes were made")
            print("   Remove --dry-run flag to execute migration")
        
        print()
        print("=" * 80)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Grand Unification Migration - Consolidate all data into sports_data.db"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate migration without writing to database'
    )
    parser.add_argument(
        '--skip-perplexity',
        action='store_true',
        help='Skip perplexity.db migration'
    )
    parser.add_argument(
        '--skip-games',
        action='store_true',
        help='Skip historical games JSON migration'
    )
    parser.add_argument(
        '--skip-odds',
        action='store_true',
        help='Skip odds_cache migration'
    )
    parser.add_argument(
        '--db-path',
        default='data/sports_data.db',
        help='Path to target database (default: data/sports_data.db)'
    )
    
    args = parser.parse_args()
    
    # Create migrator
    migrator = GrandUnificationMigrator(db_path=args.db_path, dry_run=args.dry_run)
    
    try:
        # Execute migrations
        if not args.skip_perplexity:
            migrator.migrate_perplexity_cache()
        
        if not args.skip_games:
            migrator.migrate_games_from_json()
        
        if not args.skip_odds:
            migrator.migrate_odds_cache()
        
        # Print summary
        migrator.print_summary()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
