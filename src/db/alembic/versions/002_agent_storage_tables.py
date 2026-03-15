"""Agent Storage Tables — fact cache, execution audit, prediction ledger

Revision ID: 002_agent_storage
Revises: 001_hybrid_schema
Create Date: 2026-03-15

Adds three tables for the agent execution lifecycle:
- fact_snapshots: TTL-aware cache for provider results
- execution_runs: audit trail of every agent query
- predictions: ledger for backtesting and calibration
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_agent_storage'
down_revision = '001_hybrid_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- fact_snapshots ---
    op.create_table(
        'fact_snapshots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('slot_key', sa.String(), nullable=False),
        sa.Column('data_type', sa.String(), nullable=False),
        sa.Column('entity', sa.String(), nullable=False),
        sa.Column('league', sa.String(), nullable=False),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('confidence', sa.Float(), server_default='1.0'),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('quality_score', sa.Float(), server_default='0.0'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_fact_snap_lookup', 'fact_snapshots', ['slot_key', 'entity', 'league'])
    op.create_index('idx_fact_snap_expires', 'fact_snapshots', ['expires_at'])
    op.create_index('idx_fact_snap_entity', 'fact_snapshots', ['entity'])
    op.create_index('idx_fact_snap_slot_key', 'fact_snapshots', ['slot_key'])
    op.create_index(
        'idx_fact_snap_data_gin', 'fact_snapshots', ['data'],
        postgresql_using='gin',
    )

    # --- execution_runs ---
    op.create_table(
        'execution_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('query_text', sa.String(), nullable=False),
        sa.Column('understanding', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('plan', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('slots_requested', sa.Integer(), nullable=True),
        sa.Column('slots_filled', sa.Integer(), nullable=True),
        sa.Column('data_quality_score', sa.Float(), nullable=True),
        sa.Column('execution_mode', sa.String(), nullable=True),
        sa.Column('providers_used', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('errors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_exec_runs_created', 'execution_runs', ['created_at'])

    # --- predictions ---
    op.create_table(
        'predictions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('execution_run_id', sa.String(), nullable=True),
        sa.Column('game_id', sa.String(), nullable=True),
        sa.Column('league', sa.String(), nullable=False),
        sa.Column('prediction_type', sa.String(), nullable=False),
        sa.Column('prediction', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('market_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('data_quality_score', sa.Float(), nullable=True),
        sa.Column('outcome', sa.String(), nullable=True),
        sa.Column('settled_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['execution_run_id'], ['execution_runs.id']),
        sa.ForeignKeyConstraint(['game_id'], ['games.id']),
    )
    op.create_index('idx_predictions_created', 'predictions', ['created_at'])


def downgrade() -> None:
    op.drop_table('predictions')
    op.drop_table('execution_runs')
    op.drop_table('fact_snapshots')
