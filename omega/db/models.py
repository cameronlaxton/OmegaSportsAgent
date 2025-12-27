"""
SQLAlchemy ORM Models for OMEGA Sports Betting Platform.
Multi-sport support: NFL, NBA, MLB, NHL, CFB.
"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date,
    ForeignKey, Numeric, CheckConstraint, Index, JSON
)
from sqlalchemy.orm import relationship
from omega.db.database import Base


class League(Base):
    """Sports leagues (NFL, NBA, MLB, NHL, CFB)."""
    __tablename__ = 'leagues'
    
    league_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)
    sport = Column(String(50), nullable=False)
    season_year = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    teams = relationship("Team", back_populates="league")
    players = relationship("Player", back_populates="league")
    simulations = relationship("Simulation", back_populates="league")
    
    def __repr__(self):
        return f"<League(name='{self.name}', season={self.season_year})>"


class Team(Base):
    """Team/franchise data with season-specific info."""
    __tablename__ = 'teams'
    
    team_id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(Integer, ForeignKey('leagues.league_id'), nullable=False)
    abbreviation = Column(String(10), nullable=False)
    full_name = Column(String(100), nullable=False)
    city = Column(String(100))
    conference = Column(String(50))
    division = Column(String(50))
    season = Column(Integer, nullable=False)
    
    off_rating = Column(Numeric(6, 2))
    def_rating = Column(Numeric(6, 2))
    pace = Column(Numeric(6, 2))
    
    pass_yards_per_game = Column(Numeric(6, 2))
    rush_yards_per_game = Column(Numeric(6, 2))
    points_per_game = Column(Numeric(6, 2))
    points_allowed_per_game = Column(Numeric(6, 2))
    
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    ties = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    league = relationship("League", back_populates="teams")
    player_stats = relationship("PlayerSeasonStats", back_populates="team")
    home_games = relationship("Game", foreign_keys="Game.home_team_id", back_populates="home_team")
    away_games = relationship("Game", foreign_keys="Game.away_team_id", back_populates="away_team")
    
    __table_args__ = (
        Index('ix_teams_league_season', 'league_id', 'season'),
        Index('ix_teams_abbrev', 'abbreviation'),
    )
    
    def __repr__(self):
        return f"<Team(name='{self.full_name}', abbrev='{self.abbreviation}')>"


class Player(Base):
    """Player master data across all sports."""
    __tablename__ = 'players'
    
    player_id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(Integer, ForeignKey('leagues.league_id'), nullable=False)
    external_id = Column(String(50))
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    position = Column(String(20))
    height = Column(String(10))
    weight = Column(Integer)
    birth_date = Column(Date)
    college = Column(String(100))
    draft_year = Column(Integer)
    draft_round = Column(Integer)
    draft_pick = Column(Integer)
    status = Column(String(50), default='active')
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    league = relationship("League", back_populates="players")
    season_stats = relationship("PlayerSeasonStats", back_populates="player")
    
    __table_args__ = (
        Index('ix_players_name', 'last_name', 'first_name'),
        Index('ix_players_external', 'external_id'),
    )
    
    def __repr__(self):
        return f"<Player(name='{self.first_name} {self.last_name}', pos='{self.position}')>"


class PlayerSeasonStats(Base):
    """Player performance stats per season - multi-sport fields."""
    __tablename__ = 'player_season_stats'
    
    stat_id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey('players.player_id'), nullable=False)
    team_id = Column(Integer, ForeignKey('teams.team_id'), nullable=False)
    season = Column(Integer, nullable=False)
    
    games_played = Column(Integer, default=0)
    games_started = Column(Integer, default=0)
    
    pass_attempts = Column(Integer, default=0)
    pass_completions = Column(Integer, default=0)
    pass_yards = Column(Integer, default=0)
    pass_touchdowns = Column(Integer, default=0)
    interceptions = Column(Integer, default=0)
    passer_rating = Column(Numeric(6, 2))
    
    rush_attempts = Column(Integer, default=0)
    rush_yards = Column(Integer, default=0)
    rush_touchdowns = Column(Integer, default=0)
    yards_per_carry = Column(Numeric(5, 2))
    
    receptions = Column(Integer, default=0)
    targets = Column(Integer, default=0)
    receiving_yards = Column(Integer, default=0)
    receiving_touchdowns = Column(Integer, default=0)
    yards_per_reception = Column(Numeric(5, 2))
    
    points = Column(Numeric(7, 2), default=0)
    rebounds = Column(Numeric(5, 2), default=0)
    assists = Column(Numeric(5, 2), default=0)
    steals = Column(Numeric(5, 2), default=0)
    blocks = Column(Numeric(5, 2), default=0)
    field_goal_pct = Column(Numeric(5, 3))
    three_pt_pct = Column(Numeric(5, 3))
    free_throw_pct = Column(Numeric(5, 3))
    minutes_per_game = Column(Numeric(5, 2))
    
    fantasy_points_ppr = Column(Numeric(8, 2))
    fantasy_points_half_ppr = Column(Numeric(8, 2))
    fantasy_points_standard = Column(Numeric(8, 2))
    projected_fantasy_points = Column(Numeric(8, 2))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    player = relationship("Player", back_populates="season_stats")
    team = relationship("Team", back_populates="player_stats")
    
    __table_args__ = (
        Index('ix_player_stats_season', 'player_id', 'season'),
        Index('ix_player_stats_team', 'team_id', 'season'),
    )
    
    def __repr__(self):
        return f"<PlayerSeasonStats(player_id={self.player_id}, season={self.season})>"


class Game(Base):
    """Historical and simulated game results."""
    __tablename__ = 'games'
    
    game_id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(50))
    league_id = Column(Integer, ForeignKey('leagues.league_id'), nullable=False)
    home_team_id = Column(Integer, ForeignKey('teams.team_id'), nullable=False)
    away_team_id = Column(Integer, ForeignKey('teams.team_id'), nullable=False)
    season = Column(Integer, nullable=False)
    week = Column(Integer)
    game_date = Column(DateTime, nullable=False)
    venue = Column(String(200))
    
    home_score = Column(Integer)
    away_score = Column(Integer)
    is_completed = Column(Boolean, default=False)
    is_historical = Column(Boolean, default=True)
    
    opening_spread = Column(Numeric(5, 2))
    closing_spread = Column(Numeric(5, 2))
    opening_total = Column(Numeric(5, 2))
    closing_total = Column(Numeric(5, 2))
    home_ml_odds = Column(Integer)
    away_ml_odds = Column(Integer)
    
    weather_temp = Column(Integer)
    weather_wind = Column(Integer)
    weather_condition = Column(String(50))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    league = relationship("League")
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_games")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_games")
    simulation_results = relationship("SimulationResult", back_populates="game")
    betting_odds = relationship("BettingOdds", back_populates="game")
    
    __table_args__ = (
        Index('ix_games_date', 'game_date'),
        Index('ix_games_season_week', 'season', 'week'),
        Index('ix_games_external', 'external_id'),
    )
    
    def __repr__(self):
        return f"<Game(home={self.home_team_id} vs away={self.away_team_id}, date={self.game_date})>"


class Simulation(Base):
    """Metadata about Monte Carlo simulation runs."""
    __tablename__ = 'simulations'
    
    simulation_id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(Integer, ForeignKey('leagues.league_id'), nullable=False)
    season = Column(Integer, nullable=False)
    simulation_name = Column(String(200))
    simulation_type = Column(String(50))
    model_version = Column(String(50))
    num_iterations = Column(Integer, nullable=False)
    
    parameters_json = Column(JSON)
    
    status = Column(String(20), default='pending')
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    execution_time_seconds = Column(Numeric(10, 3))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    league = relationship("League", back_populates="simulations")
    results = relationship("SimulationResult", back_populates="simulation")
    
    __table_args__ = (
        Index('ix_simulations_league_season', 'league_id', 'season'),
    )
    
    def __repr__(self):
        return f"<Simulation(name='{self.simulation_name}', iterations={self.num_iterations})>"


class SimulationResult(Base):
    """Probability distributions from Monte Carlo simulations."""
    __tablename__ = 'simulation_results'
    
    result_id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(Integer, ForeignKey('simulations.simulation_id'), nullable=False)
    game_id = Column(Integer, ForeignKey('games.game_id'))
    home_team_id = Column(Integer, ForeignKey('teams.team_id'))
    away_team_id = Column(Integer, ForeignKey('teams.team_id'))
    season = Column(Integer, nullable=False)
    
    home_win_probability = Column(Numeric(6, 4), CheckConstraint('home_win_probability >= 0 AND home_win_probability <= 1'))
    away_win_probability = Column(Numeric(6, 4), CheckConstraint('away_win_probability >= 0 AND away_win_probability <= 1'))
    tie_probability = Column(Numeric(6, 4))
    
    expected_spread = Column(Numeric(6, 2))
    spread_std_dev = Column(Numeric(6, 2))
    cover_probability = Column(Numeric(6, 4))
    
    expected_total_points = Column(Numeric(6, 2))
    total_std_dev = Column(Numeric(6, 2))
    over_under_probability = Column(Numeric(6, 4))
    
    home_score_median = Column(Numeric(6, 2))
    home_score_mean = Column(Numeric(6, 2))
    home_score_p10 = Column(Numeric(6, 2))
    home_score_p25 = Column(Numeric(6, 2))
    home_score_p75 = Column(Numeric(6, 2))
    home_score_p90 = Column(Numeric(6, 2))
    
    away_score_median = Column(Numeric(6, 2))
    away_score_mean = Column(Numeric(6, 2))
    away_score_p10 = Column(Numeric(6, 2))
    away_score_p25 = Column(Numeric(6, 2))
    away_score_p75 = Column(Numeric(6, 2))
    away_score_p90 = Column(Numeric(6, 2))
    
    distribution_json = Column(JSON)
    
    edge_pct = Column(Numeric(6, 2))
    ev_pct = Column(Numeric(6, 2))
    confidence_tier = Column(String(5))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    simulation = relationship("Simulation", back_populates="results")
    game = relationship("Game", back_populates="simulation_results")
    home_team = relationship("Team", foreign_keys=[home_team_id])
    away_team = relationship("Team", foreign_keys=[away_team_id])
    
    __table_args__ = (
        Index('ix_sim_results_game', 'game_id'),
        Index('ix_sim_results_season', 'season'),
    )
    
    def __repr__(self):
        return f"<SimulationResult(home_win_prob={self.home_win_probability})>"


class BettingOdds(Base):
    """Historical and projected betting odds for analysis."""
    __tablename__ = 'betting_odds'
    
    odds_id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey('games.game_id'), nullable=False)
    sportsbook = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    home_ml = Column(Integer)
    away_ml = Column(Integer)
    spread = Column(Numeric(5, 2))
    spread_home_odds = Column(Integer)
    spread_away_odds = Column(Integer)
    total = Column(Numeric(5, 2))
    over_odds = Column(Integer)
    under_odds = Column(Integer)
    
    is_opening = Column(Boolean, default=False)
    is_closing = Column(Boolean, default=False)
    
    game = relationship("Game", back_populates="betting_odds")
    
    __table_args__ = (
        Index('ix_odds_game', 'game_id'),
        Index('ix_odds_timestamp', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<BettingOdds(game_id={self.game_id}, spread={self.spread})>"


class ModelCalibration(Base):
    """Model accuracy tracking and parameter tuning."""
    __tablename__ = 'model_calibration'
    
    calibration_id = Column(Integer, primary_key=True, autoincrement=True)
    season = Column(Integer, nullable=False)
    league_name = Column(String(50))
    model_version = Column(String(50), nullable=False)
    calibration_date = Column(DateTime, default=datetime.utcnow)
    
    win_prob_accuracy = Column(Numeric(6, 4))
    spread_mae = Column(Numeric(6, 2))
    spread_cover_accuracy = Column(Numeric(6, 4))
    total_mae = Column(Numeric(6, 2))
    over_under_accuracy = Column(Numeric(6, 4))
    
    roi_percent = Column(Numeric(8, 4))
    profitable_bets = Column(Integer)
    total_bets_backtested = Column(Integer)
    
    brier_score = Column(Numeric(8, 6))
    log_loss = Column(Numeric(8, 6))
    
    parameters_json = Column(JSON)
    notes = Column(Text)
    
    __table_args__ = (
        Index('ix_calibration_season', 'season'),
        Index('ix_calibration_version', 'model_version'),
    )
    
    def __repr__(self):
        return f"<ModelCalibration(version='{self.model_version}', accuracy={self.win_prob_accuracy})>"
