"""
Seed script for OMEGA database with sample NFL/NBA data.
Run with: python -m omega.db.seed
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, date
from decimal import Decimal
from omega.db.database import get_db, check_connection
from omega.db.models import (
    League, Team, Player, PlayerSeasonStats, Game,
    Simulation, SimulationResult, BettingOdds, ModelCalibration
)


def seed_leagues(session):
    """Create NFL and NBA leagues."""
    leagues = [
        League(name='NFL', sport='Football', season_year=2024),
        League(name='NBA', sport='Basketball', season_year=2024),
        League(name='MLB', sport='Baseball', season_year=2025),
        League(name='NHL', sport='Hockey', season_year=2024),
    ]
    for league in leagues:
        existing = session.query(League).filter_by(name=league.name, season_year=league.season_year).first()
        if not existing:
            session.add(league)
    session.flush()
    print("Leagues seeded")
    return {l.name: l for l in session.query(League).all()}


def seed_nfl_teams(session, nfl_league):
    """Seed NFL teams with real 2024 data."""
    nfl_teams = [
        {'abbrev': 'KC', 'name': 'Kansas City Chiefs', 'city': 'Kansas City', 'conf': 'AFC', 'div': 'West', 'ppg': 28.5, 'papg': 20.1},
        {'abbrev': 'BUF', 'name': 'Buffalo Bills', 'city': 'Buffalo', 'conf': 'AFC', 'div': 'East', 'ppg': 30.2, 'papg': 22.4},
        {'abbrev': 'DET', 'name': 'Detroit Lions', 'city': 'Detroit', 'conf': 'NFC', 'div': 'North', 'ppg': 33.1, 'papg': 19.8},
        {'abbrev': 'PHI', 'name': 'Philadelphia Eagles', 'city': 'Philadelphia', 'conf': 'NFC', 'div': 'East', 'ppg': 27.4, 'papg': 18.3},
        {'abbrev': 'MIN', 'name': 'Minnesota Vikings', 'city': 'Minneapolis', 'conf': 'NFC', 'div': 'North', 'ppg': 26.7, 'papg': 21.5},
        {'abbrev': 'DAL', 'name': 'Dallas Cowboys', 'city': 'Dallas', 'conf': 'NFC', 'div': 'East', 'ppg': 21.8, 'papg': 25.4},
        {'abbrev': 'WSH', 'name': 'Washington Commanders', 'city': 'Washington', 'conf': 'NFC', 'div': 'East', 'ppg': 25.1, 'papg': 23.7},
        {'abbrev': 'DEN', 'name': 'Denver Broncos', 'city': 'Denver', 'conf': 'AFC', 'div': 'West', 'ppg': 23.4, 'papg': 20.8},
        {'abbrev': 'SF', 'name': 'San Francisco 49ers', 'city': 'San Francisco', 'conf': 'NFC', 'div': 'West', 'ppg': 24.6, 'papg': 21.2},
        {'abbrev': 'BAL', 'name': 'Baltimore Ravens', 'city': 'Baltimore', 'conf': 'AFC', 'div': 'North', 'ppg': 29.5, 'papg': 19.4},
    ]
    
    for t in nfl_teams:
        existing = session.query(Team).filter_by(abbreviation=t['abbrev'], season=2024).first()
        if not existing:
            team = Team(
                league_id=nfl_league.league_id,
                abbreviation=t['abbrev'],
                full_name=t['name'],
                city=t['city'],
                conference=t['conf'],
                division=t['div'],
                season=2024,
                points_per_game=Decimal(str(t['ppg'])),
                points_allowed_per_game=Decimal(str(t['papg'])),
            )
            session.add(team)
    session.flush()
    print("NFL teams seeded")


def seed_nba_teams(session, nba_league):
    """Seed NBA teams with real 2024-25 data."""
    nba_teams = [
        {'abbrev': 'BOS', 'name': 'Boston Celtics', 'city': 'Boston', 'conf': 'East', 'off': 120.5, 'def': 109.8, 'pace': 99.2},
        {'abbrev': 'OKC', 'name': 'Oklahoma City Thunder', 'city': 'Oklahoma City', 'conf': 'West', 'off': 118.2, 'def': 107.4, 'pace': 100.1},
        {'abbrev': 'CLE', 'name': 'Cleveland Cavaliers', 'city': 'Cleveland', 'conf': 'East', 'off': 122.1, 'def': 110.3, 'pace': 98.4},
        {'abbrev': 'NYK', 'name': 'New York Knicks', 'city': 'New York', 'conf': 'East', 'off': 117.3, 'def': 114.3, 'pace': 99.0},
        {'abbrev': 'LAL', 'name': 'Los Angeles Lakers', 'city': 'Los Angeles', 'conf': 'West', 'off': 115.8, 'def': 112.1, 'pace': 101.2},
        {'abbrev': 'DEN', 'name': 'Denver Nuggets', 'city': 'Denver', 'conf': 'West', 'off': 116.4, 'def': 113.7, 'pace': 97.8},
        {'abbrev': 'GSW', 'name': 'Golden State Warriors', 'city': 'San Francisco', 'conf': 'West', 'off': 114.9, 'def': 111.8, 'pace': 100.5},
        {'abbrev': 'MIL', 'name': 'Milwaukee Bucks', 'city': 'Milwaukee', 'conf': 'East', 'off': 118.7, 'def': 115.2, 'pace': 99.3},
    ]
    
    for t in nba_teams:
        existing = session.query(Team).filter_by(abbreviation=t['abbrev'], season=2024).first()
        if not existing:
            team = Team(
                league_id=nba_league.league_id,
                abbreviation=t['abbrev'],
                full_name=t['name'],
                city=t['city'],
                conference=t['conf'],
                season=2024,
                off_rating=Decimal(str(t['off'])),
                def_rating=Decimal(str(t['def'])),
                pace=Decimal(str(t['pace'])),
            )
            session.add(team)
    session.flush()
    print("NBA teams seeded")


def seed_nfl_players(session, nfl_league):
    """Seed sample NFL players with stats."""
    players_data = [
        {'first': 'Patrick', 'last': 'Mahomes', 'pos': 'QB', 'team': 'KC', 
         'pass_yards': 4183, 'pass_td': 26, 'rush_yards': 389, 'fantasy': 352.8},
        {'first': 'Josh', 'last': 'Allen', 'pos': 'QB', 'team': 'BUF',
         'pass_yards': 3731, 'pass_td': 28, 'rush_yards': 531, 'fantasy': 378.4},
        {'first': 'Jahmyr', 'last': 'Gibbs', 'pos': 'RB', 'team': 'DET',
         'rush_yards': 1412, 'rush_td': 16, 'rec_yards': 517, 'receptions': 52, 'fantasy': 342.9},
        {'first': 'Saquon', 'last': 'Barkley', 'pos': 'RB', 'team': 'PHI',
         'rush_yards': 1838, 'rush_td': 13, 'rec_yards': 278, 'receptions': 33, 'fantasy': 318.6},
        {'first': 'Ja\'Marr', 'last': 'Chase', 'pos': 'WR', 'team': 'CIN',
         'rec_yards': 1612, 'rec_td': 17, 'receptions': 117, 'targets': 153, 'fantasy': 401.2},
        {'first': 'CeeDee', 'last': 'Lamb', 'pos': 'WR', 'team': 'DAL',
         'rec_yards': 1057, 'rec_td': 6, 'receptions': 85, 'targets': 118, 'fantasy': 215.7},
    ]
    
    for p in players_data:
        existing = session.query(Player).filter_by(first_name=p['first'], last_name=p['last']).first()
        if not existing:
            player = Player(
                league_id=nfl_league.league_id,
                first_name=p['first'],
                last_name=p['last'],
                position=p['pos'],
            )
            session.add(player)
            session.flush()
            
            team = session.query(Team).filter_by(abbreviation=p['team'], season=2024).first()
            if team:
                stats = PlayerSeasonStats(
                    player_id=player.player_id,
                    team_id=team.team_id,
                    season=2024,
                    games_played=15,
                    pass_yards=p.get('pass_yards', 0),
                    pass_touchdowns=p.get('pass_td', 0),
                    rush_yards=p.get('rush_yards', 0),
                    rush_touchdowns=p.get('rush_td', 0),
                    receiving_yards=p.get('rec_yards', 0),
                    receiving_touchdowns=p.get('rec_td', 0),
                    receptions=p.get('receptions', 0),
                    targets=p.get('targets', 0),
                    fantasy_points_ppr=Decimal(str(p.get('fantasy', 0))),
                )
                session.add(stats)
    session.flush()
    print("NFL players seeded")


def seed_nba_players(session, nba_league):
    """Seed sample NBA players with stats."""
    players_data = [
        {'first': 'Jayson', 'last': 'Tatum', 'pos': 'SF', 'team': 'BOS',
         'ppg': 27.1, 'rpg': 8.4, 'apg': 4.9, 'fg_pct': 0.456, 'mpg': 35.8},
        {'first': 'Shai', 'last': 'Gilgeous-Alexander', 'pos': 'PG', 'team': 'OKC',
         'ppg': 31.2, 'rpg': 5.5, 'apg': 6.1, 'fg_pct': 0.535, 'mpg': 34.2},
        {'first': 'Donovan', 'last': 'Mitchell', 'pos': 'SG', 'team': 'CLE',
         'ppg': 24.2, 'rpg': 4.4, 'apg': 4.6, 'fg_pct': 0.469, 'mpg': 33.4},
        {'first': 'Jalen', 'last': 'Brunson', 'pos': 'PG', 'team': 'NYK',
         'ppg': 25.1, 'rpg': 3.2, 'apg': 7.5, 'fg_pct': 0.481, 'mpg': 35.1},
        {'first': 'LeBron', 'last': 'James', 'pos': 'SF', 'team': 'LAL',
         'ppg': 23.8, 'rpg': 7.8, 'apg': 8.9, 'fg_pct': 0.502, 'mpg': 35.5},
    ]
    
    for p in players_data:
        existing = session.query(Player).filter_by(first_name=p['first'], last_name=p['last']).first()
        if not existing:
            player = Player(
                league_id=nba_league.league_id,
                first_name=p['first'],
                last_name=p['last'],
                position=p['pos'],
            )
            session.add(player)
            session.flush()
            
            team = session.query(Team).filter_by(abbreviation=p['team'], season=2024).first()
            if team:
                stats = PlayerSeasonStats(
                    player_id=player.player_id,
                    team_id=team.team_id,
                    season=2024,
                    games_played=30,
                    points=Decimal(str(p['ppg'])),
                    rebounds=Decimal(str(p['rpg'])),
                    assists=Decimal(str(p['apg'])),
                    field_goal_pct=Decimal(str(p['fg_pct'])),
                    minutes_per_game=Decimal(str(p['mpg'])),
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
    
    print("\nSeeding OMEGA database...")
    
    with get_db() as session:
        leagues = seed_leagues(session)
        
        nfl = leagues.get('NFL')
        nba = leagues.get('NBA')
        
        if nfl:
            seed_nfl_teams(session, nfl)
            seed_nfl_players(session, nfl)
        
        if nba:
            seed_nba_teams(session, nba)
            seed_nba_players(session, nba)
        
        session.commit()
    
    print("\nSeed data inserted successfully!")
    
    print("\n=== Sample Queries ===")
    with get_db() as session:
        print("\nNFL Players:")
        nfl_players = session.query(Player).join(League).filter(League.name == 'NFL').limit(5).all()
        for p in nfl_players:
            stats = session.query(PlayerSeasonStats).filter_by(player_id=p.player_id, season=2024).first()
            if stats:
                print(f"  {p.first_name} {p.last_name} ({p.position}): {stats.fantasy_points_ppr} fantasy pts")
        
        print("\nNBA Players:")
        nba_players = session.query(Player).join(League).filter(League.name == 'NBA').limit(5).all()
        for p in nba_players:
            stats = session.query(PlayerSeasonStats).filter_by(player_id=p.player_id, season=2024).first()
            if stats:
                print(f"  {p.first_name} {p.last_name} ({p.position}): {stats.points} PPG")
    
    return True


if __name__ == '__main__':
    run_seed()
