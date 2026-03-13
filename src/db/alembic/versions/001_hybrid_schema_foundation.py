"""Hybrid Schema Foundation - Box Score Architecture

Revision ID: 001_hybrid_schema
Revises: 3bde1e271421
Create Date: 2026-01-26

This migration replaces the old multi-sport schema with the new Hybrid Schema:
- Relational columns for universal data (IDs, Names, Dates)
- JSONB columns for sport-specific stats (Box Scores)
- Entity resolution support for handling scraper name variations

WARNING: This migration drops all existing tables and recreates them with the new schema.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_hybrid_schema'
down_revision = '3bde1e271421'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- DROP OLD SCHEMA ---
    # Drop tables in reverse dependency order from old schema
    op.drop_index('ix_sim_results_season', table_name='simulation_results', if_exists=True)
    op.drop_index('ix_sim_results_game', table_name='simulation_results', if_exists=True)
    op.drop_table('simulation_results', if_exists=True)
    op.drop_index('ix_odds_timestamp', table_name='betting_odds', if_exists=True)
    op.drop_index('ix_odds_game', table_name='betting_odds', if_exists=True)
    op.drop_table('betting_odds', if_exists=True)
    op.drop_index('ix_player_stats_team', table_name='player_season_stats', if_exists=True)
    op.drop_index('ix_player_stats_season', table_name='player_season_stats', if_exists=True)
    op.drop_table('player_season_stats', if_exists=True)
    op.drop_index('ix_games_season_week', table_name='games', if_exists=True)
    op.drop_index('ix_games_external', table_name='games', if_exists=True)
    op.drop_index('ix_games_date', table_name='games', if_exists=True)
    op.drop_table('games', if_exists=True)
    op.drop_index('ix_teams_league_season', table_name='teams', if_exists=True)
    op.drop_index('ix_teams_abbrev', table_name='teams', if_exists=True)
    op.drop_table('teams', if_exists=True)
    op.drop_index('ix_simulations_league_season', table_name='simulations', if_exists=True)
    op.drop_table('simulations', if_exists=True)
    op.drop_index('ix_players_name', table_name='players', if_exists=True)
    op.drop_index('ix_players_external', table_name='players', if_exists=True)
    op.drop_table('players', if_exists=True)
    op.drop_index('ix_calibration_version', table_name='model_calibration', if_exists=True)
    op.drop_index('ix_calibration_season', table_name='model_calibration', if_exists=True)
    op.drop_table('model_calibration', if_exists=True)
    op.drop_table('leagues', if_exists=True)

    # --- CREATE NEW HYBRID SCHEMA ---

    # --- ENUMS ---
    sport_enum = postgresql.ENUM('NBA', 'NFL', 'MLB', 'NHL', name='sport', create_type=False)
    market_status_enum = postgresql.ENUM('OPEN', 'CLOSED', 'SETTLED', name='marketstatus', create_type=False)

    op.execute("CREATE TYPE IF NOT EXISTS sport AS ENUM ('NBA', 'NFL', 'MLB', 'NHL')")
    op.execute("CREATE TYPE IF NOT EXISTS marketstatus AS ENUM ('OPEN', 'CLOSED', 'SETTLED')")

    # --- CORE ENTITIES ---

    # Leagues table
    op.create_table(
        'leagues',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('sport', sport_enum, nullable=False),
        sa.Column('current_season', sa.Integer()),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), server_default='{}'),
    )

    # Teams table
    op.create_table(
        'teams',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('league_id', sa.String(), sa.ForeignKey('leagues.id')),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('abbrev', sa.String(), index=True),
        sa.Column('aliases', postgresql.JSONB(astext_type=sa.Text()), server_default='[]'),
        sa.Column('wins', sa.Integer(), server_default='0'),
        sa.Column('losses', sa.Integer(), server_default='0'),
        sa.Column('season_stats', postgresql.JSONB(astext_type=sa.Text()), server_default='{}'),
    )

    # Players table
    op.create_table(
        'players',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('team_id', sa.String(), sa.ForeignKey('teams.id')),
        sa.Column('name', sa.String(), index=True),
        sa.Column('aliases', postgresql.JSONB(astext_type=sa.Text()), server_default='[]'),
        sa.Column('status', sa.String()),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), server_default='{}'),
    )

    # --- DATA LAKE (Box Scores) ---

    # Games table
    op.create_table(
        'games',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('league_id', sa.String(), sa.ForeignKey('leagues.id')),
        sa.Column('date', sa.DateTime(), index=True),
        sa.Column('status', market_status_enum, server_default='OPEN'),
        sa.Column('home_team_id', sa.String(), sa.ForeignKey('teams.id')),
        sa.Column('away_team_id', sa.String(), sa.ForeignKey('teams.id')),
        sa.Column('home_score', sa.Integer()),
        sa.Column('away_score', sa.Integer()),
        sa.Column('environment', postgresql.JSONB(astext_type=sa.Text()), server_default='{}'),
    )

    # Player Game Logs (THE BOX SCORE - most important table)
    op.create_table(
        'player_game_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('game_id', sa.String(), sa.ForeignKey('games.id')),
        sa.Column('player_id', sa.String(), sa.ForeignKey('players.id')),
        sa.Column('team_id', sa.String(), sa.ForeignKey('teams.id')),
        sa.Column('stats', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )

    # Create GIN index for JSONB searching inside stats
    op.create_index('idx_pgl_player_game', 'player_game_logs', ['player_id', 'game_id'])
    op.create_index('idx_pgl_stats_gin', 'player_game_logs', ['stats'], postgresql_using='gin')

    # --- MARKET & EXECUTION ---

    # Odds Snapshots (for CLV/Steam tracking)
    op.create_table(
        'odds_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('game_id', sa.String(), sa.ForeignKey('games.id')),
        sa.Column('bookmaker', sa.String()),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('markets', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )

    # Wagers (Betting Ledger)
    op.create_table(
        'wagers',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('game_id', sa.String(), sa.ForeignKey('games.id')),
        sa.Column('market_type', sa.String()),
        sa.Column('selection', sa.String()),
        sa.Column('price', sa.Integer()),
        sa.Column('units', sa.Float()),
        sa.Column('model_prob', sa.Float()),
        sa.Column('implied_prob', sa.Float()),
        sa.Column('result', sa.String()),
        sa.Column('closing_price', sa.Integer()),
        sa.Column('profit', sa.Float()),
    )

    # --- ENTITY RESOLUTION SUPPORT ---

    # Canonical Names (maps scraper aliases to UUIDs)
    op.create_table(
        'canonical_names',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('canonical_id', sa.String(), nullable=False, index=True),
        sa.Column('alias', sa.String(), nullable=False, index=True),
        sa.Column('source', sa.String()),
        sa.Column('confidence', sa.Float(), server_default='1.0'),
    )

    op.create_index('idx_canonical_alias_type', 'canonical_names', ['alias', 'entity_type'])


def downgrade() -> None:
    # Drop tables in reverse order of creation
    op.drop_table('canonical_names')
    op.drop_table('wagers')
    op.drop_table('odds_snapshots')
    op.drop_index('idx_pgl_stats_gin', table_name='player_game_logs')
    op.drop_index('idx_pgl_player_game', table_name='player_game_logs')
    op.drop_table('player_game_logs')
    op.drop_table('games')
    op.drop_table('players')
    op.drop_table('teams')
    op.drop_table('leagues')

    # Drop enums
    op.execute("DROP TYPE marketstatus")
    op.execute("DROP TYPE sport")
