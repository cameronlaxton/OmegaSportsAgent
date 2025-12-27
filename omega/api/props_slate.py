"""
Props Slate Generator

Generates available player props with injury filtering.
Called by server.js to provide real-time filtered data.
"""

import json
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

sys.path.insert(0, '.')

from omega.data.injury_api import filter_available_players, get_injured_players

NBA_PROPS = [
    {"name": "Tyrese Haliburton", "player": "Tyrese Haliburton", "team": "IND", "team_full": "Indiana Pacers", "prop_type": "Assists", "line": 10.5, "direction": "Over", "projected": 12.1, "edge_pct": 8.2, "tier": "A", "odds": -115, "league": "NBA"},
    {"name": "Jayson Tatum", "player": "Jayson Tatum", "team": "BOS", "team_full": "Boston Celtics", "prop_type": "Points", "line": 27.5, "direction": "Over", "projected": 30.2, "edge_pct": 7.5, "tier": "B", "odds": -110, "league": "NBA"},
    {"name": "Anthony Edwards", "player": "Anthony Edwards", "team": "MIN", "team_full": "Minnesota Timberwolves", "prop_type": "Points", "line": 25.5, "direction": "Over", "projected": 27.8, "edge_pct": 6.8, "tier": "B", "odds": -115, "league": "NBA"},
    {"name": "Shai Gilgeous-Alexander", "player": "Shai Gilgeous-Alexander", "team": "OKC", "team_full": "Oklahoma City Thunder", "prop_type": "Points", "line": 31.5, "direction": "Over", "projected": 33.4, "edge_pct": 6.5, "tier": "B", "odds": -110, "league": "NBA"},
    {"name": "Domantas Sabonis", "player": "Domantas Sabonis", "team": "SAC", "team_full": "Sacramento Kings", "prop_type": "Rebounds", "line": 12.5, "direction": "Over", "projected": 14.1, "edge_pct": 5.8, "tier": "B", "odds": -120, "league": "NBA"},
    {"name": "Nikola Jokic", "player": "Nikola Jokic", "team": "DEN", "team_full": "Denver Nuggets", "prop_type": "Assists", "line": 9.5, "direction": "Over", "projected": 10.8, "edge_pct": 5.5, "tier": "B", "odds": -110, "league": "NBA"},
    {"name": "LaMelo Ball", "player": "LaMelo Ball", "team": "CHA", "team_full": "Charlotte Hornets", "prop_type": "Points", "line": 22.5, "direction": "Over", "projected": 24.5, "edge_pct": 5.2, "tier": "B", "odds": -115, "league": "NBA"},
    {"name": "Trae Young", "player": "Trae Young", "team": "ATL", "team_full": "Atlanta Hawks", "prop_type": "Assists", "line": 11.5, "direction": "Under", "projected": 10.1, "edge_pct": 4.8, "tier": "C", "odds": -110, "league": "NBA"},
    {"name": "Luka Doncic", "player": "Luka Doncic", "team": "DAL", "team_full": "Dallas Mavericks", "prop_type": "Points", "line": 33.5, "direction": "Over", "projected": 35.8, "edge_pct": 6.2, "tier": "B", "odds": -115, "league": "NBA"},
    {"name": "Giannis Antetokounmpo", "player": "Giannis Antetokounmpo", "team": "MIL", "team_full": "Milwaukee Bucks", "prop_type": "Rebounds", "line": 11.5, "direction": "Over", "projected": 13.2, "edge_pct": 5.9, "tier": "B", "odds": -110, "league": "NBA"},
    {"name": "De'Aaron Fox", "player": "De'Aaron Fox", "team": "SAC", "team_full": "Sacramento Kings", "prop_type": "Points", "line": 25.5, "direction": "Over", "projected": 27.2, "edge_pct": 5.4, "tier": "B", "odds": -115, "league": "NBA"},
    {"name": "Ja Morant", "player": "Ja Morant", "team": "MEM", "team_full": "Memphis Grizzlies", "prop_type": "Points", "line": 24.5, "direction": "Over", "projected": 26.8, "edge_pct": 6.1, "tier": "B", "odds": -110, "league": "NBA"}
]

NFL_PROPS = [
    {"name": "Patrick Mahomes", "player": "Patrick Mahomes", "team": "KC", "team_full": "Kansas City Chiefs", "prop_type": "Pass Yards", "line": 275.5, "direction": "Over", "projected": 295.2, "edge_pct": 7.8, "tier": "A", "odds": -115, "league": "NFL"},
    {"name": "Josh Allen", "player": "Josh Allen", "team": "BUF", "team_full": "Buffalo Bills", "prop_type": "Pass TDs", "line": 2.5, "direction": "Over", "projected": 2.9, "edge_pct": 7.2, "tier": "B", "odds": -110, "league": "NFL"},
    {"name": "Derrick Henry", "player": "Derrick Henry", "team": "BAL", "team_full": "Baltimore Ravens", "prop_type": "Rush Yards", "line": 95.5, "direction": "Over", "projected": 108.4, "edge_pct": 6.5, "tier": "B", "odds": -115, "league": "NFL"},
    {"name": "Ja'Marr Chase", "player": "Ja'Marr Chase", "team": "CIN", "team_full": "Cincinnati Bengals", "prop_type": "Receiving Yards", "line": 85.5, "direction": "Over", "projected": 94.8, "edge_pct": 6.1, "tier": "B", "odds": -110, "league": "NFL"},
    {"name": "Travis Kelce", "player": "Travis Kelce", "team": "KC", "team_full": "Kansas City Chiefs", "prop_type": "Receptions", "line": 5.5, "direction": "Over", "projected": 6.4, "edge_pct": 5.8, "tier": "B", "odds": -115, "league": "NFL"},
    {"name": "Lamar Jackson", "player": "Lamar Jackson", "team": "BAL", "team_full": "Baltimore Ravens", "prop_type": "Rush Yards", "line": 55.5, "direction": "Over", "projected": 62.1, "edge_pct": 5.5, "tier": "B", "odds": -110, "league": "NFL"},
]

NCAAB_PROPS = [
    {"name": "Cooper Flagg", "player": "Cooper Flagg", "team": "DUKE", "team_full": "Duke Blue Devils", "prop_type": "Points", "line": 18.5, "direction": "Over", "projected": 21.2, "edge_pct": 7.5, "tier": "B", "odds": -115, "league": "NCAAB"},
    {"name": "Dylan Harper", "player": "Dylan Harper", "team": "RUTG", "team_full": "Rutgers Scarlet Knights", "prop_type": "Points", "line": 20.5, "direction": "Over", "projected": 23.1, "edge_pct": 6.8, "tier": "B", "odds": -110, "league": "NCAAB"},
    {"name": "Ace Bailey", "player": "Ace Bailey", "team": "RUTG", "team_full": "Rutgers Scarlet Knights", "prop_type": "Rebounds", "line": 7.5, "direction": "Over", "projected": 8.6, "edge_pct": 5.9, "tier": "B", "odds": -115, "league": "NCAAB"},
]

DEFAULT_PROPS = NBA_PROPS + NFL_PROPS + NCAAB_PROPS


def get_props_slate(prop_type: Optional[str] = None, league: str = "all") -> Dict[str, Any]:
    """
    Get available props filtered by injury status.
    
    Args:
        prop_type: Filter by prop type (Points, Assists, Rebounds)
        league: League filter - "all" returns all leagues, specific league (NBA/NFL/NCAAB) filters to that league only
    
    Returns:
        Dictionary with available props and injury info
    """
    if league.lower() == "all":
        base_props = DEFAULT_PROPS
        available_props = []
        nba_injured = get_injured_players("NBA")
        for prop in base_props:
            prop_league = prop.get("league", "NBA")
            if prop_league == "NBA":
                nba_available = filter_available_players([prop], "NBA")
                if nba_available:
                    available_props.append(prop)
            else:
                available_props.append(prop)
        injured = nba_injured
    else:
        base_props = [p for p in DEFAULT_PROPS if p.get("league", "NBA") == league.upper()]
        if league.upper() == "NBA":
            available_props = filter_available_players(base_props, league)
            injured = get_injured_players(league)
        else:
            available_props = base_props
            injured = {}
    
    filtered_out = []
    for prop in base_props:
        if prop not in available_props:
            name = prop.get("name", "")
            injury_info = injured.get(name.lower(), {})
            filtered_out.append({
                "player": name,
                "status": injury_info.get("status", "unavailable"),
                "injury": injury_info.get("injury_type", "")
            })
    
    if prop_type and prop_type.lower() != "all":
        available_props = [p for p in available_props if p["prop_type"].lower() == prop_type.lower()]
    
    for prop in available_props:
        if "name" in prop and "player" not in prop:
            prop["player"] = prop["name"]
    
    return {
        "props": available_props,
        "total": len(available_props),
        "filtered_out": filtered_out,
        "injury_filtered": len(filtered_out),
        "generated_at": datetime.now().isoformat()
    }


def get_players_to_watch(league: str = "NBA") -> Dict[str, Any]:
    """
    Get available players to watch filtered by injury status.
    """
    default_players = [
        {"name": "Tyrese Haliburton", "team": "Indiana Pacers", "position": "PG", "edge_pct": 8.2, "prop": "Assists O 10.5", "tier": "B"},
        {"name": "Jayson Tatum", "team": "Boston Celtics", "position": "SF", "edge_pct": 7.5, "prop": "Points O 27.5", "tier": "B"},
        {"name": "Anthony Edwards", "team": "Minnesota Timberwolves", "position": "SG", "edge_pct": 6.8, "prop": "Points O 25.5", "tier": "B"},
        {"name": "Shai Gilgeous-Alexander", "team": "Oklahoma City Thunder", "position": "PG", "edge_pct": 6.5, "prop": "Points O 31.5", "tier": "B"},
        {"name": "Domantas Sabonis", "team": "Sacramento Kings", "position": "C", "edge_pct": 5.8, "prop": "Rebounds O 12.5", "tier": "B"},
        {"name": "Nikola Jokic", "team": "Denver Nuggets", "position": "C", "edge_pct": 5.5, "prop": "Assists O 9.5", "tier": "B"}
    ]
    
    available = filter_available_players(default_players, league)
    
    injured = get_injured_players(league)
    unavailable = []
    for p in default_players:
        if p not in available:
            info = injured.get(p["name"].lower(), {})
            unavailable.append({
                "name": p["name"],
                "status": info.get("status", "unavailable"),
                "injury": info.get("injury_type", "")
            })
    
    return {
        "players": available,
        "unavailable": unavailable,
        "total_available": len(available),
        "generated_at": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", default="all", help="Prop type filter")
    parser.add_argument("--league", default="all", help="League filter (all, NBA, NFL, NCAAB)")
    parser.add_argument("--mode", default="props", choices=["props", "players"], help="Output mode")
    args = parser.parse_args()
    
    if args.mode == "players":
        result = get_players_to_watch()
    else:
        result = get_props_slate(args.type if args.type != "all" else None, args.league)
    
    print(json.dumps(result))
