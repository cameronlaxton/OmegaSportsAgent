#!/usr/bin/env python3
"""
Update player_props table with betting lines from player_props_odds.

This script:
1. Reads betting lines from player_props_odds table (populated by ingest_player_prop_odds.py)
2. Matches them to player_props records
3. Updates player_props with betting lines (over_line, over_odds, under_odds)

Usage:
    # First, fetch odds into player_props_odds:
    python scripts/ingest_player_prop_odds.py --sport NBA --date 2024-01-15
    
    # Then, update player_props with those lines:
    python scripts/update_player_props_with_lines.py --sport NBA --date 2024-01-15
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Project imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.db_manager import DatabaseManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def _normalize_player_name(name: str) -> str:
    """Normalize player name for matching."""
    if not name:
        return ""
    # Remove common suffixes and normalize
    name = name.strip().lower()
    # Handle variations
    name = name.replace("'", "").replace(".", "").replace("-", " ").replace("  ", " ")
    return name.strip()


def _players_match(name1: str, name2: str) -> bool:
    """Check if two player names match (fuzzy)."""
    n1 = _normalize_player_name(name1)
    n2 = _normalize_player_name(name2)
    
    if not n1 or not n2:
        return False
    
    # Exact match
    if n1 == n2:
        return True
    
    # Check if one contains the other (for nicknames)
    if n1 in n2 or n2 in n1:
        return True
    
    # Check if last names match (split by space, take last part)
    n1_parts = n1.split()
    n2_parts = n2.split()
    if n1_parts and n2_parts:
        if n1_parts[-1] == n2_parts[-1]:
            # Last names match, check if first initial matches
            if len(n1_parts) > 1 and len(n2_parts) > 1:
                if n1_parts[0][0] == n2_parts[0][0]:
                    return True
    
    return False


def update_player_props_from_odds(sport: str, dates: Optional[List[str]] = None):
    """
    Update player_props table with betting lines from player_props_odds.
    
    Args:
        sport: Sport name
        dates: Optional list of date strings (if None, processes all dates)
    """
    db = DatabaseManager("data/sports_data.db")
    conn = db.get_connection()
    cursor = conn.cursor()
    
    total_updated = 0
    total_matched = 0
    total_not_found = 0
    
    # Get all odds records (group by game_id, player, prop_type, line to get best odds)
    if dates:
        # Filter by dates
        date_filter = " AND g.date IN (" + ",".join(["?"] * len(dates)) + ")"
        params = [sport] + dates
    else:
        # Process all dates
        date_filter = ""
        params = [sport]
    
    logger.info(f"Fetching odds from player_props_odds for {sport}...")
    
    # Get all unique odds (take first bookmaker's odds for each prop)
    cursor.execute(f"""
        SELECT DISTINCT
            ppo.game_id,
            ppo.player_name,
            ppo.prop_type,
            ppo.line,
            ppo.over_odds,
            ppo.under_odds,
            ppo.bookmaker
        FROM player_props_odds ppo
        JOIN games g ON ppo.game_id = g.game_id
        WHERE g.sport = ? {date_filter}
        ORDER BY ppo.game_id, ppo.player_name, ppo.prop_type, ppo.line
    """, params)
    
    odds_records = cursor.fetchall()
    
    if not odds_records:
        logger.warning(f"No odds found in player_props_odds for {sport}")
        return
    
    logger.info(f"Found {len(odds_records)} odds records")
    
    # For each odds record, find matching player_props
    for odds_row in odds_records:
            game_id, odds_player_name, prop_type, line, over_odds, under_odds, bookmaker = odds_row
            
            # Find matching player_props
            cursor.execute("""
                SELECT prop_id, player_name, actual_value
                FROM player_props
                WHERE game_id = ? AND prop_type = ? AND sport = ?
            """, (game_id, prop_type, sport))
            
            matched = False
            for prop_row in cursor.fetchall():
                prop_id, db_player_name, actual_value = prop_row
                
                # Check if players match
                if _players_match(odds_player_name, db_player_name):
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
                        """, (
                            line,
                            line,
                            over_odds,
                            under_odds,
                            bookmaker,
                            prop_id
                        ))
                        total_updated += 1
                        matched = True
                        total_matched += 1
                        
                        if total_updated % 100 == 0:
                            conn.commit()
                            logger.info(f"  Updated {total_updated} props so far...")
                    except Exception as e:
                        logger.error(f"Error updating prop {prop_id}: {e}")
                        continue
            
            if not matched:
                total_not_found += 1
                if total_not_found <= 10:  # Log first 10 misses
                    logger.debug(f"  No match for {odds_player_name} ({prop_type}) in game {game_id}")
    
    conn.commit()
    logger.info(f"✅ Done. Total updated: {total_updated}, Matched: {total_matched}, Not found: {total_not_found}")


def _date_range(start_date: str, end_date: str) -> List[str]:
    """Generate list of dates between start and end."""
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    days = (end - start).days
    return [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days + 1)]


def main():
    parser = argparse.ArgumentParser(
        description="Update player_props with betting lines from player_props_odds"
    )
    parser.add_argument("--sport", default="NBA", help="Sport (default: NBA)")
    parser.add_argument("--date", help="Single date (YYYY-MM-DD)")
    parser.add_argument("--start-date", dest="start_date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", dest="end_date", help="End date (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    if args.date:
        dates = [args.date]
    else:
        if not args.start_date:
            logger.error("Must provide either --date or --start-date")
            return
        start = args.start_date
        end = args.end_date or start
        dates = _date_range(start, end)
    
    update_player_props_from_odds(args.sport, dates)


if __name__ == "__main__":
    main()

