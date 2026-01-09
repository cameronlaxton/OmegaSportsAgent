#!/usr/bin/env python3
"""
⚠️ EXPERIMENTAL - USE WITH CAUTION

This script is experimental and may not work as expected.

Consider using:
    python scripts/collect_historical_sqlite.py --sports NBA NFL

Note:
    - This was an experimental enrichment approach
    - Odds collection is now better integrated into the main collection script
    - Keep for reference or experimental purposes only
    
See: START_HERE.md for recommended scripts

---

EXPERIMENTAL: Enrich games with historical betting odds.
Processes games where has_odds = 0.
Uses The Odds API to fetch historical betting lines.
"""

import sys
import json
import logging
from datetime import datetime, timedelta
from core.db_manager import DatabaseManager
from src.odds_api_client import TheOddsAPIClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def match_teams(odds_team, game_team):
    """Fuzzy team name matching."""
    odds_lower = odds_team.lower()
    game_lower = game_team.lower()
    return odds_lower in game_lower or game_lower in odds_lower


def enrich_odds(sport='NBA', season=None, limit=None):
    """
    Enrich games with betting odds.
    
    Args:
        sport: Sport type (NBA or NFL)
        season: Season year to filter (optional)
        limit: Max number of games to enrich (optional)
    """
    db = DatabaseManager('data/sports_data.db')
    odds_api = TheOddsAPIClient()
    
    # Query for games needing odds
    query = 'SELECT game_id, date, home_team, away_team, season FROM games WHERE sport = ? AND has_odds = 0'
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
        logger.info(f"✅ All {sport} games already have odds")
        return
    
    logger.info(f"🔄 Enriching {len(games)} {sport} games with betting odds...")
    
    enriched = 0
    errors = 0
    not_found = 0
    
    # Cache odds by date to minimize API calls
    odds_cache = {}
    
    for game in games:
        game_id, date, home_team, away_team, game_season = game
        
        try:
            # Fetch odds for this date (use cache if available)
            if date not in odds_cache:
                odds_games = odds_api.get_historical_odds(sport, date)
                odds_cache[date] = odds_games
            else:
                odds_games = odds_cache[date]
            
            # Match game by teams
            odds_data = None
            for odds_game in odds_games:
                if (match_teams(odds_game.get('home_team', ''), home_team) and
                    match_teams(odds_game.get('away_team', ''), away_team)):
                    odds_data = odds_game
                    break
            
            if odds_data:
                # Insert odds into odds_history table (multiple rows for each market)
                timestamp = int(datetime.now().timestamp())
                bookmaker = odds_data.get('bookmaker', 'fanduel')
                
                # Insert moneyline odds
                moneyline = odds_data.get('moneyline', {})
                if moneyline:
                    cursor.execute('''
                        INSERT OR IGNORE INTO odds_history 
                        (game_id, bookmaker, market_type, home_odds, away_odds, timestamp, source)
                        VALUES (?, ?, 'moneyline', ?, ?, ?, 'oddsapi')
                    ''', (game_id, bookmaker, moneyline.get('home'), moneyline.get('away'), timestamp))
                
                # Insert spread odds
                spread = odds_data.get('spread', {})
                if spread:
                    cursor.execute('''
                        INSERT OR IGNORE INTO odds_history 
                        (game_id, bookmaker, market_type, line, home_odds, away_odds, timestamp, source)
                        VALUES (?, ?, 'spread', ?, ?, ?, ?, 'oddsapi')
                    ''', (game_id, bookmaker, spread.get('line'), spread.get('home_odds'), spread.get('away_odds'), timestamp))
                
                # Insert total odds
                total = odds_data.get('total', {})
                if total:
                    cursor.execute('''
                        INSERT OR IGNORE INTO odds_history 
                        (game_id, bookmaker, market_type, line, over_odds, under_odds, timestamp, source)
                        VALUES (?, ?, 'total', ?, ?, ?, ?, 'oddsapi')
                    ''', (game_id, bookmaker, total.get('line'), total.get('over_odds'), total.get('under_odds'), timestamp))
                
                # Update game record with flattened odds
                update_data = {
                    'has_odds': 1,
                    'updated_at': timestamp
                }
                
                # Extract main betting lines if available
                if moneyline:
                    update_data['moneyline_home'] = moneyline.get('home')
                    update_data['moneyline_away'] = moneyline.get('away')
                
                if spread:
                    update_data['spread_line'] = spread.get('line')
                    update_data['spread_home_odds'] = spread.get('home_odds')
                    update_data['spread_away_odds'] = spread.get('away_odds')
                
                if total:
                    update_data['total_line'] = total.get('line')
                    update_data['total_over_odds'] = total.get('over_odds')
                    update_data['total_under_odds'] = total.get('under_odds')
                
                # Build UPDATE query
                set_clause = ', '.join([f"{k} = ?" for k in update_data.keys()])
                values = list(update_data.values()) + [game_id]
                
                cursor.execute(
                    f'UPDATE games SET {set_clause} WHERE game_id = ?',
                    values
                )
                conn.commit()
                
                enriched += 1
                if enriched % 10 == 0:
                    logger.info(f"  Progress: {enriched}/{len(games)} games enriched")
            else:
                not_found += 1
                
        except Exception as e:
            logger.error(f"  Error enriching odds for {game_id}: {e}")
            errors += 1
            continue
    
    logger.info(f"\n✅ Odds enrichment complete!")
    logger.info(f"   Enriched: {enriched}")
    logger.info(f"   Not found: {not_found}")
    logger.info(f"   Errors: {errors}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Enrich games with betting odds')
    parser.add_argument('--sport', default='NBA', choices=['NBA', 'NFL'], help='Sport type')
    parser.add_argument('--season', type=int, help='Season year (optional)')
    parser.add_argument('--limit', type=int, help='Max games to process (optional)')
    
    args = parser.parse_args()
    
    enrich_odds(sport=args.sport, season=args.season, limit=args.limit)
