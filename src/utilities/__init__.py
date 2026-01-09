"""
OMEGA Utilities Package

This package provides utility modules for output formatting, data logging,
model auditing, and sandbox persistence.

Modules:
    - output_formatter: Generates standardized output tables and narrative structure
    - data_logging: File-based storage for simulation outputs and bet recommendations
    - model_audit: Computes Brier score, CLV, ROI, and drift flags
    - sandbox_persistence: Persistent bet tracking and backtesting
"""

from src.utilities.output_formatter import (
    format_full_suggested_bets_table,
    format_straight_bets_table,
    format_props_only_table,
    format_clv_tracking_table,
    format_rejected_bets_log,
    format_context_drivers_table,
    format_risk_stake_table,
    format_simulation_summary_table,
    format_narrative_analysis,
    format_full_output,
)

from src.utilities.data_logging import (
    get_log_directory,
    log_simulation_output,
    log_bet_recommendation,
    load_past_logs,
    export_bet_log_to_csv,
)

from src.utilities.model_audit import (
    brier_score,
    clv,
    drift_flags,
    run_model_health_check,
)

from src.utilities.sandbox_persistence import (
    OmegaCacheLogger,
)

__all__ = [
    "format_full_suggested_bets_table",
    "format_straight_bets_table",
    "format_props_only_table",
    "format_clv_tracking_table",
    "format_rejected_bets_log",
    "format_context_drivers_table",
    "format_risk_stake_table",
    "format_simulation_summary_table",
    "format_narrative_analysis",
    "format_full_output",
    "get_log_directory",
    "log_simulation_output",
    "log_bet_recommendation",
    "load_past_logs",
    "export_bet_log_to_csv",
    "brier_score",
    "clv",
    "drift_flags",
    "run_model_health_check",
    "OmegaCacheLogger",
]
