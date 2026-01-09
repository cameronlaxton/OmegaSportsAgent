"""
Performance tracking and metrics calculation.
"""

import logging
from typing import Dict, List, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""

    hit_rate: float
    roi: float
    max_drawdown: float
    expected_value: float
    profit_factor: float
    win_count: int
    loss_count: int
    total_bets: int


class PerformanceTracker:
    """
    Tracks and calculates performance metrics.
    """

    def __init__(self):
        """Initialize performance tracker."""
        logger.info("PerformanceTracker initialized")

    def calculate_metrics(self, results: List[Dict[str, Any]]) -> PerformanceMetrics:
        """
        Calculate performance metrics.

        Args:
            results: List of bet results with 'outcome' (win/loss) and 'profit' fields

        Returns:
            PerformanceMetrics object
        """
        logger.info(f"Calculating metrics for {len(results)} results")
        
        if not results:
            return PerformanceMetrics(
                hit_rate=0.0,
                roi=0.0,
                max_drawdown=0.0,
                expected_value=0.0,
                profit_factor=0.0,
                win_count=0,
                loss_count=0,
                total_bets=0,
            )
        
        # Count wins and losses
        win_count = sum(1 for r in results if r.get('outcome') == 'win')
        loss_count = sum(1 for r in results if r.get('outcome') == 'loss')
        total_bets = len(results)
        
        # Calculate hit rate
        hit_rate = win_count / total_bets if total_bets > 0 else 0.0
        
        # Calculate profits
        total_profit = sum(r.get('profit', 0.0) for r in results)
        total_wagered = sum(r.get('stake', 1.0) for r in results)
        
        # Calculate ROI
        roi = total_profit / total_wagered if total_wagered > 0 else 0.0
        
        # Calculate max drawdown
        max_drawdown = self._calculate_max_drawdown(results)
        
        # Calculate expected value
        expected_value = total_profit / total_bets if total_bets > 0 else 0.0
        
        # Calculate profit factor
        total_wins = sum(r.get('profit', 0.0) for r in results if r.get('profit', 0.0) > 0)
        total_losses = abs(sum(r.get('profit', 0.0) for r in results if r.get('profit', 0.0) < 0))
        
        if total_losses > 0:
            profit_factor = total_wins / total_losses
        elif total_wins > 0:
            profit_factor = float('inf')
        else:
            profit_factor = 0.0
        
        return PerformanceMetrics(
            hit_rate=hit_rate,
            roi=roi,
            max_drawdown=max_drawdown,
            expected_value=expected_value,
            profit_factor=profit_factor,
            win_count=win_count,
            loss_count=loss_count,
            total_bets=total_bets,
        )
    
    def _calculate_max_drawdown(self, results: List[Dict[str, Any]]) -> float:
        """
        Calculate maximum drawdown from results.
        
        Args:
            results: List of bet results with 'profit' field
            
        Returns:
            Maximum drawdown as a decimal
        """
        if not results:
            return 0.0
        
        # Calculate cumulative profits
        cumulative = 0.0
        peak = 0.0
        max_drawdown = 0.0
        
        for result in results:
            cumulative += result.get('profit', 0.0)
            if cumulative > peak:
                peak = cumulative
            drawdown = (peak - cumulative) / peak if peak > 0 else 0.0
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return max_drawdown

    def calculate_roi(self, initial_bankroll: float, final_bankroll: float) -> float:
        """
        Calculate return on investment.

        Args:
            initial_bankroll: Starting bankroll
            final_bankroll: Ending bankroll

        Returns:
            ROI as decimal
        """
        if initial_bankroll == 0:
            return 0.0
        return (final_bankroll - initial_bankroll) / initial_bankroll

    def calculate_hit_rate(self, wins: int, total: int) -> float:
        """
        Calculate hit rate.

        Args:
            wins: Number of winning bets
            total: Total number of bets

        Returns:
            Hit rate as decimal
        """
        if total == 0:
            return 0.0
        return wins / total
