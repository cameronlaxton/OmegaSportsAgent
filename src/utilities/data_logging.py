"""
Bet recommendation and decision logging.

Writes structured JSONL log entries to disk for audit trails and backtesting.
Logs go to outputs/logs/bets/ (alongside outputs/recommendations/ used by BetRecorder).
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional


_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DEFAULT_LOG_DIR = os.path.join(_PROJECT_ROOT, "outputs", "logs", "bets")


def get_log_directory() -> str:
    """Return the default log directory, creating it if needed."""
    log_dir = os.path.abspath(_DEFAULT_LOG_DIR)
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def log_bet_recommendation(
    rec: Dict[str, Any],
    directory: Optional[str] = None,
) -> None:
    """Append a bet recommendation to a date-stamped log file.

    Args:
        rec: Recommendation dict to log.
        directory: Override log directory. Defaults to logs/bets/.
    """
    log_dir = directory or get_log_directory()
    os.makedirs(log_dir, exist_ok=True)
    filename = f"bets_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
    filepath = os.path.join(log_dir, filename)

    entry = {
        "logged_at": datetime.now().isoformat(),
        **rec,
    }
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")
