#!/usr/bin/env python3
"""
⚠️ EXPERIMENTAL - USE WITH CAUTION

This script is experimental and may not work as expected.

Consider using:
    python scripts/collect_historical_sqlite.py --sports NBA NFL

Note:
    - This was an experimental enrichment approach
    - Player stats collection is now better integrated into the main collection script
    - Keep for reference or experimental purposes only
    
See: START_HERE.md for recommended scripts

---

EXPERIMENTAL: Enrich games with player statistics from BallDontLie API.
Processes games where has_player_stats = 0.
"""

import sys
import json
import logging
from datetime import datetime
from core.db_manager import DatabaseManager
from src.balldontlie_client import BallDontLieAPIClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def enrich_player_stats(sport='NBA', season=None, limit=None):
    """
    Enrich games with player statistics.
    
    Args:
        sport: Sport type (NBA or NFL)
        season: Season year to filter (optional)
        limit: Max number of games to enrich (optional)
    """
    db = DatabaseManager('data/sports_data.db')
    client = BallDontLieAPIClient()
    
    # Query for games needing player stats
    query = 'SELECT game_id, date, home_team, away_team, season FROM games WHERE sport = ? AND has_player_stats = 0'
    params = [sport]
    
    if season:
        query += ' AND season = ?'
        params.append(season)
    
    if limit:
        query += f' LIMIT {limit}'
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    games = cursor.fetchall()
    
    if not games:
        logger.info(f"✅ All {sport} games already have player stats")
        return
    
    logger.info(f"🔄 Enriching {len(games)} {sport} games with player statistics...")
    
    enriched = 0
    errors = 0
    
    for game in games:
        game_id, date, home_team, away_team, game_season = game
        
        try:
            # Extract BallDontLie game ID from our game_id format
            # Handles both "nba_12345" and "12345" formats
            if '_' in str(game_id):
                bdl_game_id = int(game_id.split('_')[1])
            else:
                bdl_game_id = int(game_id)
            
            # Fetch player stats for this game
            stats = client.get_game_stats([bdl_game_id])
            
            if stats:
                # Convert to JSON and update database
                player_stats_json = json.dumps(stats)
                
                cursor.execute(
                    'UPDATE games SET player_stats = ?, has_player_stats = 1, updated_at = ? WHERE game_id = ?',
                    (player_stats_json, int(datetime.now().timestamp()), game_id)
                )
                conn.commit()
                
                enriched += 1
                if enriched % 10 == 0:
                    logger.info(f"  Progress: {enriched}/{len(games)} games enriched")
            else:
                logger.warning(f"  No stats returned for game {game_id}")
                
        except Exception as e:
            logger.error(f"  Error enriching {game_id}: {e}")
            errors += 1
            continue
    
    logger.info(f"\n✅ Player stats enrichment complete!")
    logger.info(f"   Enriched: {enriched}")
    logger.info(f"   Errors: {errors}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Enrich games with player statistics')
    parser.add_argument('--sport', default='NBA', choices=['NBA', 'NFL'], help='Sport type')
    parser.add_argument('--season', type=int, help='Season year (optional)')
    parser.add_argument('--limit', type=int, help='Max games to process (optional)')
    
    args = parser.parse_args()
    
    enrich_player_stats(sport=args.sport, season=args.season, limit=args.limit)
