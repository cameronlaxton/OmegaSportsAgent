#!/usr/bin/env python3
"""
Ingest player prop odds into player_props_odds.

Uses The Odds API to fetch player prop markets by date, matches them to local
games by date/home/away, and upserts lines into player_props_odds for
calibration against actuals in player_props.

Usage examples:
    python scripts/ingest_player_prop_odds.py --sport NBA --date 2024-01-15
    python scripts/ingest_player_prop_odds.py --sport NBA --start-date 2024-01-01 --end-date 2024-01-07

Requires env var THE_ODDS_API_KEY.
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
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

PLAYER_MARKETS = list(PROP_TYPE_MAP.keys())


def _fetch_events(session: requests.Session, client: TheOddsAPIClient, api_sport: str, date: str) -> List[Dict[str, Any]]:
    params = {
        "apiKey": client.api_key,
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "american",
    }

    # Try current odds first (works for live/upcoming); if historical is needed and current is empty, try historical.
    url_current = f"{client.BASE_URL}/sports/{api_sport}/odds"
    client._rate_limit()
    resp = session.get(url_current, params=params, timeout=30)

    if resp.status_code != 200:
        logger.debug(f"Current event fetch failed ({resp.status_code}): {resp.text[:200]}")
        resp_data = []
    else:
        try:
            data = resp.json()
            resp_data = data.get("data") if isinstance(data, dict) else data
        except Exception:
            resp_data = []

    if resp_data:
        return resp_data if isinstance(resp_data, list) else []

    # Historical attempt (paid tiers). If unavailable, it may return 401/403/404 or empty.
    hist_url = f"{client.BASE_URL}/historical/sports/{api_sport}/odds"
    params_hist = params | {"date": f"{date}T12:00:00Z"}
    client._rate_limit()
    hist_resp = session.get(hist_url, params=params_hist, timeout=30)
    if hist_resp.status_code != 200:
        logger.warning(f"Historical event fetch failed for {date} ({hist_resp.status_code}): {hist_resp.text[:200]}")
        return []

    try:
        data = hist_resp.json()
        if isinstance(data, dict):
            return data.get("data") or data.get("events") or []
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def _fetch_event_props(session: requests.Session, client: TheOddsAPIClient, api_sport: str, event_id: str, date: str) -> Optional[Dict[str, Any]]:
    params = {
        "apiKey": client.api_key,
        "regions": "us",
        "markets": ",".join(PLAYER_MARKETS),
        "oddsFormat": "american",
    }

    # Current event odds (works for live/upcoming games)
    url_current = f"{client.BASE_URL}/sports/{api_sport}/events/{event_id}/odds"
    client._rate_limit()
    resp = session.get(url_current, params=params, timeout=30)

    if resp.status_code == 200:
        try:
            data = resp.json()
            if data.get("bookmakers"):
                return data
        except Exception:
            pass

    # Historical fallback
    hist_url = f"{client.BASE_URL}/historical/sports/{api_sport}/events/{event_id}/odds"
    params_hist = params | {"date": f"{date}T12:00:00Z"}
    client._rate_limit()
    hist_resp = session.get(hist_url, params=params_hist, timeout=30)

    if hist_resp.status_code != 200:
        logger.debug(f"Prop fetch failed for event {event_id} ({hist_resp.status_code}): {hist_resp.text[:200]}")
        return None

    try:
        return hist_resp.json()
    except Exception:
        return None


def _normalize_team(name: str) -> str:
    return name.lower().replace('.', '').replace(' ', '') if name else ''


def _teams_match(a: str, b: str) -> bool:
    na, nb = _normalize_team(a), _normalize_team(b)
    return na and nb and (na in nb or nb in na)


def _resolve_game_id(conn, sport: str, date: str, home_team: str, away_team: str) -> Optional[str]:
    cursor = conn.execute(
        "SELECT game_id, home_team, away_team FROM games WHERE sport = ? AND date = ?",
        (sport, date),
    )
    for row in cursor.fetchall():
        if _teams_match(home_team, row[1]) and _teams_match(away_team, row[2]):
            return row[0]
    return None


def _parse_timestamp(commence_time: str) -> int:
    try:
        dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception:
        return int(datetime.now(tz=timezone.utc).timestamp())


def _date_range(start_date: str, end_date: str) -> List[str]:
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    days = (end - start).days
    return [(start + timedelta(days=i)).isoformat() for i in range(days + 1)]


def _combine_props(props: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge Over/Under outcomes into single records keyed by player/line/bookmaker."""
    grouped: Dict[Tuple[str, str, str, float, str], Dict[str, Any]] = {}
    for prop in props:
        api_prop_type = prop.get("prop_type", "")
        prop_type = PROP_TYPE_MAP.get(api_prop_type)
        if not prop_type:
            continue
        line = prop.get("line")
        if line is None:
            continue
        key = (
            prop.get("game_id"),
            prop.get("bookmaker"),
            prop.get("player_name"),
            prop_type,
            float(line),
        )
        record = grouped.setdefault(
            key,
            {
                "game_id": prop.get("game_id"),
                "bookmaker": prop.get("bookmaker"),
                "player_name": prop.get("player_name"),
                "prop_type": prop_type,
                "line": float(line),
                "over_odds": None,
                "under_odds": None,
                "home_team": prop.get("home_team", ""),
                "away_team": prop.get("away_team", ""),
                "timestamp": _parse_timestamp(prop.get("timestamp", "")),
            },
        )
        if "over_odds" in prop:
            record["over_odds"] = prop.get("over_odds")
        if "under_odds" in prop:
            record["under_odds"] = prop.get("under_odds")
    return list(grouped.values())


def ingest_player_prop_odds(sport: str, dates: List[str]):
    load_dotenv('.env')
    client = TheOddsAPIClient()
    if not client.api_key:
        logger.error("THE_ODDS_API_KEY not set; cannot ingest player prop odds")
        return

    db = DatabaseManager("data/sports_data.db")
    conn = db.get_connection()

    total_inserted = 0
    total_skipped = 0

    api_sport = TheOddsAPIClient.SPORT_MAPPING.get(sport.upper())
    if not api_sport:
        logger.error(f"Sport {sport} not supported")
        return

    session = requests.Session()

    for date in dates:
        logger.info(f"Fetching player prop odds for {sport} on {date}")

        # Step 1: get event list (h2h) for the date to obtain event IDs
        events = _fetch_events(session, client, api_sport, date)
        if not events:
            logger.info(f"No events returned for {date}")
            continue

        # Step 2: fetch player prop markets per event
        props: List[Dict[str, Any]] = []
        for ev in events:
            ev_props = _fetch_event_props(session, client, api_sport, ev.get("id"), date)
            if not ev_props:
                continue
            for bm in ev_props.get("bookmakers", []):
                for market in bm.get("markets", []):
                    if market.get("key") not in PLAYER_MARKETS:
                        continue
                    for outcome in market.get("outcomes", []):
                        prop = {
                            "game_id": ev.get("id"),
                            "home_team": ev.get("home_team"),
                            "away_team": ev.get("away_team"),
                            "player_name": outcome.get("description") or outcome.get("participant"),
                            "prop_type": market.get("key"),
                            "line": outcome.get("point"),
                            "bookmaker": bm.get("title"),
                            "timestamp": market.get("last_update"),
                        }
                        name = (outcome.get("name") or "").lower()
                        if "over" in name:
                            prop["over_odds"] = outcome.get("price")
                        if "under" in name:
                            prop["under_odds"] = outcome.get("price")
                        props.append(prop)

        if not props:
            logger.info(f"No player props returned for {date}")
            continue

        combined = _combine_props(props)
        inserted = 0
        skipped = 0

        for record in combined:
            game_id = _resolve_game_id(
                conn,
                sport,
                date,
                record.get("home_team", ""),
                record.get("away_team", ""),
            ) or record.get("game_id")
            if not game_id:
                skipped += 1
                continue

            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO player_props_odds
                        (game_id, bookmaker, player_name, prop_type, line, over_odds, under_odds, timestamp, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'the-odds-api')
                    """,
                    (
                        game_id,
                        record.get("bookmaker"),
                        record.get("player_name"),
                        record.get("prop_type"),
                        record.get("line"),
                        record.get("over_odds"),
                        record.get("under_odds"),
                        record.get("timestamp"),
                    ),
                )
                inserted += 1
            except Exception as exc:
                logger.error(f"Failed to insert prop for {game_id}: {exc}")
                skipped += 1

        conn.commit()
        total_inserted += inserted
        total_skipped += skipped
        logger.info(f"{date}: inserted {inserted}, skipped {skipped}")

    logger.info(f"✅ Done. Inserted: {total_inserted}, skipped: {total_skipped}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest player prop odds into SQLite")
    parser.add_argument("--sport", default="NBA", help="Sport (default: NBA)")
    parser.add_argument("--date", help="Single date (YYYY-MM-DD)")
    parser.add_argument("--start-date", dest="start_date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", dest="end_date", help="End date (YYYY-MM-DD)")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.date:
        dates = [args.date]
    else:
        start = args.start_date or datetime.utcnow().date().isoformat()
        end = args.end_date or start
        dates = _date_range(start, end)

    ingest_player_prop_odds(args.sport, dates)


if __name__ == "__main__":
    main()
