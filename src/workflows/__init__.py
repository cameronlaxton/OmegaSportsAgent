"""Workflow modules for automated bet generation."""

from src.workflows.morning_bets import (
    run_morning_workflow,
    generate_daily_picks,
    evaluate_game,
    format_output_for_github
)

__all__ = [
    'run_morning_workflow',
    'generate_daily_picks',
    'evaluate_game',
    'format_output_for_github'
]
