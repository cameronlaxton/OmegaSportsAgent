#!/usr/bin/env python3
"""
Unified Game Analysis Module

Comprehensive game analysis API that returns rich data including:
- Game info (teams, time, venue)
- Bets with actual data (spread, moneyline, total)
- Player props with projections
- Team historical performance (last 5 games)
- Player historical performance (last 5 games)
- Matchup analysis (pace, def rating, off rating)
- Narrative from Perplexity API
"""

import json
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ESPN_API_BASE = "https://site.api.espn.com/apis/site/v2/sports"

LEAGUE_PATHS = {
    "NBA": "basketball/nba",
    "NFL": "football/nfl",
    "MLB": "baseball/mlb",
    "NHL": "hockey/nhl",
    "NCAAB": "basketball/mens-college-basketball",
    "NCAAF": "football/college-football",
    "WNBA": "basketball/wnba"
}

REQUEST_TIMEOUT = 15
RATE_LIMIT_DELAY = 0.5
_last_request_time = 0


def _rate_limit():
    """Enforce rate limiting between requests."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - elapsed)
    _last_request_time = time.time()


def _make_espn_request(url: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """Make a request to the ESPN API."""
    _rate_limit()
    
    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()
        logger.warning(f"ESPN API returned {response.status_code}")
        return None
    except Exception as e:
        logger.error(f"ESPN API request failed: {e}")
        return None


def find_game_by_team(team_name: str, league: str) -> Optional[Dict[str, Any]]:
    """Find today's game for a given team."""
    league_path = LEAGUE_PATHS.get(league.upper(), f"basketball/{league.lower()}")
    today = datetime.now().strftime("%Y%m%d")
    
    url = f"{ESPN_API_BASE}/{league_path}/scoreboard"
    data = _make_espn_request(url, params={"dates": today})
    
    if not data:
        return None
    
    team_lower = team_name.lower()
    
    for event in data.get("events", []):
        competition = event.get("competitions", [{}])[0]
        competitors = competition.get("competitors", [])
        
        for comp in competitors:
            team = comp.get("team", {})
            if (team_lower in team.get("displayName", "").lower() or
                team_lower in team.get("abbreviation", "").lower() or
                team_lower in team.get("shortDisplayName", "").lower()):
                return _parse_game_event(event, league)
    
    return None


def find_game_by_id(game_id: str, league: str) -> Optional[Dict[str, Any]]:
    """Find a game by its ESPN event ID."""
    league_path = LEAGUE_PATHS.get(league.upper(), f"basketball/{league.lower()}")
    
    url = f"{ESPN_API_BASE}/{league_path}/summary"
    data = _make_espn_request(url, params={"event": game_id})
    
    if data:
        return _parse_game_summary(data, game_id, league)
    
    today = datetime.now().strftime("%Y%m%d")
    url = f"{ESPN_API_BASE}/{league_path}/scoreboard"
    data = _make_espn_request(url, params={"dates": today})
    
    if data:
        for event in data.get("events", []):
            if event.get("id") == game_id:
                return _parse_game_event(event, league)
    
    return None


def _parse_game_event(event: Dict, league: str) -> Dict[str, Any]:
    """Parse game event from scoreboard data."""
    competition = event.get("competitions", [{}])[0]
    competitors = competition.get("competitors", [])
    
    home_team = None
    away_team = None
    
    for comp in competitors:
        team = comp.get("team", {})
        team_info = {
            "id": team.get("id"),
            "name": team.get("displayName", ""),
            "abbreviation": team.get("abbreviation", ""),
            "short_name": team.get("shortDisplayName", ""),
            "logo": team.get("logo", ""),
            "score": comp.get("score", "0"),
            "record": comp.get("records", [{}])[0].get("summary", "") if comp.get("records") else ""
        }
        
        if comp.get("homeAway") == "home":
            home_team = team_info
        else:
            away_team = team_info
    
    odds_data = _parse_odds_from_competition(competition)
    
    return {
        "game_id": event.get("id", ""),
        "league": league.upper(),
        "name": event.get("name", ""),
        "short_name": event.get("shortName", ""),
        "date": event.get("date", ""),
        "status": event.get("status", {}).get("type", {}).get("description", ""),
        "status_detail": event.get("status", {}).get("type", {}).get("detail", ""),
        "venue": competition.get("venue", {}).get("fullName", ""),
        "venue_city": competition.get("venue", {}).get("address", {}).get("city", ""),
        "broadcast": competition.get("broadcasts", [{}])[0].get("names", []) if competition.get("broadcasts") else [],
        "home_team": home_team,
        "away_team": away_team,
        "odds": odds_data
    }


def _parse_odds_from_competition(competition: Dict) -> Dict[str, Any]:
    """Parse odds data from competition."""
    odds = competition.get("odds", [])
    if not odds:
        return {}
    
    odds_item = odds[0]
    
    return {
        "spread": odds_item.get("details", ""),
        "spread_value": odds_item.get("spread"),
        "over_under": odds_item.get("overUnder"),
        "home_ml": odds_item.get("homeTeamOdds", {}).get("moneyLine"),
        "away_ml": odds_item.get("awayTeamOdds", {}).get("moneyLine"),
        "provider": odds_item.get("provider", {}).get("name", "")
    }


def _parse_game_summary(data: Dict, game_id: str, league: str) -> Dict[str, Any]:
    """Parse detailed game summary data."""
    game_info = data.get("gameInfo", {})
    boxscore = data.get("boxscore", {})
    predictor = data.get("predictor", {})
    header = data.get("header", {})
    
    competitions = header.get("competitions", [{}])
    competition = competitions[0] if competitions else {}
    competitors = competition.get("competitors", [])
    
    home_team = None
    away_team = None
    
    for comp in competitors:
        team = comp.get("team", {})
        team_info = {
            "id": team.get("id"),
            "name": team.get("displayName", ""),
            "abbreviation": team.get("abbreviation", ""),
            "logo": team.get("logo", ""),
            "score": comp.get("score", "0"),
            "record": comp.get("record", [{}])[0].get("summary", "") if comp.get("record") else ""
        }
        
        if comp.get("homeAway") == "home":
            home_team = team_info
        else:
            away_team = team_info
    
    win_prob = {}
    if predictor:
        win_prob = {
            "home": predictor.get("homeTeam", {}).get("gameProjection"),
            "away": predictor.get("awayTeam", {}).get("gameProjection")
        }
    
    return {
        "game_id": game_id,
        "league": league.upper(),
        "name": header.get("gameNote", ""),
        "date": competition.get("date", ""),
        "status": competition.get("status", {}).get("type", {}).get("description", ""),
        "venue": game_info.get("venue", {}).get("fullName", ""),
        "venue_city": game_info.get("venue", {}).get("address", {}).get("city", ""),
        "attendance": game_info.get("attendance"),
        "home_team": home_team,
        "away_team": away_team,
        "win_probability": win_prob,
        "broadcast": competition.get("broadcasts", [{}])[0].get("names", []) if competition.get("broadcasts") else []
    }


def get_team_last_5_games(team_id: str, league: str) -> List[Dict[str, Any]]:
    """Get last 5 games for a team with scores and W/L."""
    league_path = LEAGUE_PATHS.get(league.upper())
    if not league_path:
        return []
    
    url = f"{ESPN_API_BASE}/{league_path}/teams/{team_id}/schedule"
    data = _make_espn_request(url)
    
    if not data:
        return []
    
    events = data.get("events", [])
    completed_games = []
    
    for event in events:
        competitions = event.get("competitions", [])
        if not competitions:
            continue
        
        competition = competitions[0]
        status = competition.get("status", {}).get("type", {}).get("name", "")
        
        if status != "STATUS_FINAL":
            continue
        
        competitors = competition.get("competitors", [])
        team_data = None
        opponent_data = None
        
        for comp in competitors:
            if comp.get("id") == team_id:
                team_data = comp
            else:
                opponent_data = comp
        
        if team_data and opponent_data:
            team_score = int(team_data.get("score", {}).get("value", 0) if isinstance(team_data.get("score"), dict) else team_data.get("score", 0))
            opp_score = int(opponent_data.get("score", {}).get("value", 0) if isinstance(opponent_data.get("score"), dict) else opponent_data.get("score", 0))
            
            completed_games.append({
                "date": event.get("date", ""),
                "opponent": opponent_data.get("team", {}).get("displayName", ""),
                "opponent_abbrev": opponent_data.get("team", {}).get("abbreviation", ""),
                "team_score": team_score,
                "opponent_score": opp_score,
                "result": "W" if team_score > opp_score else "L",
                "home_away": team_data.get("homeAway", "")
            })
    
    completed_games.sort(key=lambda x: x["date"], reverse=True)
    return completed_games[:5]


def get_team_stats(team_id: str, league: str) -> Dict[str, Any]:
    """Get team statistics for matchup analysis."""
    league_path = LEAGUE_PATHS.get(league.upper())
    if not league_path:
        return {}
    
    url = f"{ESPN_API_BASE}/{league_path}/teams/{team_id}/statistics"
    data = _make_espn_request(url)
    
    if not data:
        return {}
    
    stats = {}
    
    for split in data.get("splits", {}).get("categories", []):
        category_name = split.get("name", "")
        for stat in split.get("stats", []):
            stat_name = stat.get("name", "")
            stat_value = stat.get("value", 0)
            stats[f"{category_name}_{stat_name}"] = stat_value
    
    results = data.get("results", {})
    stats["record"] = results.get("displayValue", "")
    
    return stats


def get_matchup_analysis(home_team_id: str, away_team_id: str, league: str) -> Dict[str, Any]:
    """Generate matchup analysis with pace, ratings, etc."""
    home_stats = get_team_stats(home_team_id, league)
    away_stats = get_team_stats(away_team_id, league)
    
    analysis = {
        "home_stats": {},
        "away_stats": {},
        "comparison": {}
    }
    
    if league.upper() in ["NBA", "NCAAB", "WNBA"]:
        key_stats = ["pace", "offensiveRating", "defensiveRating", "pointsPerGame", "reboundsPerGame", "assistsPerGame"]
        stat_labels = {
            "pace": "Pace",
            "offensiveRating": "Off Rating",
            "defensiveRating": "Def Rating",
            "pointsPerGame": "PPG",
            "reboundsPerGame": "RPG",
            "assistsPerGame": "APG"
        }
    else:
        key_stats = ["pointsPerGame", "yardsPerGame", "turnoversPerGame"]
        stat_labels = {
            "pointsPerGame": "PPG",
            "yardsPerGame": "YPG",
            "turnoversPerGame": "TO/G"
        }
    
    for stat_key in key_stats:
        home_val = None
        away_val = None
        
        for key, val in home_stats.items():
            if stat_key.lower() in key.lower():
                home_val = val
                break
        
        for key, val in away_stats.items():
            if stat_key.lower() in key.lower():
                away_val = val
                break
        
        label = stat_labels.get(stat_key, stat_key)
        if home_val is not None:
            analysis["home_stats"][label] = round(home_val, 1) if isinstance(home_val, float) else home_val
        if away_val is not None:
            analysis["away_stats"][label] = round(away_val, 1) if isinstance(away_val, float) else away_val
        
        if home_val is not None and away_val is not None:
            diff = home_val - away_val
            analysis["comparison"][label] = {
                "home": round(home_val, 1) if isinstance(home_val, float) else home_val,
                "away": round(away_val, 1) if isinstance(away_val, float) else away_val,
                "diff": round(diff, 1) if isinstance(diff, float) else diff,
                "advantage": "home" if diff > 0 else "away" if diff < 0 else "even"
            }
    
    analysis["home_record"] = home_stats.get("record", "")
    analysis["away_record"] = away_stats.get("record", "")
    
    return analysis


def get_team_roster_with_stats(team_id: str, league: str) -> List[Dict[str, Any]]:
    """Get roster with player stats for last 5 games estimation."""
    league_path = LEAGUE_PATHS.get(league.upper())
    if not league_path:
        return []
    
    url = f"{ESPN_API_BASE}/{league_path}/teams/{team_id}/roster"
    data = _make_espn_request(url)
    
    if not data:
        return []
    
    players = []
    
    for athlete in data.get("athletes", []):
        player_info = {
            "id": athlete.get("id"),
            "name": athlete.get("displayName", ""),
            "position": athlete.get("position", {}).get("abbreviation", ""),
            "jersey": athlete.get("jersey", ""),
            "headshot": athlete.get("headshot", {}).get("href", "")
        }
        players.append(player_info)
    
    return players[:15]


def get_key_players_last_5(team_id: str, league: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Get key players with their last 5 games stats."""
    league_path = LEAGUE_PATHS.get(league.upper())
    if not league_path:
        return []
    
    url = f"{ESPN_API_BASE}/{league_path}/teams/{team_id}"
    data = _make_espn_request(url)
    
    if not data:
        return []
    
    team_data = data.get("team", {})
    athletes = team_data.get("athletes", [])
    
    players_with_stats = []
    
    for athlete in athletes[:limit]:
        player_id = athlete.get("id")
        player_name = athlete.get("displayName", "")
        
        player_stats_url = f"{ESPN_API_BASE}/{league_path}/athletes/{player_id}/gamelog"
        player_data = _make_espn_request(player_stats_url)
        
        last_5_games = []
        if player_data:
            events = player_data.get("events", [])[:5]
            
            for event in events:
                stats = event.get("stats", {})
                
                if league.upper() in ["NBA", "NCAAB", "WNBA"]:
                    game_stats = {
                        "date": event.get("eventDate", ""),
                        "opponent": event.get("opponent", {}).get("abbreviation", ""),
                        "pts": stats.get("points", 0),
                        "reb": stats.get("rebounds", 0),
                        "ast": stats.get("assists", 0),
                        "min": stats.get("minutes", "")
                    }
                else:
                    game_stats = {
                        "date": event.get("eventDate", ""),
                        "opponent": event.get("opponent", {}).get("abbreviation", ""),
                        "pass_yds": stats.get("passingYards", 0),
                        "rush_yds": stats.get("rushingYards", 0),
                        "rec_yds": stats.get("receivingYards", 0),
                        "tds": stats.get("touchdowns", 0)
                    }
                
                last_5_games.append(game_stats)
        
        players_with_stats.append({
            "id": player_id,
            "name": player_name,
            "position": athlete.get("position", {}).get("abbreviation", ""),
            "last_5_games": last_5_games
        })
    
    return players_with_stats


def get_injuries(team_abbrev: str, league: str) -> List[Dict[str, Any]]:
    """Get injury report for a team."""
    try:
        from src.data.injury_api import get_team_availability
        result = get_team_availability(team_abbrev, league)
        return result.get("all_injuries", [])
    except ImportError:
        return []
    except Exception as e:
        logger.warning(f"Error getting injuries: {e}")
        return []


def get_player_game_logs_for_game(home_team_id: str, away_team_id: str, league: str, max_players: int = 8) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch player game logs for both teams in a game.
    
    Args:
        home_team_id: ESPN team ID for home team
        away_team_id: ESPN team ID for away team
        league: League code (NBA, NFL, etc.)
        max_players: Maximum players per team to fetch logs for
    
    Returns:
        Dictionary with home_players and away_players lists containing game logs
    """
    from src.data.player_game_log import get_cached_player_game_log
    
    result = {
        "home_players": [],
        "away_players": []
    }
    
    home_roster = get_team_roster_with_stats(home_team_id, league)
    away_roster = get_team_roster_with_stats(away_team_id, league)
    
    for player in home_roster[:max_players]:
        player_name = player.get("name", "")
        if not player_name:
            continue
        
        try:
            game_logs = get_cached_player_game_log(player_name, league, n_games=5)
            if game_logs:
                result["home_players"].append({
                    "id": player.get("id"),
                    "name": player_name,
                    "position": player.get("position", ""),
                    "game_logs": game_logs
                })
        except Exception as e:
            logger.debug(f"Error getting game log for {player_name}: {e}")
    
    for player in away_roster[:max_players]:
        player_name = player.get("name", "")
        if not player_name:
            continue
        
        try:
            game_logs = get_cached_player_game_log(player_name, league, n_games=5)
            if game_logs:
                result["away_players"].append({
                    "id": player.get("id"),
                    "name": player_name,
                    "position": player.get("position", ""),
                    "game_logs": game_logs
                })
        except Exception as e:
            logger.debug(f"Error getting game log for {player_name}: {e}")
    
    return result


def get_odds_from_api(game_id: str, league: str) -> Dict[str, Any]:
    """Get odds data from The Odds API if available."""
    try:
        from src.data.odds_scraper import get_upcoming_games
        games = get_upcoming_games(league)
        
        for game in games:
            if game.get("game_id") == game_id:
                bookmakers = game.get("bookmakers", [])
                if bookmakers:
                    first_book = bookmakers[0]
                    markets = first_book.get("markets", {})
                    
                    spread_data = markets.get("spreads", [])
                    ml_data = markets.get("h2h", [])
                    totals_data = markets.get("totals", [])
                    
                    return {
                        "spread": spread_data,
                        "moneyline": ml_data,
                        "total": totals_data,
                        "provider": first_book.get("name", "")
                    }
        
        return {}
    except ImportError:
        return {}
    except Exception as e:
        logger.warning(f"Error getting odds: {e}")
        return {}


def get_player_props(game_id: str, league: str) -> List[Dict[str, Any]]:
    """Get player props for a game."""
    try:
        from src.data.odds_scraper import get_player_props as get_props
        return get_props(game_id, league)
    except ImportError:
        return []
    except Exception as e:
        logger.warning(f"Error getting player props: {e}")
        return []


def generate_narrative(home_team: str, away_team: str, spread: Optional[str] = None, total: Optional[float] = None) -> Dict[str, Any]:
    """Generate narrative using Perplexity API."""
    try:
        from src.api.perplexity_narrative import generate_game_narrative
        return generate_game_narrative(home_team, away_team, spread, total)
    except ImportError:
        return {"success": False, "error": "Perplexity module not available"}
    except Exception as e:
        logger.warning(f"Error generating narrative: {e}")
        return {"success": False, "error": str(e)}


def get_unified_game_analysis(team_name: Optional[str] = None, game_id: Optional[str] = None, league: str = "NBA") -> Dict[str, Any]:
    """
    Get comprehensive unified game analysis.
    
    Args:
        team_name: Team name to find game for (optional)
        game_id: ESPN game ID (optional)
        league: League code (NBA, NFL, etc.)
    
    Returns:
        Comprehensive game analysis data
    """
    league = league.upper()
    
    if game_id:
        game = find_game_by_id(game_id, league)
    elif team_name:
        game = find_game_by_team(team_name, league)
    else:
        return {"error": "Either team_name or game_id required"}
    
    if not game:
        return {"error": f"No game found for {'game_id: ' + game_id if game_id else 'team: ' + team_name}"}
    
    result = {
        "success": True,
        "generated_at": datetime.now().isoformat(),
        "game_info": {
            "game_id": game.get("game_id"),
            "league": league,
            "name": game.get("name"),
            "date": game.get("date"),
            "status": game.get("status"),
            "venue": game.get("venue"),
            "venue_city": game.get("venue_city", ""),
            "broadcast": game.get("broadcast", [])
        },
        "teams": {
            "home": game.get("home_team"),
            "away": game.get("away_team")
        },
        "betting": {
            "espn_odds": game.get("odds", {}),
            "odds_api": {},
            "player_props": []
        },
        "historical": {
            "home_last_5": [],
            "away_last_5": []
        },
        "player_performance": {
            "home_players": [],
            "away_players": []
        },
        "player_game_logs": {
            "home_players": [],
            "away_players": []
        },
        "matchup_analysis": {},
        "injuries": {
            "home": [],
            "away": []
        },
        "narrative": {}
    }
    
    home_team = game.get("home_team", {})
    away_team = game.get("away_team", {})
    home_id = home_team.get("id")
    away_id = away_team.get("id")
    home_abbrev = home_team.get("abbreviation", "")
    away_abbrev = away_team.get("abbreviation", "")
    
    game_id_val = game.get("game_id", "")
    odds_api_data = get_odds_from_api(game_id_val, league)
    if odds_api_data:
        result["betting"]["odds_api"] = odds_api_data
    
    props = get_player_props(game_id_val, league)
    if props:
        result["betting"]["player_props"] = props
    
    if home_id:
        result["historical"]["home_last_5"] = get_team_last_5_games(home_id, league)
    if away_id:
        result["historical"]["away_last_5"] = get_team_last_5_games(away_id, league)
    
    if home_id and away_id:
        result["matchup_analysis"] = get_matchup_analysis(home_id, away_id, league)
    
    if home_abbrev:
        result["injuries"]["home"] = get_injuries(home_abbrev, league)
    if away_abbrev:
        result["injuries"]["away"] = get_injuries(away_abbrev, league)
    
    if home_id and away_id:
        try:
            player_logs = get_player_game_logs_for_game(home_id, away_id, league, max_players=5)
            result["player_game_logs"] = player_logs
        except Exception as e:
            logger.warning(f"Error fetching player game logs: {e}")
    
    home_name = home_team.get("name", "")
    away_name = away_team.get("name", "")
    spread = game.get("odds", {}).get("spread", "")
    total = game.get("odds", {}).get("over_under")
    
    result["narrative"] = generate_narrative(home_name, away_name, spread, total)
    
    result["charts"] = {
        "home_scores": [g.get("team_score", 0) for g in result["historical"]["home_last_5"]],
        "home_results": [g.get("result", "") for g in result["historical"]["home_last_5"]],
        "away_scores": [g.get("team_score", 0) for g in result["historical"]["away_last_5"]],
        "away_results": [g.get("result", "") for g in result["historical"]["away_last_5"]],
        "home_win_pct": sum(1 for g in result["historical"]["home_last_5"] if g.get("result") == "W") / max(len(result["historical"]["home_last_5"]), 1) * 100,
        "away_win_pct": sum(1 for g in result["historical"]["away_last_5"] if g.get("result") == "W") / max(len(result["historical"]["away_last_5"]), 1) * 100
    }
    
    return result


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Unified Game Analysis")
    parser.add_argument("--team", help="Team name to search for")
    parser.add_argument("--game_id", help="ESPN game ID")
    parser.add_argument("--league", default="NBA", help="League code (NBA, NFL, etc.)")
    
    args = parser.parse_args()
    
    if not args.team and not args.game_id:
        print(json.dumps({"error": "Either --team or --game_id required"}))
        sys.exit(1)
    
    result = get_unified_game_analysis(
        team_name=args.team,
        game_id=args.game_id,
        league=args.league
    )
    
    print(json.dumps(result, indent=2, default=str))
