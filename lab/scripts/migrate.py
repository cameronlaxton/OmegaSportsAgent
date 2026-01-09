"""
One-time migration script to import legacy JSON data into SQLite database.

Migrates:
1. sample_nba_2024_games.json -> games table
2. odds_cache/*.json -> odds_history table
3. perplexity.db (if exists) -> perplexity_cache table (preserve existing)

Usage:
    python scripts/migrate.py [--dry-run]
"""

import os
import sys
import json
import glob
import sqlite3
from datetime import datetime
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.db_manager import DatabaseManager


class DataMigrator:
    """Handles migration of legacy JSON data to SQLite."""
    
    def __init__(self, db_path: str = "data/sports_data.db", dry_run: bool = False):
        """
        Initialize migrator.
        
        Args:
            db_path: Path to SQLite database
            dry_run: If True, print actions without writing to database
        """
        self.db_manager = DatabaseManager(db_path)
        self.dry_run = dry_run
        self.stats = {
            'games': 0,
            'props': 0,
            'odds': 0,
            'perplexity': 0,
            'errors': 0
        }
    
    def migrate_games_json(self, json_path: str):
        """
        Migrate games from JSON file to database.
        
        Args:
            json_path: Path to JSON file (e.g., sample_nba_2024_games.json)
        """
        if not os.path.exists(json_path):
            print(f"⚠️  File not found: {json_path}")
            return
        
        print(f"\n📂 Migrating games from: {json_path}")
        
        try:
            with open(json_path, 'r') as f:
                games = json.load(f)
            
            if not isinstance(games, list):
                print(f"❌ Expected list of games, got {type(games)}")
                return
            
            print(f"   Found {len(games)} games")
            
            for game in games:
                if self.dry_run:
                    print(f"   [DRY RUN] Would insert game: {game.get('game_id')}")
                else:
                    if self.db_manager.insert_game(game):
                        self.stats['games'] += 1
                    else:
                        self.stats['errors'] += 1
            
            print(f"✅ Migrated {self.stats['games']} games")
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error in {json_path}: {e}")
            self.stats['errors'] += 1
        except Exception as e:
            print(f"❌ Error migrating {json_path}: {e}")
            self.stats['errors'] += 1
    
    def migrate_odds_cache(self, cache_dir: str = "data/odds_cache"):
        """
        Migrate historical odds from cache directory.
        
        Args:
            cache_dir: Root odds cache directory
        """
        if not os.path.exists(cache_dir):
            print(f"\n⚠️  Odds cache not found: {cache_dir}")
            return
        
        print(f"\n📂 Migrating odds cache from: {cache_dir}")
        
        # Find all JSON files in odds_cache/**/*.json
        pattern = os.path.join(cache_dir, "**", "*.json")
        json_files = glob.glob(pattern, recursive=True)
        
        if not json_files:
            print(f"   No JSON files found in {cache_dir}")
            return
        
        print(f"   Found {len(json_files)} odds files")
        
        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    odds_data = json.load(f)
                
                # Parse file path for metadata
                # Example: data/odds_cache/nba/2023/2023-10-24.json
                rel_path = os.path.relpath(json_file, cache_dir)
                parts = rel_path.split(os.sep)
                
                sport = parts[0].upper() if len(parts) > 0 else 'NBA'
                date_str = os.path.splitext(os.path.basename(json_file))[0]
                
                # Handle different odds cache formats
                if isinstance(odds_data, list):
                    # Format: List of game odds
                    for game_odds in odds_data:
                        self._insert_game_odds(game_odds, sport, date_str)
                
                elif isinstance(odds_data, dict):
                    # Format: Single game or nested structure
                    if 'games' in odds_data:
                        for game_odds in odds_data['games']:
                            self._insert_game_odds(game_odds, sport, date_str)
                    else:
                        self._insert_game_odds(odds_data, sport, date_str)
            
            except Exception as e:
                print(f"   ⚠️  Error in {json_file}: {e}")
                self.stats['errors'] += 1
        
        print(f"✅ Migrated {self.stats['odds']} odds records")
    
    def _insert_game_odds(self, game_odds: Dict[str, Any], sport: str, date_str: str):
        """
        Insert odds for a single game.
        
        Args:
            game_odds: Odds data for one game
            sport: Sport type
            date_str: Date string (YYYY-MM-DD)
        """
        game_id = game_odds.get('id') or game_odds.get('game_id')
        
        if not game_id:
            return
        
        bookmakers = game_odds.get('bookmakers', [])
        
        for bookmaker_data in bookmakers:
            bookmaker = bookmaker_data.get('key') or bookmaker_data.get('title', 'unknown')
            markets = bookmaker_data.get('markets', [])
            
            for market in markets:
                market_type = market.get('key')  # 'h2h', 'spreads', 'totals'
                outcomes = market.get('outcomes', [])
                
                if not market_type or not outcomes:
                    continue
                
                # Convert market key to our format
                if market_type == 'h2h':
                    market_type = 'moneyline'
                elif market_type == 'spreads':
                    market_type = 'spread'
                elif market_type == 'totals':
                    market_type = 'total'
                
                # Build odds record
                odds_record = {
                    'game_id': str(game_id),
                    'bookmaker': bookmaker,
                    'market_type': market_type,
                    'source': 'oddsapi',
                    'timestamp': int(datetime.now().timestamp())
                }
                
                # Parse outcomes
                for outcome in outcomes:
                    name = outcome.get('name', '').lower()
                    price = outcome.get('price')  # American odds
                    point = outcome.get('point')  # Spread/total line
                    
                    if market_type == 'moneyline':
                        if 'home' in name or name == outcomes[0].get('name'):
                            odds_record['home_odds'] = price
                        else:
                            odds_record['away_odds'] = price
                    
                    elif market_type == 'spread':
                        if point:
                            odds_record['line'] = point
                        if 'home' in name or name == outcomes[0].get('name'):
                            odds_record['home_odds'] = price
                        else:
                            odds_record['away_odds'] = price
                    
                    elif market_type == 'total':
                        if point:
                            odds_record['line'] = point
                        if 'over' in name.lower():
                            odds_record['over_odds'] = price
                        elif 'under' in name.lower():
                            odds_record['under_odds'] = price
                
                # Insert into database
                if self.dry_run:
                    print(f"   [DRY RUN] Would insert odds: {game_id} - {bookmaker} - {market_type}")
                else:
                    if self.db_manager.insert_odds_history(odds_record):
                        self.stats['odds'] += 1
    
    def migrate_perplexity_cache(self, old_db_path: str = "data/cache/perplexity.db"):
        """
        Migrate existing Perplexity cache from old database.
        
        Args:
            old_db_path: Path to legacy perplexity.db
        """
        if not os.path.exists(old_db_path):
            print(f"\n⚠️  Perplexity cache not found: {old_db_path}")
            return
        
        print(f"\n📂 Migrating Perplexity cache from: {old_db_path}")
        
        try:
            # Connect to old database
            old_conn = sqlite3.connect(old_db_path)
            old_conn.row_factory = sqlite3.Row
            cursor = old_conn.cursor()
            
            # Check if table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='perplexity_cache'
            """)
            
            if not cursor.fetchone():
                print("   No perplexity_cache table found in old database")
                old_conn.close()
                return
            
            # Read all cache entries
            cursor.execute("SELECT * FROM perplexity_cache")
            rows = cursor.fetchall()
            
            print(f"   Found {len(rows)} cache entries")
            
            for row in rows:
                cache_data = dict(row)
                
                if self.dry_run:
                    print(f"   [DRY RUN] Would insert cache: {cache_data.get('query_hash')}")
                else:
                    if self.db_manager.insert_perplexity_cache(cache_data):
                        self.stats['perplexity'] += 1
                    else:
                        self.stats['errors'] += 1
            
            old_conn.close()
            print(f"✅ Migrated {self.stats['perplexity']} Perplexity cache entries")
            
        except sqlite3.Error as e:
            print(f"❌ SQLite error: {e}")
            self.stats['errors'] += 1
        except Exception as e:
            print(f"❌ Error migrating Perplexity cache: {e}")
            self.stats['errors'] += 1
    
    def print_summary(self):
        """Print migration summary report."""
        print("\n" + "="*60)
        print("MIGRATION SUMMARY")
        print("="*60)
        print(f"Games migrated:           {self.stats['games']:>6}")
        print(f"Props migrated:           {self.stats['props']:>6}")
        print(f"Odds records migrated:    {self.stats['odds']:>6}")
        print(f"Perplexity cache entries: {self.stats['perplexity']:>6}")
        print(f"Errors encountered:       {self.stats['errors']:>6}")
        print("="*60)
        
        if not self.dry_run:
            # Get current database stats
            db_stats = self.db_manager.get_stats()
            print("\nCURRENT DATABASE STATE")
            print("="*60)
            for table, count in db_stats.items():
                print(f"{table:.<30} {count:>6}")
            print("="*60)


def main():
    """Run migration."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate legacy JSON data to SQLite')
    parser.add_argument('--dry-run', action='store_true', help='Print actions without executing')
    parser.add_argument('--db', default='data/sports_data.db', help='SQLite database path')
    
    args = parser.parse_args()
    
    print("="*60)
    print("SPORTS DATA MIGRATION TO SQLITE")
    print("="*60)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No data will be written\n")
    
    migrator = DataMigrator(db_path=args.db, dry_run=args.dry_run)
    
    # Migrate games
    games_files = [
        'data/historical/sample_nba_2024_games.json',
        'data/historical/nba_2020_games.json',
        'data/historical/nba_2021_games.json',
        'data/historical/nba_2022_games.json',
        'data/historical/nba_2023_games.json',
        'data/historical/nba_2024_games.json',
        'data/historical/nfl_2020_games.json',
        'data/historical/nfl_2021_games.json',
        'data/historical/nfl_2022_games.json',
        'data/historical/nfl_2023_games.json',
        'data/historical/nfl_2024_games.json',
    ]
    
    for games_file in games_files:
        migrator.migrate_games_json(games_file)
    
    # Migrate odds cache
    migrator.migrate_odds_cache('data/odds_cache')
    
    # Migrate Perplexity cache
    migrator.migrate_perplexity_cache('data/cache/perplexity.db')
    
    # Print summary
    migrator.print_summary()
    
    if args.dry_run:
        print("\n💡 Run without --dry-run to execute migration")
    else:
        print("\n✅ Migration complete!")


if __name__ == '__main__':
    main()
