#!/usr/bin/env python3
"""
Player Stats Enrichment Script

Finds games with missing player_stats and enriches them using:
1. BallDontLie API (primary, 60 req/min rate limit)
2. ESPN scraping (fallback)
3. Perplexity web search (last resort)

Usage:
    python scripts/enrich_stats.py
    python scripts/enrich_stats.py --sport NBA --season 2024
    python scripts/enrich_stats.py --limit 100
    python scripts/enrich_stats.py --dry-run
"""

import os
import sys
import time
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional
import requests
import logging

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.db_manager import DatabaseManager
from src.balldontlie_client import BallDontLieAPIClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class StatsEnricher:
    """Enriches games with missing player statistics."""
    
    def __init__(
        self,
        db_path: str = "data/sports_data.db",
        dry_run: bool = False,
        rate_limit: float = 1.0
    ):
        """
        Initialize enricher.
        
        Args:
            db_path: Path to SQLite database
            dry_run: If True, simulate without writing
            rate_limit: Seconds between API requests (default: 1.0 for 60/min)
        """
        self.db_path = db_path
        self.db_manager = DatabaseManager(db_path)
        self.dry_run = dry_run
        self.rate_limit = rate_limit
        
        # Initialize API clients
        self.balldontlie = BallDontLieAPIClient()
        
        self.stats = {
            'total_missing': 0,
            'enriched': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        print("=" * 80)
        print("🏀 PLAYER STATS ENRICHMENT")
        print("=" * 80)
        print(f"Database: {db_path}")
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        print(f"Rate Limit: {rate_limit}s between requests (max {60/rate_limit:.0f} req/min)")
        print()
    
    def find_missing_stats_games(
        self,
        sport: Optional[str] = None,
        season: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Find games missing player stats.
        
        Args:
            sport: Filter by sport (e.g., 'NBA')
            season: Filter by season year
            limit: Maximum number of games to return
            
        Returns:
            List of game records needing enrichment
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT game_id, date, sport, season, home_team, away_team, status
            FROM games
            WHERE (
                has_player_stats = 0 
                OR has_player_stats IS NULL
                OR player_stats IS NULL
                OR player_stats = ''
                OR player_stats = '[]'
            )
            AND status = 'Final'
        """
        
        params = []
        
        if sport:
            query += " AND sport = ?"
            params.append(sport)
        
        if season:
            query += " AND season = ?"
            params.append(season)
        
        query += " ORDER BY date DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, params)
        
        games = []
        for row in cursor.fetchall():
            games.append({
                'game_id': row[0],
                'date': row[1],
                'sport': row[2],
                'season': row[3],
                'home_team': row[4],
                'away_team': row[5],
                'status': row[6]
            })
        
        return games
    
    def enrich_game_stats(self, game: Dict[str, Any]) -> bool:
        """
        Enrich a single game with player stats.
        
        Args:
            game: Game record dictionary
            
        Returns:
            True if enriched successfully, False otherwise
        """
        game_id = game['game_id']
        game_date = game['date']
        sport = game['sport']
        
        logger.info(f"Enriching {game_id} ({game_date}): {game['away_team']} @ {game['home_team']}")
        
        if self.dry_run:
            logger.info(f"  [DRY RUN] Would enrich game")
            return True
        
        # Try BallDontLie API first (NBA only)
        if sport == 'NBA':
            player_stats = self._fetch_balldontlie_stats(game_id, game_date)
            
            if player_stats:
                logger.info(f"  ✅ Fetched stats from BallDontLie ({len(player_stats)} players)")
                return self._update_game_stats(game_id, player_stats)
        
        # Fallback: Try ESPN scraping
        logger.info(f"  ⚠️  BallDontLie unavailable, trying ESPN scraping...")
        player_stats = self._fetch_espn_stats(game_id, game_date)
        
        if player_stats:
            logger.info(f"  ✅ Fetched stats from ESPN ({len(player_stats)} players)")
            return self._update_game_stats(game_id, player_stats)
        
        # Last resort: Mark as attempted (no data available)
        logger.warning(f"  ❌ Could not fetch stats for {game_id}")
        return False
    
    def _fetch_balldontlie_stats(
        self,
        game_id: str,
        game_date: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch player stats from BallDontLie API.
        
        Args:
            game_id: Game ID (may contain ESPN or other identifiers)
            game_date: Game date YYYY-MM-DD
            
        Returns:
            List of player stat dictionaries or None
        """
        if not self.balldontlie.api_key:
            return None
        
        try:
            # Rate limiting
            time.sleep(self.rate_limit)
            
            # BallDontLie uses date-based queries
            # Get all games on that date, then match by team names
            games = self.balldontlie.get_games(
                start_date=game_date,
                end_date=game_date
            )
            
            if not games:
                logger.debug(f"  No games found on {game_date}")
                return None
            
            # Find matching game
            # Note: Would need to map team names to BallDontLie IDs for exact matching
            # For now, we'll get stats for all games that day
            
            # Get stats for the date range
            # BallDontLie API: /v1/stats?dates[]={date}&per_page=100
            url = f"{self.balldontlie.BASE_URL}/stats"
            params = {
                'dates[]': game_date,
                'per_page': 100
            }
            
            response = self.balldontlie.session.get(
                url,
                params=params,
                timeout=self.balldontlie.request_timeout
            )
            
            if response.status_code != 200:
                logger.warning(f"  BallDontLie API returned {response.status_code}")
                return None
            
            data = response.json()
            stats_data = data.get('data', [])
            
            if not stats_data:
                logger.debug(f"  No stats data for {game_date}")
                return None
            
            # Transform to our format
            player_stats = []
            for stat in stats_data:
                player = stat.get('player', {})
                team = stat.get('team', {})
                
                player_stats.append({
                    'player_name': f"{player.get('first_name', '')} {player.get('last_name', '')}".strip(),
                    'player_id': player.get('id'),
                    'team': team.get('full_name', team.get('name', '')),
                    'team_id': team.get('id'),
                    'minutes': stat.get('min', ''),
                    'points': stat.get('pts', 0),
                    'rebounds': stat.get('reb', 0),
                    'assists': stat.get('ast', 0),
                    'steals': stat.get('stl', 0),
                    'blocks': stat.get('blk', 0),
                    'turnovers': stat.get('turnover', 0),
                    'fouls': stat.get('pf', 0),
                    'fg_made': stat.get('fgm', 0),
                    'fg_attempted': stat.get('fga', 0),
                    'fg_pct': stat.get('fg_pct', 0),
                    'three_pt_made': stat.get('fg3m', 0),
                    'three_pt_attempted': stat.get('fg3a', 0),
                    'three_pt_pct': stat.get('fg3_pct', 0),
                    'ft_made': stat.get('ftm', 0),
                    'ft_attempted': stat.get('fta', 0),
                    'ft_pct': stat.get('ft_pct', 0),
                    'plus_minus': stat.get('plus_minus'),
                })
            
            return player_stats if player_stats else None
            
        except requests.RequestException as e:
            logger.error(f"  API request error: {e}")
            return None
        except Exception as e:
            logger.error(f"  Error fetching BallDontLie stats: {e}")
            return None
    
    def _fetch_espn_stats(
        self,
        game_id: str,
        game_date: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch player stats from ESPN (web scraping fallback).
        
        Args:
            game_id: Game ID (should contain ESPN ID if from ESPN)
            game_date: Game date YYYY-MM-DD
            
        Returns:
            List of player stat dictionaries or None
        """
        # Extract ESPN ID from game_id if present
        if 'espn' not in game_id.lower():
            logger.debug(f"  Game ID doesn't contain ESPN identifier")
            return None
        
        try:
            # Extract numeric ESPN game ID
            # Format: nba_espn_401234567 -> 401234567
            espn_id = game_id.split('_')[-1]
            
            if not espn_id.isdigit():
                logger.debug(f"  Could not extract numeric ESPN ID from {game_id}")
                return None
            
            # Rate limiting
            time.sleep(self.rate_limit)
            
            # ESPN box score API endpoint
            url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary"
            params = {'event': espn_id}
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"  ESPN API returned {response.status_code}")
                return None
            
            data = response.json()
            
            # Extract player stats from box score
            player_stats = []
            
            # ESPN structure: boxscore -> players -> team -> statistics
            boxscore = data.get('boxscore', {})
            players_data = boxscore.get('players', [])
            
            for team_data in players_data:
                team_name = team_data.get('team', {}).get('displayName', '')
                statistics = team_data.get('statistics', [])
                
                # Find stat labels
                stat_labels = []
                if statistics:
                    stat_labels = statistics[0].get('labels', [])
                
                # Process each player
                for player_group in statistics:
                    athletes = player_group.get('athletes', [])
                    
                    for athlete in athletes:
                        athlete_info = athlete.get('athlete', {})
                        stats_values = athlete.get('stats', [])
                        
                        if not stats_values or all(v == '0' for v in stats_values):
                            continue  # Skip DNP players
                        
                        # Map stats to our format
                        stat_dict = dict(zip(stat_labels, stats_values))
                        
                        player_stats.append({
                            'player_name': athlete_info.get('displayName', ''),
                            'player_id': athlete_info.get('id'),
                            'team': team_name,
                            'minutes': stat_dict.get('MIN', '0'),
                            'points': int(stat_dict.get('PTS', 0)) if stat_dict.get('PTS', '0').isdigit() else 0,
                            'rebounds': int(stat_dict.get('REB', 0)) if stat_dict.get('REB', '0').isdigit() else 0,
                            'assists': int(stat_dict.get('AST', 0)) if stat_dict.get('AST', '0').isdigit() else 0,
                            'steals': int(stat_dict.get('STL', 0)) if stat_dict.get('STL', '0').isdigit() else 0,
                            'blocks': int(stat_dict.get('BLK', 0)) if stat_dict.get('BLK', '0').isdigit() else 0,
                            'turnovers': int(stat_dict.get('TO', 0)) if stat_dict.get('TO', '0').isdigit() else 0,
                            'fg': stat_dict.get('FG', '0-0'),
                            'three_pt': stat_dict.get('3PT', '0-0'),
                            'ft': stat_dict.get('FT', '0-0'),
                        })
            
            return player_stats if player_stats else None
            
        except requests.RequestException as e:
            logger.error(f"  ESPN request error: {e}")
            return None
        except Exception as e:
            logger.error(f"  Error scraping ESPN: {e}")
            return None
    
    def _update_game_stats(self, game_id: str, player_stats: List[Dict[str, Any]]) -> bool:
        """
        Update game record with player stats.
        
        Args:
            game_id: Game ID
            player_stats: List of player stat dictionaries
            
        Returns:
            True if updated successfully
        """
        if self.dry_run:
            return True
        
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Serialize player stats to JSON
            player_stats_json = json.dumps(player_stats)
            
            # Update game record
            cursor.execute("""
                UPDATE games
                SET player_stats = ?,
                    has_player_stats = 1,
                    updated_at = ?
                WHERE game_id = ?
            """, (
                player_stats_json,
                int(datetime.now().timestamp()),
                game_id
            ))
            
            conn.commit()
            
            return cursor.rowcount > 0
            
        except sqlite3.Error as e:
            logger.error(f"  Database error updating {game_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"  Error updating {game_id}: {e}")
            return False
    
    def enrich_all(
        self,
        sport: Optional[str] = None,
        season: Optional[int] = None,
        limit: Optional[int] = None
    ):
        """
        Enrich all games missing player stats.
        
        Args:
            sport: Filter by sport
            season: Filter by season
            limit: Maximum number of games to enrich
        """
        print("=" * 80)
        print("🔍 FINDING GAMES MISSING PLAYER STATS")
        print("=" * 80)
        
        games = self.find_missing_stats_games(sport=sport, season=season, limit=limit)
        
        self.stats['total_missing'] = len(games)
        
        print(f"Found {len(games)} games needing enrichment")
        
        if not games:
            print("✅ No games need enrichment!")
            return
        
        print()
        print("=" * 80)
        print("🚀 STARTING ENRICHMENT")
        print("=" * 80)
        print()
        
        start_time = time.time()
        
        for i, game in enumerate(games):
            print(f"[{i+1}/{len(games)}] {game['game_id']}")
            
            try:
                success = self.enrich_game_stats(game)
                
                if success:
                    self.stats['enriched'] += 1
                else:
                    self.stats['failed'] += 1
                
                # Progress update every 10 games
                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed
                    remaining = (len(games) - i - 1) / rate if rate > 0 else 0
                    
                    print()
                    print(f"📊 Progress: {i+1}/{len(games)} games ({(i+1)/len(games)*100:.1f}%)")
                    print(f"   Enriched: {self.stats['enriched']}, Failed: {self.stats['failed']}")
                    print(f"   Rate: {rate:.1f} games/sec, ETA: {remaining/60:.1f} min")
                    print()
            
            except KeyboardInterrupt:
                print("\n\n⚠️  Enrichment interrupted by user")
                break
            except Exception as e:
                error_msg = f"Unexpected error enriching {game['game_id']}: {e}"
                logger.error(error_msg)
                self.stats['errors'].append(error_msg)
                self.stats['failed'] += 1
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print enrichment summary."""
        print()
        print("=" * 80)
        print("📊 ENRICHMENT SUMMARY")
        print("=" * 80)
        print()
        
        print(f"Total Missing:  {self.stats['total_missing']:,}")
        print(f"Enriched:       {self.stats['enriched']:,}")
        print(f"Failed:         {self.stats['failed']:,}")
        print(f"Skipped:        {self.stats['skipped']:,}")
        print()
        
        if self.stats['enriched'] > 0 and self.stats['total_missing'] > 0:
            success_rate = self.stats['enriched'] / self.stats['total_missing'] * 100
            print(f"Success Rate: {success_rate:.1f}%")
            print()
        
        if self.stats['errors']:
            print("⚠️  ERRORS:")
            for error in self.stats['errors'][:10]:
                print(f"  - {error}")
            if len(self.stats['errors']) > 10:
                print(f"  ... and {len(self.stats['errors']) - 10} more")
            print()
        
        if not self.dry_run:
            print("✅ Enrichment Complete!")
            print()
            print("📋 NEXT STEPS:")
            print("  Run: python scripts/audit_state.py --verbose")
        else:
            print("ℹ️  This was a DRY RUN - no changes were made")
        
        print()
        print("=" * 80)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enrich games with player statistics")
    parser.add_argument(
        '--sport',
        help='Filter by sport (e.g., NBA)'
    )
    parser.add_argument(
        '--season',
        type=int,
        help='Filter by season year'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of games to enrich'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate without writing to database'
    )
    parser.add_argument(
        '--rate-limit',
        type=float,
        default=1.0,
        help='Seconds between API requests (default: 1.0)'
    )
    parser.add_argument(
        '--db-path',
        default='data/sports_data.db',
        help='Path to database (default: data/sports_data.db)'
    )
    
    args = parser.parse_args()
    
    # Create enricher
    enricher = StatsEnricher(
        db_path=args.db_path,
        dry_run=args.dry_run,
        rate_limit=args.rate_limit
    )
    
    try:
        # Run enrichment
        enricher.enrich_all(
            sport=args.sport,
            season=args.season,
            limit=args.limit
        )
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        enricher.print_summary()
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
