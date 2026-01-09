#!/usr/bin/env python3
"""
Fetch player prop betting lines from The Odds API and update player_props table.

This script:
1. Fetches player prop odds from The Odds API for specified dates
2. Matches them to existing player_props records
3. Updates player_props with betting lines (over_line, over_odds, under_odds)

Usage:
    python scripts/fetch_player_prop_lines.py --sport NBA --date 2024-01-15
    python scripts/fetch_player_prop_lines.py --sport NBA --start-date 2024-01-01 --end-date 2024-01-07
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# Project imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.db_manager import DatabaseManager
from src.odds_api_client import TheOddsAPIClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Map API market keys to internal prop_type values
PROP_TYPE_MAP = {
    "player_points": "points",
    "player_rebounds": "rebounds",
    "player_assists": "assists",
    "player_steals": "steals",
    "player_blocks": "blocks",
    "player_threes": "three_pt_made",
}


def _normalize_team(name: str) -> str:
    """Normalize team name for matching."""
    if not name:
        return ""
    return name.lower().replace('.', '').replace(' ', '').strip()


def _teams_match(a: str, b: str) -> bool:
    """Check if two team names match."""
    na, nb = _normalize_team(a), _normalize_team(b)
    return na and nb and (na in nb or nb in na)


def _normalize_player_name(name: str) -> str:
    """Normalize player name for matching."""
    if not name:
        return ""
    # Remove common suffixes and normalize
    name = name.strip()
    # Handle variations like "LeBron James" vs "Lebron James"
    return name.lower().replace("'", "").replace(".", "")


def _combine_over_under_props(api_props: List[Dict[str, Any]]) -> Dict[tuple, Dict[str, Any]]:
    """Combine over/under outcomes into single prop records."""
    combined = {}
    
    for prop in api_props:
        # The API returns separate entries for over/under
        player_name = prop.get("player_name", "").strip()
        prop_type_raw = prop.get("prop_type", "")
        prop_type = PROP_TYPE_MAP.get(prop_type_raw) or prop_type_raw.replace("player_", "")
        line = prop.get("line") or prop.get("over_line") or prop.get("under_line")
        
        if not player_name or not prop_type or line is None:
            continue
        
        # Use game_id, home_team, away_team for matching
        game_id = prop.get("game_id", "")
        home_team = prop.get("home_team", "")
        away_team = prop.get("away_team", "")
        
        # Key: (game_id, normalized_player, prop_type, line)
        norm_player = _normalize_player_name(player_name)
        key = (game_id, norm_player, prop_type, float(line))
        
        if key not in combined:
            combined[key] = {
                "game_id": game_id,
                "player_name": player_name,
                "norm_player": norm_player,
                "prop_type": prop_type,
                "line": float(line),
                "home_team": home_team,
                "away_team": away_team,
                "over_odds": None,
                "under_odds": None,
                "bookmaker": prop.get("bookmaker", "")
            }
        
        # Add odds (API returns separate over/under entries)
        if prop.get("over_odds"):
            combined[key]["over_odds"] = prop.get("over_odds")
        if prop.get("under_odds"):
            combined[key]["under_odds"] = prop.get("under_odds")
        if prop.get("over_line"):
            combined[key]["line"] = float(prop.get("over_line"))
        if prop.get("under_line"):
            combined[key]["line"] = float(prop.get("under_line"))
    
    return combined


def _match_player_props(
    db: DatabaseManager,
    sport: str,
    date: str,
    api_props: List[Dict[str, Any]]
) -> int:
    """
    Match API props to database player_props and update betting lines.
    
    Args:
        db: Database manager
        sport: Sport name
        date: Date string
        api_props: List of props from API
        
    Returns:
        Number of props updated
    """
    conn = db.get_connection()
    cursor = conn.cursor()
    
    updated = 0
    
    # Combine over/under props
    combined_props = _combine_over_under_props(api_props)
    
    # Match each combined prop to database
    for key, api_prop in combined_props.items():
        api_game_id = api_prop["game_id"]
        home_team = api_prop["home_team"]
        away_team = api_prop["away_team"]
        norm_player = api_prop["norm_player"]
        prop_type = api_prop["prop_type"]
        line = api_prop["line"]
        
        # Find matching game in our database
        cursor.execute("""
            SELECT game_id, home_team, away_team FROM games 
            WHERE sport = ? AND date = ?
        """, (sport, date))
        
        matching_game_id = None
        for row in cursor.fetchall():
            game_id, db_home, db_away = row
            if _teams_match(home_team, db_home) and _teams_match(away_team, db_away):
                matching_game_id = game_id
                break
        
        if not matching_game_id:
            continue
        
        # Find matching player_props records
        cursor.execute("""
            SELECT prop_id, player_name, actual_value
            FROM player_props
            WHERE game_id = ? AND prop_type = ? AND sport = ?
        """, (matching_game_id, prop_type, sport))
        
        for row in cursor.fetchall():
            prop_id, db_player_name, actual_value = row
            db_norm_player = _normalize_player_name(db_player_name)
            
            # Check if players match (fuzzy match)
            if db_norm_player == norm_player or norm_player in db_norm_player or db_norm_player in norm_player:
                # Update this prop with betting lines
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
                        api_prop["over_odds"],
                        api_prop["under_odds"],
                        api_prop["bookmaker"],
                        prop_id
                    ))
                    updated += 1
                    if updated % 100 == 0:
                        conn.commit()
                        logger.info(f"  Updated {updated} props so far...")
                except Exception as e:
                    logger.error(f"Error updating prop {prop_id}: {e}")
                    continue
    
    conn.commit()
    return updated


def fetch_and_update_prop_lines(sport: str, dates: List[str]):
    """Fetch player prop lines from API and update database."""
    load_dotenv('.env')
    
    client = TheOddsAPIClient()
    if not client.api_key:
        logger.error("THE_ODDS_API_KEY not set; cannot fetch player prop lines")
        return
    
    db = DatabaseManager("data/sports_data.db")
    
    total_updated = 0
    
    for date in dates:
        logger.info(f"Fetching player prop lines for {sport} on {date}")
        
        # Fetch player props from The Odds API
        try:
            api_props = client.fetch_player_props(
                sport=sport,
                date=date,
                markets=list(PROP_TYPE_MAP.keys())
            )
            
            if not api_props:
                logger.info(f"No player props returned for {date}")
                continue
            
            logger.info(f"Fetched {len(api_props)} player props from API")
            
            # Match and update database
            updated = _match_player_props(db, sport, date, api_props)
            total_updated += updated
            
            logger.info(f"{date}: Updated {updated} player props with betting lines")
            
        except Exception as e:
            logger.error(f"Error processing {date}: {e}", exc_info=True)
            continue
    
    logger.info(f"✅ Done. Total updated: {total_updated}")


def _date_range(start_date: str, end_date: str) -> List[str]:
    """Generate list of dates between start and end."""
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    days = (end - start).days
    return [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days + 1)]


def main():
    parser = argparse.ArgumentParser(
        description="Fetch player prop betting lines from The Odds API"
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
    
    fetch_and_update_prop_lines(args.sport, dates)


if __name__ == "__main__":
    main()

