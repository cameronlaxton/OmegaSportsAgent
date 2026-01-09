#!/usr/bin/env python3
"""
Simple script to update player_props with betting lines.

This script provides a simpler alternative that:
1. Uses The Odds API to fetch current/upcoming player props
2. Directly updates player_props table

OR

3. Allows manual entry of betting lines for testing

Usage:
    # Try to fetch from API (for current/upcoming games)
    python scripts/simple_prop_line_update.py --sport NBA --fetch
    
    # Or manually set a default line for testing
    python scripts/simple_prop_line_update.py --sport NBA --set-default-lines
"""

import argparse
import logging
import os
import sys
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# Project imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.db_manager import DatabaseManager
from src.odds_api_client import TheOddsAPIClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def set_default_lines_for_testing(sport: str):
    """
    Set default betting lines for player props based on historical averages.
    
    This is a TEMPORARY solution for testing calibration when API data isn't available.
    Uses average actual values as proxy for betting lines.
    """
    db = DatabaseManager("data/sports_data.db")
    conn = db.get_connection()
    cursor = conn.cursor()
    
    logger.info(f"Setting default lines for {sport} player props based on averages...")
    
    # For each prop type, calculate average actual_value and use as line
    prop_types = ['points', 'rebounds', 'assists']
    
    for prop_type in prop_types:
        # Get average actual_value for this prop type
        cursor.execute("""
            SELECT AVG(actual_value), COUNT(*)
            FROM player_props
            WHERE sport = ? AND prop_type = ? AND actual_value IS NOT NULL
        """, (sport, prop_type))
        
        row = cursor.fetchone()
        if row and row[0] is not None:
            avg_value = float(row[0])
            count = row[1]
            
            # Round to nearest 0.5 for typical betting lines
            line = round(avg_value * 2) / 2
            
            # Use standard -110 odds
            over_odds = -110
            under_odds = -110
            
            # Update all props of this type that don't have lines
            cursor.execute("""
                UPDATE player_props
                SET over_line = ?,
                    under_line = ?,
                    over_odds = ?,
                    under_odds = ?
                WHERE sport = ? 
                    AND prop_type = ?
                    AND over_line IS NULL
                    AND actual_value IS NOT NULL
            """, (line, line, over_odds, under_odds, sport, prop_type))
            
            updated = cursor.rowcount
            logger.info(f"  {prop_type}: Set line={line} for {updated} props (avg={avg_value:.1f}, n={count})")
    
    conn.commit()
    logger.info("✅ Default lines set (for testing only - not real betting lines!)")


def fetch_and_update_current_props(sport: str):
    """Fetch current player props from API and update database."""
    load_dotenv('.env')
    
    client = TheOddsAPIClient()
    if not client.api_key:
        logger.error("THE_ODDS_API_KEY not set")
        return
    
    # Get today's date
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    
    logger.info(f"Fetching current player props for {sport} (date: {today})")
    
    # Fetch player props
    try:
        props = client.fetch_player_props(sport=sport, date=today)
        logger.info(f"Fetched {len(props)} props from API")
        
        if not props:
            logger.warning("No props returned - API may not have current data")
            return
        
        # Update player_props with these lines
        db = DatabaseManager("data/sports_data.db")
        conn = db.get_connection()
        cursor = conn.cursor()
        
        updated = 0
        
        # Group props by player+type+line
        props_by_key = {}
        for prop in props:
            player = prop.get("player_name", "").strip()
            prop_type_raw = prop.get("prop_type", "")
            # Map API prop type to our prop type
            prop_type_map = {
                "points": "points",
                "rebounds": "rebounds", 
                "assists": "assists"
            }
            prop_type = prop_type_map.get(prop_type_raw, prop_type_raw)
            line = prop.get("line")
            
            if not player or not prop_type or line is None:
                continue
            
            key = (player.lower(), prop_type, float(line))
            if key not in props_by_key:
                props_by_key[key] = {
                    "player": player,
                    "prop_type": prop_type,
                    "line": float(line),
                    "over_odds": None,
                    "under_odds": None
                }
            
            if prop.get("over_odds"):
                props_by_key[key]["over_odds"] = prop.get("over_odds")
            if prop.get("under_odds"):
                props_by_key[key]["under_odds"] = prop.get("under_odds")
        
        # Match to player_props
        for key, api_prop in props_by_key.items():
            player_lower, prop_type, line = key
            
            # Find matching props
            cursor.execute("""
                SELECT prop_id, player_name, game_id
                FROM player_props
                WHERE sport = ? 
                    AND prop_type = ?
                    AND LOWER(player_name) LIKE ?
                    AND over_line IS NULL
            """, (sport, prop_type, f"%{player_lower}%"))
            
            for row in cursor.fetchall():
                prop_id, db_player, game_id = row
                # Update
                try:
                    cursor.execute("""
                        UPDATE player_props
                        SET over_line = ?,
                            under_line = ?,
                            over_odds = ?,
                            under_odds = ?
                        WHERE prop_id = ?
                    """, (
                        line,
                        line,
                        api_prop["over_odds"],
                        api_prop["under_odds"],
                        prop_id
                    ))
                    updated += 1
                except Exception as e:
                    logger.error(f"Error updating {prop_id}: {e}")
        
        conn.commit()
        logger.info(f"✅ Updated {updated} player props with betting lines")
        
    except Exception as e:
        logger.error(f"Error fetching props: {e}", exc_info=True)


def main():
    parser = argparse.ArgumentParser(
        description="Update player_props with betting lines"
    )
    parser.add_argument("--sport", default="NBA", help="Sport")
    parser.add_argument("--fetch", action="store_true", help="Fetch from API (current games)")
    parser.add_argument("--set-default-lines", action="store_true", 
                       help="Set default lines based on averages (for testing)")
    
    args = parser.parse_args()
    
    if args.set_default_lines:
        set_default_lines_for_testing(args.sport)
    elif args.fetch:
        fetch_and_update_current_props(args.sport)
    else:
        parser.print_help()
        print("\nChoose one:")
        print("  --fetch              : Fetch current props from API")
        print("  --set-default-lines  : Set default lines for testing")


if __name__ == "__main__":
    main()

