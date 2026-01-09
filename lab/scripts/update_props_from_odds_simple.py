#!/usr/bin/env python3
"""
Simple script to update player_props with betting lines from player_props_odds.

Matches by team names and dates instead of game_ids (which may not match).

Usage:
    python scripts/update_props_from_odds_simple.py --sport NBA
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.db_manager import DatabaseManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def _normalize_team(name: str) -> str:
    """Normalize team name."""
    if not name:
        return ""
    return name.lower().replace('.', '').replace(' ', '').strip()


def _teams_match(a: str, b: str) -> bool:
    """Check if team names match."""
    na, nb = _normalize_team(a), _normalize_team(b)
    return na and nb and (na in nb or nb in na)


def _normalize_player(name: str) -> str:
    """Normalize player name."""
    if not name:
        return ""
    return name.lower().strip().replace("'", "").replace(".", "").replace("-", " ")


def _players_match(name1: str, name2: str) -> bool:
    """Check if player names match."""
    n1 = _normalize_player(name1)
    n2 = _normalize_player(name2)
    if not n1 or not n2:
        return False
    if n1 == n2:
        return True
    # Check if one contains the other
    if n1 in n2 or n2 in n1:
        return True
    # Check last name match
    n1_parts = n1.split()
    n2_parts = n2.split()
    if n1_parts and n2_parts and n1_parts[-1] == n2_parts[-1]:
        return True
    return False


def update_all_props(sport: str):
    """Update all player_props with lines from player_props_odds."""
    db = DatabaseManager("data/sports_data.db")
    conn = db.get_connection()
    cursor = conn.cursor()
    
    logger.info(f"Updating player_props for {sport}...")
    
    # Get all odds records with game info
    cursor.execute("""
        SELECT 
            ppo.game_id as odds_game_id,
            ppo.player_name as odds_player,
            ppo.prop_type,
            ppo.line,
            ppo.over_odds,
            ppo.under_odds,
            ppo.bookmaker,
            g.date,
            g.home_team,
            g.away_team
        FROM player_props_odds ppo
        JOIN games g ON ppo.game_id = g.game_id
        WHERE g.sport = ?
        ORDER BY g.date, ppo.player_name, ppo.prop_type
    """, (sport,))
    
    odds_records = cursor.fetchall()
    logger.info(f"Found {len(odds_records)} odds records")
    
    if not odds_records:
        logger.warning("No odds records found")
        return
    
    updated = 0
    matched = 0
    not_found = 0
    
    # For each odds record, find matching player_props by date and teams
    for odds_row in odds_records:
        (odds_game_id, odds_player, prop_type, line, over_odds, under_odds, 
         bookmaker, game_date, home_team, away_team) = odds_row
        
        # Find player_props for this date and prop_type
        cursor.execute("""
            SELECT pp.prop_id, pp.player_name, pp.game_id, g.home_team, g.away_team
            FROM player_props pp
            JOIN games g ON pp.game_id = g.game_id
            WHERE pp.sport = ? 
                AND pp.prop_type = ?
                AND g.date = ?
        """, (sport, prop_type, game_date))
        
        matched_prop = False
        for prop_row in cursor.fetchall():
            prop_id, db_player, db_game_id, db_home, db_away = prop_row
            
            # Check if teams match
            if not (_teams_match(home_team, db_home) and _teams_match(away_team, db_away)):
                continue
            
            # Check if players match
            if _players_match(odds_player, db_player):
                # Update this prop
                try:
                    cursor.execute("""
                        UPDATE player_props
                        SET over_line = ?,
                            under_line = ?,
                            over_odds = ?,
                            under_odds = ?,
                            bookmaker = COALESCE(?, bookmaker)
                        WHERE prop_id = ?
                    """, (line, line, over_odds, under_odds, bookmaker, prop_id))
                    
                    updated += 1
                    matched_prop = True
                    matched += 1
                    
                    if updated % 100 == 0:
                        conn.commit()
                        logger.info(f"  Updated {updated} props...")
                except Exception as e:
                    logger.error(f"Error updating {prop_id}: {e}")
        
        if not matched_prop:
            not_found += 1
            if not_found <= 20:
                logger.debug(f"  No match: {odds_player} ({prop_type}) on {game_date}")
    
    conn.commit()
    logger.info(f"✅ Done. Updated: {updated}, Matched: {matched}, Not found: {not_found}")


def main():
    parser = argparse.ArgumentParser(
        description="Update player_props with betting lines from player_props_odds"
    )
    parser.add_argument("--sport", default="NBA", help="Sport (default: NBA)")
    
    args = parser.parse_args()
    update_all_props(args.sport)


if __name__ == "__main__":
    main()

