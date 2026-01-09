"""
Configuration for Module 1: Edge Threshold Calibration
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Module1Config:
    """Configuration for edge threshold calibration."""

    # Thresholds to test (percent)
    thresholds: List[float] = None

    # Sports to include
    sports: List[str] = None

    # Bet types to test
    bet_types: List[str] = None

    # Backtest period
    start_year: int = 2020
    end_year: int = 2024

    # Simulation iterations per game
    iterations: int = 10000

    # Statistical confidence level
    confidence_level: float = 0.95

    def __post_init__(self):
        """Set defaults."""
        if self.thresholds is None:
            self.thresholds = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        if self.sports is None:
            self.sports = ["NBA", "NFL", "NCAAB", "NCAAF"]
        if self.bet_types is None:
            self.bet_types = ["moneyline", "spread", "total"]
