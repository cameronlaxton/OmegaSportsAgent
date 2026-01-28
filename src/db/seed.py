"""
Seed script for OMEGA database with sample NFL/NBA data.
Uses the Hybrid JSONB schema for sport-specific stats.

Run with: python -m src.db.seed
"""

import sys
import os
import uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from src.db.database import get_db, check_connection
from src.db.schema import (
    League, Team, Player, PlayerSeasonStats, Game,
    Simulation, SimulationResult, BettingOdds, ModelCalibration,
    Sport, MarketStatus, SimulationStatus
)


def generate_id(prefix: str = "") -> str:
    """Generate a unique string ID."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}" if prefix else uuid.uuid4().hex


def seed_leagues(session):
    """Create NFL and NBA leagues using hybrid schema."""
    leagues_data = [
        {"id": "NFL", "sport": Sport.NFL, "current_season": 2024, "config": {
            "quarters": 4, "quarter_length": 15, "overtime": True,
            "possessions_per_game": 12, "home_advantage": 2.5
        }},
        {"id": "NBA", "sport": Sport.NBA, "current_season": 2024, "config": {
            "quarters": 4, "quarter_length": 12, "shot_clock": 24,
            "possessions_per_game": 100, "home_advantage": 3.0
        }},
        {"id": "MLB", "sport": Sport.MLB, "current_season": 2025, "config": {
            "innings": 9, "pitch_clock": True
        }},
        {"id": "NHL", "sport": Sport.NHL, "current_season": 2024, "config": {
            "periods": 3, "period_length": 20, "overtime": True
        }},
    ]

    for l in leagues_data:
        existing = session.query(League).filter_by(id=l["id"]).first()
        if not existing:
            league = League(
                id=l["id"],
                sport=l["sport"],
                current_season=l["current_season"],
                config=l["config"]
            )
            session.add(league)
    session.flush()
    print("Leagues seeded")
    return {l.id: l for l in session.query(League).all()}


def seed_nfl_teams(session, league_id: str):
    """Seed NFL teams with JSONB season_stats."""
    nfl_teams = [
        {"abbrev": "KC", "name": "Kansas City Chiefs", "stats": {
            "ppg": 28.5, "papg": 20.1, "off_rating": 118.0, "def_rating": 95.0,
            "pass_yds_pg": 265.2, "rush_yds_pg": 142.3
        }},
        {"abbrev": "BUF", "name": "Buffalo Bills", "stats": {
            "ppg": 30.2, "papg": 22.4, "off_rating": 122.0, "def_rating": 102.0,
            "pass_yds_pg": 285.1, "rush_yds_pg": 118.7
        }},
        {"abbrev": "DET", "name": "Detroit Lions", "stats": {
            "ppg": 33.1, "papg": 19.8, "off_rating": 126.0, "def_rating": 94.0,
            "pass_yds_pg": 248.9, "rush_yds_pg": 165.4
        }},
        {"abbrev": "PHI", "name": "Philadelphia Eagles", "stats": {
            "ppg": 27.4, "papg": 18.3, "off_rating": 115.0, "def_rating": 91.0,
            "pass_yds_pg": 232.1, "rush_yds_pg": 178.2
        }},
        {"abbrev": "BAL", "name": "Baltimore Ravens", "stats": {
            "ppg": 29.5, "papg": 19.4, "off_rating": 120.0, "def_rating": 93.0,
            "pass_yds_pg": 218.4, "rush_yds_pg": 192.7
        }},
        {"abbrev": "SF", "name": "San Francisco 49ers", "stats": {
            "ppg": 24.6, "papg": 21.2, "off_rating": 108.0, "def_rating": 98.0,
            "pass_yds_pg": 245.3, "rush_yds_pg": 128.6
        }},
        {"abbrev": "DAL", "name": "Dallas Cowboys", "stats": {
            "ppg": 21.8, "papg": 25.4, "off_rating": 98.0, "def_rating": 112.0,
            "pass_yds_pg": 258.2, "rush_yds_pg": 95.4
        }},
    ]

    for t in nfl_teams:
        team_id = f"NFL_{t['abbrev']}"
        existing = session.query(Team).filter_by(id=team_id).first()
        if not existing:
            team = Team(
                id=team_id,
                league_id=league_id,
                full_name=t["name"],
                abbrev=t["abbrev"],
                wins=0,
                losses=0,
                aliases=[t["name"].split()[-1], t["abbrev"]],  # e.g., ["Chiefs", "KC"]
                season_stats=t["stats"]
            )
            session.add(team)
    session.flush()
    print("NFL teams seeded")


def seed_nba_teams(session, league_id: str):
    """Seed NBA teams with JSONB season_stats."""
    nba_teams = [
        {"abbrev": "BOS", "name": "Boston Celtics", "stats": {
            "off_rating": 120.5, "def_rating": 109.8, "pace": 99.2,
            "ppg": 118.3, "fg_pct": 0.485, "three_pt_pct": 0.385
        }},
        {"abbrev": "OKC", "name": "Oklahoma City Thunder", "stats": {
            "off_rating": 118.2, "def_rating": 107.4, "pace": 100.1,
            "ppg": 117.8, "fg_pct": 0.478, "three_pt_pct": 0.362
        }},
        {"abbrev": "CLE", "name": "Cleveland Cavaliers", "stats": {
            "off_rating": 122.1, "def_rating": 110.3, "pace": 98.4,
            "ppg": 120.5, "fg_pct": 0.492, "three_pt_pct": 0.378
        }},
        {"abbrev": "NYK", "name": "New York Knicks", "stats": {
            "off_rating": 117.3, "def_rating": 114.3, "pace": 99.0,
            "ppg": 115.2, "fg_pct": 0.468, "three_pt_pct": 0.358
        }},
        {"abbrev": "LAL", "name": "Los Angeles Lakers", "stats": {
            "off_rating": 115.8, "def_rating": 112.1, "pace": 101.2,
            "ppg": 116.4, "fg_pct": 0.475, "three_pt_pct": 0.345
        }},
        {"abbrev": "DEN", "name": "Denver Nuggets", "stats": {
            "off_rating": 116.4, "def_rating": 113.7, "pace": 97.8,
            "ppg": 113.8, "fg_pct": 0.488, "three_pt_pct": 0.365
        }},
        {"abbrev": "GSW", "name": "Golden State Warriors", "stats": {
            "off_rating": 114.9, "def_rating": 111.8, "pace": 100.5,
            "ppg": 114.2, "fg_pct": 0.472, "three_pt_pct": 0.382
        }},
        {"abbrev": "MIL", "name": "Milwaukee Bucks", "stats": {
            "off_rating": 118.7, "def_rating": 115.2, "pace": 99.3,
            "ppg": 117.5, "fg_pct": 0.485, "three_pt_pct": 0.368
        }},
    ]

    for t in nba_teams:
        team_id = f"NBA_{t['abbrev']}"
        existing = session.query(Team).filter_by(id=team_id).first()
        if not existing:
            team = Team(
                id=team_id,
                league_id=league_id,
                full_name=t["name"],
                abbrev=t["abbrev"],
                wins=0,
                losses=0,
                aliases=[t["name"].split()[-1], t["abbrev"]],
                season_stats=t["stats"]
            )
            session.add(team)
    session.flush()
    print("NBA teams seeded")


def seed_nfl_players(session, league_id: str):
    """Seed NFL players with JSONB details and season stats."""
    players_data = [
        {"name": "Patrick Mahomes", "pos": "QB", "team": "KC", "details": {
            "height": "6-3", "weight": 230, "draft_year": 2017, "draft_pick": 10
        }, "stats": {
            "pass_yds": 4183, "pass_td": 26, "int": 11, "rush_yds": 389,
            "passer_rating": 98.5, "fantasy_ppr": 352.8
        }},
        {"name": "Josh Allen", "pos": "QB", "team": "BUF", "details": {
            "height": "6-5", "weight": 237, "draft_year": 2018, "draft_pick": 7
        }, "stats": {
            "pass_yds": 3731, "pass_td": 28, "int": 6, "rush_yds": 531,
            "passer_rating": 105.2, "fantasy_ppr": 378.4
        }},
        {"name": "Jahmyr Gibbs", "pos": "RB", "team": "DET", "details": {
            "height": "5-11", "weight": 200, "draft_year": 2023, "draft_pick": 12
        }, "stats": {
            "rush_yds": 1412, "rush_td": 16, "rec_yds": 517, "rec": 52,
            "ypc": 5.8, "fantasy_ppr": 342.9
        }},
        {"name": "Saquon Barkley", "pos": "RB", "team": "PHI", "details": {
            "height": "6-0", "weight": 232, "draft_year": 2018, "draft_pick": 2
        }, "stats": {
            "rush_yds": 1838, "rush_td": 13, "rec_yds": 278, "rec": 33,
            "ypc": 5.5, "fantasy_ppr": 318.6
        }},
        {"name": "Ja'Marr Chase", "pos": "WR", "team": "CIN", "details": {
            "height": "6-0", "weight": 201, "draft_year": 2021, "draft_pick": 5
        }, "stats": {
            "rec_yds": 1612, "rec_td": 17, "rec": 117, "targets": 153,
            "ypr": 13.8, "fantasy_ppr": 401.2
        }},
    ]

    for p in players_data:
        player_id = generate_id("NFL_PLAYER")
        existing = session.query(Player).filter_by(name=p["name"]).first()
        if not existing:
            team_id = f"NFL_{p['team']}"
            player = Player(
                id=player_id,
                team_id=team_id,
                name=p["name"],
                status="ACTIVE",
                aliases=[p["name"].split()[-1]],  # Last name as alias
                details={**p["details"], "position": p["pos"]}
            )
            session.add(player)
            session.flush()

            # Add season stats
            stats = PlayerSeasonStats(
                player_id=player_id,
                team_id=team_id,
                season=2024,
                games_played=15,
                stats=p["stats"],
                fantasy_points={"ppr": p["stats"].get("fantasy_ppr", 0)}
            )
            session.add(stats)
    session.flush()
    print("NFL players seeded")


def seed_nba_players(session, league_id: str):
    """Seed NBA players with JSONB details and season stats."""
    players_data = [
        {"name": "Jayson Tatum", "pos": "SF", "team": "BOS", "details": {
            "height": "6-8", "weight": 210, "draft_year": 2017, "draft_pick": 3
        }, "stats": {
            "pts": 27.1, "reb": 8.4, "ast": 4.9, "stl": 1.1, "blk": 0.6,
            "fg_pct": 0.456, "three_pt_pct": 0.378, "mpg": 35.8, "usg_pct": 0.31
        }},
        {"name": "Shai Gilgeous-Alexander", "pos": "PG", "team": "OKC", "details": {
            "height": "6-6", "weight": 195, "draft_year": 2018, "draft_pick": 11
        }, "stats": {
            "pts": 31.2, "reb": 5.5, "ast": 6.1, "stl": 2.0, "blk": 0.9,
            "fg_pct": 0.535, "three_pt_pct": 0.345, "mpg": 34.2, "usg_pct": 0.34
        }},
        {"name": "Donovan Mitchell", "pos": "SG", "team": "CLE", "details": {
            "height": "6-1", "weight": 215, "draft_year": 2017, "draft_pick": 13
        }, "stats": {
            "pts": 24.2, "reb": 4.4, "ast": 4.6, "stl": 1.3, "blk": 0.3,
            "fg_pct": 0.469, "three_pt_pct": 0.385, "mpg": 33.4, "usg_pct": 0.29
        }},
        {"name": "Jalen Brunson", "pos": "PG", "team": "NYK", "details": {
            "height": "6-2", "weight": 190, "draft_year": 2018, "draft_pick": 33
        }, "stats": {
            "pts": 25.1, "reb": 3.2, "ast": 7.5, "stl": 0.9, "blk": 0.2,
            "fg_pct": 0.481, "three_pt_pct": 0.392, "mpg": 35.1, "usg_pct": 0.32
        }},
        {"name": "LeBron James", "pos": "SF", "team": "LAL", "details": {
            "height": "6-9", "weight": 250, "draft_year": 2003, "draft_pick": 1
        }, "stats": {
            "pts": 23.8, "reb": 7.8, "ast": 8.9, "stl": 1.0, "blk": 0.5,
            "fg_pct": 0.502, "three_pt_pct": 0.358, "mpg": 35.5, "usg_pct": 0.28
        }},
        {"name": "Stephen Curry", "pos": "PG", "team": "GSW", "details": {
            "height": "6-2", "weight": 185, "draft_year": 2009, "draft_pick": 7
        }, "stats": {
            "pts": 22.5, "reb": 4.8, "ast": 6.2, "stl": 0.8, "blk": 0.3,
            "fg_pct": 0.452, "three_pt_pct": 0.408, "mpg": 32.8, "usg_pct": 0.28
        }},
    ]

    for p in players_data:
        player_id = generate_id("NBA_PLAYER")
        existing = session.query(Player).filter_by(name=p["name"]).first()
        if not existing:
            team_id = f"NBA_{p['team']}"
            player = Player(
                id=player_id,
                team_id=team_id,
                name=p["name"],
                status="ACTIVE",
                aliases=[p["name"].split()[-1], p["name"].split()[0]],
                details={**p["details"], "position": p["pos"]}
            )
            session.add(player)
            session.flush()

            # Add season stats
            stats = PlayerSeasonStats(
                player_id=player_id,
                team_id=team_id,
                season=2024,
                games_played=30,
                stats=p["stats"],
                fantasy_points={}
            )
            session.add(stats)
    session.flush()
    print("NBA players seeded")


def run_seed():
    """Main seed function."""
    print("Checking database connection...")
    if not check_connection():
        print("Failed to connect to database")
        return False

    print("\nSeeding OMEGA database with Hybrid JSONB schema...")

    with get_db() as session:
        leagues = seed_leagues(session)

        nfl_id = "NFL"
        nba_id = "NBA"

        if nfl_id in leagues:
            seed_nfl_teams(session, nfl_id)
            seed_nfl_players(session, nfl_id)

        if nba_id in leagues:
            seed_nba_teams(session, nba_id)
            seed_nba_players(session, nba_id)

        session.commit()

    print("\nSeed data inserted successfully!")

    # Sample queries to verify
    print("\n=== Sample Queries (Hybrid Schema) ===")
    with get_db() as session:
        print("\nNFL Players with JSONB stats:")
        nfl_players = session.query(Player).filter(Player.id.like("NFL_PLAYER%")).limit(3).all()
        for p in nfl_players:
            stats = session.query(PlayerSeasonStats).filter_by(player_id=p.id, season=2024).first()
            if stats:
                pts = stats.stats.get("fantasy_ppr", 0)
                print(f"  {p.name} ({p.details.get('position', 'N/A')}): {pts} fantasy pts")

        print("\nNBA Players with JSONB stats:")
        nba_players = session.query(Player).filter(Player.id.like("NBA_PLAYER%")).limit(3).all()
        for p in nba_players:
            stats = session.query(PlayerSeasonStats).filter_by(player_id=p.id, season=2024).first()
            if stats:
                ppg = stats.stats.get("pts", 0)
                print(f"  {p.name} ({p.details.get('position', 'N/A')}): {ppg} PPG")

        print("\nTeams with JSONB season_stats:")
        teams = session.query(Team).limit(4).all()
        for t in teams:
            off_rtg = t.season_stats.get("off_rating", "N/A")
            print(f"  {t.full_name}: Off Rating = {off_rtg}")

    return True


if __name__ == '__main__':
    run_seed()
