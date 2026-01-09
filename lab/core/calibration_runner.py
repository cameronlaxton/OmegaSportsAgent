#!/usr/bin/env python3
"""
Backtesting & Calibration Pipeline

Deterministic backtesting pipeline that:
1. Reads historical data from sports_data.db (no re-downloading)
2. Performs time-based train/test split (no data leakage)
3. Tunes model parameters (edge thresholds, variance scalars, Kelly policy)
4. Evaluates calibration quality (Brier score, reliability curves)
5. Outputs calibration pack for OmegaSportsAgent

Usage:
    # Run full calibration
    python -m core.calibration_runner \\
        --league NBA \\
        --start-date 2020-01-01 \\
        --end-date 2024-12-31 \\
        --train-split 0.7 \\
        --dry-run

    # Quick test run
    python -m core.calibration_runner \\
        --league NBA \\
        --start-date 2023-01-01 \\
        --end-date 2023-12-31 \\
        --dry-run

    # Generate calibration pack
    python -m core.calibration_runner \\
        --league NBA \\
        --start-date 2020-01-01 \\
        --end-date 2024-12-31 \\
        --output calibration_pack_nba_2024.json
"""

import argparse
import json
import logging
import math
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
from dataclasses import dataclass, asdict, field

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db_manager import DatabaseManager
from core.calibration_diagnostics import analyze_edge_correlation
from core.calibration import (
    apply_platt,
    calibrate_probabilities_platt,
    shrink_toward_market
)
from core.simulation_framework import SimulationFramework, ExperimentConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CalibrationMetrics:
    """Container for calibration metrics."""
    roi: float
    sharpe: float
    max_drawdown: float
    hit_rate: float
    total_bets: int
    winning_bets: int
    losing_bets: int
    push_bets: int
    total_staked: float
    total_profit: float
    brier_score: float
    log_loss: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class CalibrationPack:
    """Calibration pack output for OmegaSportsAgent."""
    version: str
    league: str
    generated_at: str
    backtest_period: Dict[str, str]
    train_period: Dict[str, str]
    test_period: Dict[str, str]
    edge_thresholds: Dict[str, float]
    variance_scalars: Dict[str, float]
    kelly_policy: Dict[str, Any]
    probability_transforms: Dict[str, Any]
    metrics: Dict[str, Any]
    reliability_bins: List[Dict[str, Any]]
    diagnostics: Optional[Dict[str, Any]] = None
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def save(self, output_path: str):
        """Save to JSON file."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"✅ Calibration pack saved to: {output_path}")


class CalibrationRunner:
    """
    Main calibration runner that coordinates backtesting and parameter tuning.
    """
    
    # Market types to calibrate
    MARKET_TYPES = ['moneyline', 'spread', 'total']
    
    # Player prop types to calibrate (by sport)
    PLAYER_PROP_TYPES = {
        'NBA': ['points', 'rebounds', 'assists'],
        'NFL': ['passing_yards', 'rushing_yards', 'touchdowns'],
        'NCAAB': ['points', 'rebounds', 'assists'],
        'NCAAF': ['passing_yards', 'rushing_yards', 'touchdowns']
    }
    
    # Default parameters (initial guesses)
    DEFAULT_EDGE_THRESHOLDS = {
        'moneyline': 0.02,  # 2% edge required
        'spread': 0.03,     # 3% edge required
        'total': 0.03,      # 3% edge required
        'props': 0.04       # 4% edge required
    }
    
    DEFAULT_VARIANCE_SCALARS = {
        'NBA': 1.0,
        'NFL': 1.0,
        'global': 1.0
    }
    
    DEFAULT_KELLY_POLICY = {
        'method': 'fractional',
        'fraction': 0.25,      # Quarter Kelly
        'max_stake': 0.05,     # 5% of bankroll max
        'min_stake': 0.01,     # 1% of bankroll min
        'tier_multipliers': {
            'high_confidence': 1.0,
            'medium_confidence': 0.5,
            'low_confidence': 0.25
        }
    }
    
    def __init__(
        self,
        db_path: str = "data/sports_data.db",
        league: str = "NBA",
        start_date: str = "2020-01-01",
        end_date: str = "2024-12-31",
        train_split: float = 0.7,
        dry_run: bool = False
    ):
        """
        Initialize calibration runner.
        
        Args:
            db_path: Path to SQLite database
            league: League to calibrate (NBA, NFL, etc.)
            start_date: Start date for backtest window
            end_date: End date for backtest window
            train_split: Fraction of data for training (0.0-1.0)
            dry_run: If True, run without saving results
        """
        self.db = DatabaseManager(db_path)
        self.league = league
        self.start_date = start_date
        self.end_date = end_date
        self.train_split = train_split
        self.dry_run = dry_run
        self.simulation = SimulationFramework()
        self._model_cache: Dict[str, Dict[str, Any]] = {}
        
        # Calculate split date (time-based, no leakage)
        self.train_end_date = self._calculate_split_date()
        
        logger.info(f"Calibration Runner Initialized")
        logger.info(f"  League: {league}")
        logger.info(f"  Backtest Window: {start_date} to {end_date}")
        logger.info(f"  Train Split: {train_split:.1%}")
        logger.info(f"  Train Period: {start_date} to {self.train_end_date}")
        logger.info(f"  Test Period: {self.train_end_date} to {end_date}")
        logger.info(f"  Dry Run: {dry_run}")
    
    def _calculate_split_date(self) -> str:
        """
        Calculate train/test split date based on time (no leakage).
        
        Returns:
            Split date (YYYY-MM-DD)
        """
        from datetime import datetime, timedelta
        
        start = datetime.strptime(self.start_date, "%Y-%m-%d")
        end = datetime.strptime(self.end_date, "%Y-%m-%d")
        
        total_days = (end - start).days
        train_days = int(total_days * self.train_split)
        
        split_date = start + timedelta(days=train_days)
        
        return split_date.strftime("%Y-%m-%d")

    def _normal_cdf(self, value: float) -> float:
        """Standard normal CDF."""
        return 0.5 * (1.0 + math.erf(value / math.sqrt(2)))

    def _implied_prob_from_odds(self, odds: Optional[int]) -> Optional[float]:
        """Convert odds to implied probability if odds exist."""
        if odds is None:
            return None
        return self._american_to_prob(odds)

    def _ensure_model_predictions(self, market_data: List[Dict[str, Any]]) -> None:
        """Populate model cache for calibration records."""
        games_to_simulate = []
        for record in market_data:
            game_id = record.get("game_id")
            if not game_id or game_id in self._model_cache:
                continue
            games_to_simulate.append({
                "game_id": game_id,
                "home_team": record.get("home_team"),
                "away_team": record.get("away_team")
            })

        if not games_to_simulate:
            return

        config = ExperimentConfig(
            module_name="calibration_runner",
            sport=self.league,
            variance_scalar=self.DEFAULT_VARIANCE_SCALARS.get(self.league, 1.0)
        )
        results = self.simulation.run_simulation(config, games_to_simulate)
        for result in results.get("results", []):
            game_id = result.get("game_id")
            if game_id:
                self._model_cache[game_id] = result

    def _spread_cover_probability(self, mean_margin: float, line: float, sigma: float) -> float:
        """Estimate home cover probability from spread mean and line."""
        if sigma <= 0:
            return 0.5
        z = (mean_margin - line) / sigma
        return self._normal_cdf(z)

    def _total_over_probability(self, mean_total: float, line: float, sigma: float) -> float:
        """Estimate over probability from total mean and line."""
        if sigma <= 0:
            return 0.5
        z = (mean_total - line) / sigma
        return self._normal_cdf(z)
    
    def load_data(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Load game data from database for specified period.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of game records
        """
        logger.info(f"Loading data: {start_date} to {end_date}")
        
        games = self.db.get_games(
            sport=self.league,
            start_date=start_date,
            end_date=end_date,
            status='Final'  # Only completed games (capital F)
        )
        
        logger.info(f"  Loaded {len(games):,} games")
        
        return games
    
    def load_calibration_data(
        self,
        start_date: str,
        end_date: str,
        market_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Load calibration data (games + odds) for market accuracy analysis.
        
        Args:
            start_date: Start date
            end_date: End date
            market_type: Market type filter (optional)
            
        Returns:
            List of calibration records (game + market expectation)
        """
        logger.info(f"Loading calibration data: {start_date} to {end_date}")
        
        calibration_data = self.db.get_calibration_data(
            sport=self.league,
            start_date=start_date,
            end_date=end_date,
            market_type=market_type
        )
        
        logger.info(f"  Loaded {len(calibration_data):,} calibration records")
        
        return calibration_data
    
    def load_player_prop_calibration_data(
        self,
        start_date: str,
        end_date: str,
        prop_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Load player prop calibration data.
        
        Args:
            start_date: Start date
            end_date: End date
            prop_type: Filter by prop type (optional)
            
        Returns:
            List of player prop calibration records
        """
        logger.info(f"Loading player prop calibration data: {start_date} to {end_date}")
        
        prop_types = [prop_type] if prop_type else self.PLAYER_PROP_TYPES.get(self.league, [])
        all_props = []
        
        for pt in prop_types:
            props = self.db.get_player_prop_calibration_data(
                sport=self.league,
                start_date=start_date,
                end_date=end_date,
                prop_type=pt
            )
            # Add market_type field for consistency
            for prop in props:
                prop['market_type'] = f'player_prop_{pt}'
            all_props.extend(props)
        
        logger.info(f"  Loaded {len(all_props):,} player prop calibration records")
        
        return all_props
    
    def validate_split(self):
        """
        Validate train/test split has no temporal leakage.
        
        Raises:
            ValueError: If validation fails
        """
        logger.info("Validating train/test split...")
        
        train_data = self.load_data(self.start_date, self.train_end_date)
        test_data = self.load_data(self.train_end_date, self.end_date)
        
        if not train_data:
            raise ValueError(f"No training data found for period {self.start_date} to {self.train_end_date}")
        
        if not test_data:
            raise ValueError(f"No test data found for period {self.train_end_date} to {self.end_date}")
        
        # Check no temporal overlap
        train_max_date = max(game['date'] for game in train_data)
        test_min_date = min(game['date'] for game in test_data)
        
        if train_max_date >= test_min_date:
            logger.warning(f"⚠️  Potential temporal leakage detected:")
            logger.warning(f"    Train max date: {train_max_date}")
            logger.warning(f"    Test min date: {test_min_date}")
        
        logger.info(f"✅ Split validated:")
        logger.info(f"    Train: {len(train_data):,} games ({self.start_date} to {train_max_date})")
        logger.info(f"    Test:  {len(test_data):,} games ({test_min_date} to {self.end_date})")
        
        return True
    
    def tune_edge_thresholds(
        self,
        calibration_data: List[Dict[str, Any]],
        market_type: str
    ) -> float:
        """
        Tune edge threshold for a specific market type.
        
        Searches for threshold that maximizes risk-adjusted return (Sharpe ratio)
        while maintaining reasonable hit rate.
        
        Args:
            calibration_data: Calibration records
            market_type: Market type (moneyline, spread, total)
            
        Returns:
            Optimal edge threshold
        """
        logger.info(f"Tuning edge threshold for {market_type}...")
        
        # Filter to this market type
        market_data = [r for r in calibration_data if r['market_type'] == market_type]
        
        if not market_data:
            logger.warning(f"  No data for {market_type}, using default threshold")
            return self.DEFAULT_EDGE_THRESHOLDS.get(market_type, 0.03)
        
        # Grid search over threshold values
        thresholds = np.arange(0.01, 0.10, 0.005)  # 1% to 10% in 0.5% increments
        best_threshold = 0.03
        best_sharpe = -999
        
        for threshold in thresholds:
            metrics, _ = self._evaluate_threshold(market_data, threshold, market_type)
            
            # Require minimum 100 bets and 45% hit rate
            if metrics.total_bets >= 100 and metrics.hit_rate >= 0.45:
                if metrics.sharpe > best_sharpe:
                    best_sharpe = metrics.sharpe
                    best_threshold = threshold
        
        logger.info(f"  Optimal threshold: {best_threshold:.3f} (Sharpe: {best_sharpe:.2f})")
        
        return best_threshold
    
    def _generate_bets(
        self,
        market_data: List[Dict[str, Any]],
        threshold: float,
        market_type: str,
        probability_transforms: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate simulated bets for a specific edge threshold.
        
        Args:
            market_data: Market calibration data
            threshold: Edge threshold to evaluate
            market_type: Market type
            probability_transforms: Optional probability transforms to apply
            
        Returns:
            List of bet records
        """
        bets = []

        self._ensure_model_predictions(market_data)
        
        for record in market_data:
            # Calculate market implied probability
            if market_type == 'moneyline':
                home_odds = record.get('home_odds')
                away_odds = record.get('away_odds')

                if home_odds is None or away_odds is None:
                    continue
                
                model_output = self._model_cache.get(record.get("game_id"))
                if not model_output:
                    continue

                model_home_prob = model_output.get("home_win_prob")
                if model_home_prob is None:
                    continue
                model_away_prob = model_output.get("away_win_prob")
                if model_away_prob is None:
                    model_away_prob = 1.0 - model_home_prob

                # Convert American odds to implied probability
                market_home_prob = self._american_to_prob(home_odds)
                market_away_prob = self._american_to_prob(away_odds)
                
                # Determine winner
                home_score = record.get('home_score', 0)
                away_score = record.get('away_score', 0)
                home_won = home_score > away_score
                
                home_edge = model_home_prob - market_home_prob
                away_edge = model_away_prob - market_away_prob

                if home_edge >= away_edge:
                    edge = home_edge
                    model_prob = model_home_prob
                    market_prob = market_home_prob
                    outcome = 1.0 if home_won else 0.0
                    odds_prob = market_home_prob
                else:
                    edge = away_edge
                    model_prob = model_away_prob
                    market_prob = market_away_prob
                    outcome = 0.0 if home_won else 1.0
                    odds_prob = market_away_prob

                if edge >= threshold:
                    stake = 1.0
                    profit = stake * (1.0 / odds_prob - 1.0) if outcome == 1.0 else -stake

                    bets.append({
                        'edge': edge,
                        'prob': model_prob,
                        'model_prob': model_prob,
                        'market_prob': market_prob,
                        'outcome': outcome,
                        'stake': stake,
                        'profit': profit
                    })
            
            elif market_type == 'spread':
                market_result = self._get_market_prob_and_outcome(record, market_type)
                if not market_result:
                    continue
                
                # Extract values from record
                home_score = record.get('home_score', 0)
                away_score = record.get('away_score', 0)
                line = record.get('market_expectation') or record.get('spread_line', 0.0)
                
                margin = home_score - away_score
                covered = margin > line
                push = margin == line
                
                model_output = self._model_cache.get(record.get("game_id"))
                if not model_output:
                    continue

                mean_margin = model_output.get("spread_mean")
                if mean_margin is None:
                    continue

                variance_scalar = self.DEFAULT_VARIANCE_SCALARS.get(self.league, 1.0)
                sigma = 12.0 * variance_scalar
                model_home_prob = self._spread_cover_probability(mean_margin, line, sigma)
                model_away_prob = 1.0 - model_home_prob

                home_odds = record.get('home_odds')
                away_odds = record.get('away_odds')
                market_home_prob = self._implied_prob_from_odds(home_odds) or 0.5
                market_away_prob = self._implied_prob_from_odds(away_odds) or (1.0 - market_home_prob)

                home_edge = model_home_prob - market_home_prob
                away_edge = model_away_prob - market_away_prob

                if home_edge >= away_edge:
                    edge = home_edge
                    model_prob = model_home_prob
                    market_prob = market_home_prob
                    outcome = 0.5 if push else (1.0 if covered else 0.0)
                    odds_prob = market_home_prob
                else:
                    edge = away_edge
                    model_prob = model_away_prob
                    market_prob = market_away_prob
                    outcome = 0.5 if push else (0.0 if covered else 1.0)
                    odds_prob = market_away_prob
                
                if edge >= threshold:
                    stake = 1.0
                    if push:
                        profit = 0.0
                    else:
                        profit = stake * (1.0 / odds_prob - 1.0) if outcome == 1.0 else -stake
                    
                    bets.append({
                        'edge': edge,
                        'prob': model_prob,
                        'model_prob': model_prob,
                        'market_prob': market_prob,
                        'outcome': outcome,
                        'stake': stake,
                        'profit': profit
                    })

            elif market_type == 'total':
                line = record.get('market_expectation') or record.get('total_line')
                if line is None:
                    continue
                line = float(line)
                
                home_score = record.get('home_score', 0)
                away_score = record.get('away_score', 0)

                if home_score == 0 and away_score == 0:
                    continue

                total_score = home_score + away_score
                over_hit = total_score > line
                push = total_score == line

                model_output = self._model_cache.get(record.get("game_id"))
                if not model_output:
                    continue

                mean_total = model_output.get("total_mean")
                if mean_total is None:
                    continue

                variance_scalar = self.DEFAULT_VARIANCE_SCALARS.get(self.league, 1.0)
                sigma = 15.0 * variance_scalar
                model_over_prob = self._total_over_probability(mean_total, line, sigma)
                model_under_prob = 1.0 - model_over_prob

                over_odds = record.get('over_odds')
                under_odds = record.get('under_odds')
                market_over_prob = self._implied_prob_from_odds(over_odds) or 0.5
                market_under_prob = self._implied_prob_from_odds(under_odds) or (1.0 - market_over_prob)

                over_edge = model_over_prob - market_over_prob
                under_edge = model_under_prob - market_under_prob

                if over_edge >= under_edge:
                    edge = over_edge
                    model_prob = model_over_prob
                    market_prob = market_over_prob
                    outcome = 0.5 if push else (1.0 if over_hit else 0.0)
                    odds_prob = market_over_prob
                else:
                    edge = under_edge
                    model_prob = model_under_prob
                    market_prob = market_under_prob
                    outcome = 0.5 if push else (0.0 if over_hit else 1.0)
                    odds_prob = market_under_prob

                if edge >= threshold:
                    stake = 1.0
                    if push:
                        profit = 0.0
                    else:
                        profit = stake * (1.0 / odds_prob - 1.0) if outcome == 1.0 else -stake

                    bets.append({
                        'edge': edge,
                        'prob': model_prob,
                        'model_prob': model_prob,
                        'market_prob': market_prob,
                        'outcome': outcome,
                        'stake': stake,
                        'profit': profit
                    })
            
            elif market_type.startswith('player_prop_'):
                # Player prop over/under bet
                prop_type = market_type.replace('player_prop_', '')
                line = record.get('market_expectation')
                if line is None:
                    continue
                line = float(line)
                
                actual_value = record.get('actual_value')
                if actual_value is None:
                    continue
                actual_value = float(actual_value)
                
                over_odds = record.get('over_odds')
                under_odds = record.get('under_odds')
                if over_odds is None or under_odds is None:
                    continue
                
                # Determine outcome
                over_hit = actual_value > line
                push = actual_value == line
                
                # For player props, we need model predictions
                # For now, use a simplified approach: assume model predicts based on historical average
                # In production, this would come from the simulation framework
                # TODO: Integrate with simulation framework for player prop predictions
                
                # Market probabilities from odds
                market_over_prob = self._implied_prob_from_odds(over_odds) or 0.5
                market_under_prob = self._implied_prob_from_odds(under_odds) or (1.0 - market_over_prob)
                
                # Simplified model probability (in production, get from simulation)
                # For calibration, we'll use a naive approach: assume model is slightly better than market
                # This is a placeholder - should be replaced with actual model predictions
                model_over_prob = market_over_prob + 0.02  # Assume 2% edge potential
                model_over_prob = max(0.01, min(0.99, model_over_prob))  # Clamp
                model_under_prob = 1.0 - model_over_prob
                
                # Calculate edges
                over_edge = model_over_prob - market_over_prob
                under_edge = model_under_prob - market_under_prob
                
                # Choose side with higher edge
                if over_edge >= under_edge:
                    edge = over_edge
                    model_prob = model_over_prob
                    market_prob = market_over_prob
                    outcome = 0.5 if push else (1.0 if over_hit else 0.0)
                    odds_prob = market_over_prob
                else:
                    edge = under_edge
                    model_prob = model_under_prob
                    market_prob = market_under_prob
                    outcome = 0.5 if push else (0.0 if over_hit else 1.0)
                    odds_prob = market_under_prob
                
                if edge >= threshold:
                    stake = 1.0
                    if push:
                        profit = 0.0
                    else:
                        profit = stake * (1.0 / odds_prob - 1.0) if outcome == 1.0 else -stake
                    
                    bets.append({
                        'edge': edge,
                        'prob': model_prob,
                        'model_prob': model_prob,
                        'market_prob': market_prob,
                        'outcome': outcome,
                        'stake': stake,
                        'profit': profit,
                        'prop_type': prop_type
                    })
        
        return bets

    def _evaluate_threshold(
        self,
        market_data: List[Dict[str, Any]],
        threshold: float,
        market_type: str,
        probability_transforms: Optional[Dict[str, Any]] = None
    ) -> Tuple[CalibrationMetrics, List[Dict[str, Any]]]:
        """
        Evaluate a specific edge threshold.
        
        Args:
            market_data: Market calibration data
            threshold: Edge threshold to evaluate
            market_type: Market type
            probability_transforms: Optional probability transforms to apply
            
        Returns:
            Tuple of (calibration metrics, bet records)
        """
        bets = self._generate_bets(market_data, threshold, market_type, probability_transforms)
        
        return self._calculate_metrics(bets), bets
    
    def _american_to_prob(self, american_odds: int) -> float:
        """
        Convert American odds to implied probability.
        
        Args:
            american_odds: American odds (e.g., -110, +150)
            
        Returns:
            Implied probability (0.0-1.0)
        """
        if american_odds < 0:
            return abs(american_odds) / (abs(american_odds) + 100)
        else:
            return 100 / (american_odds + 100)

    def _get_market_prob_and_outcome(
        self,
        record: Dict[str, Any],
        market_type: str
    ) -> Optional[Tuple[float, float]]:
        """
        Get market implied probability and outcome for a given record.

        Returns:
            Tuple of (market_prob, outcome) or None if unavailable.
        """
        home_score = record.get('home_score', 0)
        away_score = record.get('away_score', 0)

        if market_type == 'moneyline':
            home_odds = record.get('home_odds')
            away_odds = record.get('away_odds')
            if home_odds is None or away_odds is None:
                return None
            market_prob = self._american_to_prob(home_odds)
            outcome = 1.0 if home_score > away_score else 0.0
            return market_prob, outcome

        if market_type == 'spread':
            home_odds = record.get('home_odds')
            line = record.get('market_expectation')
            if home_odds is None or line is None:
                return None
            margin = home_score - away_score
            market_prob = self._american_to_prob(home_odds)
            outcome = 1.0 if margin > line else 0.0
            return market_prob, outcome

        if market_type == 'total':
            over_odds = record.get('over_odds')
            line = record.get('market_expectation')
            if over_odds is None or line is None:
                return None
            total_score = home_score + away_score
            market_prob = self._american_to_prob(over_odds)
            outcome = 1.0 if total_score > line else 0.0
            return market_prob, outcome

        return None

    def _extract_probabilities(
        self,
        calibration_data: List[Dict[str, Any]],
        market_type: str
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Extract model, market probabilities and outcomes from calibration data.

        Returns:
            Tuple of (model_probs, market_probs, outcomes).
        """
        model_probs = []
        market_probs = []
        outcomes = []

        for record in calibration_data:
            if record.get('market_type') != market_type:
                continue

            market_result = self._get_market_prob_and_outcome(record, market_type)
            if not market_result:
                continue

            market_prob, outcome = market_result

            # Placeholder: model probabilities currently align with market-implied probs.
            model_prob = market_prob

            model_probs.append(model_prob)
            market_probs.append(market_prob)
            outcomes.append(outcome)

        return (
            np.array(model_probs, dtype=float),
            np.array(market_probs, dtype=float),
            np.array(outcomes, dtype=float)
        )
    
    def _calculate_metrics(self, bets: List[Dict[str, Any]]) -> CalibrationMetrics:
        """
        Calculate performance metrics for a set of bets.
        
        Args:
            bets: List of bet records
            
        Returns:
            Calibration metrics
        """
        if not bets:
            return CalibrationMetrics(
                roi=0.0,
                sharpe=0.0,
                max_drawdown=0.0,
                hit_rate=0.0,
                total_bets=0,
                winning_bets=0,
                losing_bets=0,
                push_bets=0,
                total_staked=0.0,
                total_profit=0.0,
                brier_score=0.0,
                log_loss=0.0
            )
        
        # Basic stats
        total_bets = len(bets)
        winning_bets = sum(1 for b in bets if b['outcome'] == 1.0)
        push_bets = sum(1 for b in bets if b['outcome'] == 0.5)
        losing_bets = sum(1 for b in bets if b['outcome'] == 0.0)
        total_staked = sum(b['stake'] for b in bets)
        total_profit = sum(b['profit'] for b in bets)
        
        # Performance metrics
        roi = (total_profit / total_staked) if total_staked > 0 else 0.0
        # Hit rate excludes pushes - it's wins / (wins + losses)
        decidable_bets = total_bets - push_bets
        hit_rate = winning_bets / decidable_bets if decidable_bets > 0 else 0.0
        
        # Risk metrics
        profits = [b['profit'] for b in bets]
        sharpe = (np.mean(profits) / np.std(profits)) if np.std(profits) > 0 else 0.0
        
        # Drawdown
        cumulative = np.cumsum(profits)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = running_max - cumulative
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0.0
        
        # Calibration metrics
        probs = [b['prob'] for b in bets]
        outcomes = [b['outcome'] for b in bets]
        
        brier_score = np.mean([(p - o) ** 2 for p, o in zip(probs, outcomes)])
        
        # Log loss (clip probabilities to avoid log(0))
        probs_clipped = np.clip(probs, 1e-15, 1 - 1e-15)
        log_loss = -np.mean([
            o * np.log(p) + (1 - o) * np.log(1 - p)
            for p, o in zip(probs_clipped, outcomes)
        ])
        
        return CalibrationMetrics(
            roi=roi,
            sharpe=sharpe,
            max_drawdown=max_drawdown,
            hit_rate=hit_rate,
            total_bets=total_bets,
            winning_bets=winning_bets,
            losing_bets=losing_bets,
            push_bets=push_bets,
            total_staked=total_staked,
            total_profit=total_profit,
            brier_score=brier_score,
            log_loss=log_loss
        )
    
    def calculate_reliability_bins(
        self,
        bets: List[Dict[str, Any]],
        n_bins: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Calculate reliability calibration bins.
        
        Bins predictions by probability and compares to empirical win rate.
        
        Args:
            bets: List of bet records
            n_bins: Number of probability bins
            
        Returns:
            List of bin statistics
        """
        if not bets:
            return []
        
        probs = np.array([b['prob'] for b in bets])
        outcomes = np.array([b['outcome'] for b in bets])
        
        bins = []
        bin_edges = np.linspace(0, 1, n_bins + 1)
        
        for i in range(n_bins):
            lower = bin_edges[i]
            upper = bin_edges[i + 1]
            
            mask = (probs >= lower) & (probs < upper)
            bin_bets = outcomes[mask]
            bin_probs = probs[mask]
            
            if len(bin_bets) > 0:
                bins.append({
                    'prob_range': f"{lower:.2f}-{upper:.2f}",
                    'predicted_prob': float(np.mean(bin_probs)),
                    'empirical_rate': float(np.mean(bin_bets)),
                    'count': int(len(bin_bets)),
                    'calibration_error': float(abs(np.mean(bin_probs) - np.mean(bin_bets)))
                })
        
        return bins

    def fit_probability_transforms(
        self,
        calibration_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Fit Platt scaling coefficients and shrinkage alphas per market type.

        Returns:
            Dictionary with per-market transform settings.
        """
        transforms = {}
        alpha_grid = np.arange(0.05, 0.26, 0.05)

        for market_type in self.MARKET_TYPES:
            model_probs, market_probs, outcomes = self._extract_probabilities(
                calibration_data,
                market_type
            )

            if model_probs.size == 0:
                transforms[market_type] = {
                    'method': 'platt+shrink',
                    'platt_coefficients': {'a': 1.0, 'b': 0.0},
                    'shrinkage_alpha': 0.1,
                    'notes': 'Insufficient data; defaults applied.'
                }
                continue

            calibrated_probs, coefficients = calibrate_probabilities_platt(
                model_probs,
                outcomes
            )

            best_alpha = 0.1
            best_brier = float('inf')

            for alpha in alpha_grid:
                shrunk_probs = shrink_toward_market(
                    calibrated_probs,
                    market_probs,
                    alpha
                )
                brier = float(np.mean((shrunk_probs - outcomes) ** 2))
                if brier < best_brier:
                    best_brier = brier
                    best_alpha = float(alpha)

            transforms[market_type] = {
                'method': 'platt+shrink',
                'platt_coefficients': coefficients,
                'shrinkage_alpha': best_alpha
            }

        return transforms
    
    def run_backtest(
        self
    ) -> Tuple[Dict[str, float], Dict[str, Any], List[Dict[str, Any]], Dict[str, Any], Optional[Dict[str, Any]]]:
        """
        Run full backtesting pipeline.
        
        Returns:
            Tuple of (edge_thresholds, metrics, reliability_bins, probability_transforms, diagnostics)
        """
        logger.info("\n" + "="*60)
        logger.info("STARTING BACKTEST CALIBRATION")
        logger.info("="*60)
        
        # Step 1: Validate split
        self.validate_split()
        
        # Step 2: Load training data
        logger.info("\nLoading training data...")
        train_calibration = self.load_calibration_data(
            self.start_date,
            self.train_end_date
        )
        
        # Load player prop calibration data
        train_prop_calibration = self.load_player_prop_calibration_data(
            self.start_date,
            self.train_end_date
        )

        # Step 3: Fit probability calibration transforms
        logger.info("\nFitting probability calibration transforms...")
        probability_transforms = self.fit_probability_transforms(train_calibration)
        
        # Step 4: Tune edge thresholds for game bets
        logger.info("\nTuning edge thresholds (game bets)...")
        edge_thresholds = {}
        
        for market_type in self.MARKET_TYPES:
            threshold = self.tune_edge_thresholds(train_calibration, market_type)
            edge_thresholds[market_type] = threshold
        
        # Step 4b: Tune edge thresholds for player props
        logger.info("\nTuning edge thresholds (player props)...")
        prop_types = self.PLAYER_PROP_TYPES.get(self.league, [])
        for prop_type in prop_types:
            market_type = f'player_prop_{prop_type}'
            prop_data = [p for p in train_prop_calibration if p.get('prop_type') == prop_type]
            if prop_data:
                threshold = self.tune_edge_thresholds(prop_data, market_type)
                edge_thresholds[market_type] = threshold
                logger.info(f"  {prop_type}: {threshold:.3f}")
            else:
                logger.warning(f"  No data for {prop_type}, using default threshold")
                edge_thresholds[market_type] = self.DEFAULT_EDGE_THRESHOLDS.get('props', 0.04)
        
        # Step 5: Evaluate on test set
        logger.info("\nEvaluating on test set...")
        test_calibration = self.load_calibration_data(
            self.train_end_date,
            self.end_date
        )
        test_prop_calibration = self.load_player_prop_calibration_data(
            self.train_end_date,
            self.end_date
        )
        
        # Collect all test bets using tuned thresholds
        all_bets = []
        
        # Game bets
        for market_type in self.MARKET_TYPES:
            market_data = [r for r in test_calibration if r['market_type'] == market_type]
            threshold = edge_thresholds[market_type]
            
            metrics, bets = self._evaluate_threshold(
                market_data,
                threshold,
                market_type,
                probability_transforms
            )
            all_bets.extend(bets)
            
            logger.info(f"\n{market_type.upper()} Results:")
            logger.info(f"  Threshold: {threshold:.3f}")
            logger.info(f"  Bets: {metrics.total_bets}")
            logger.info(f"  Hit Rate: {metrics.hit_rate:.1%}")
            logger.info(f"  ROI: {metrics.roi:.1%}")
            logger.info(f"  Sharpe: {metrics.sharpe:.2f}")
            logger.info(f"  Max Drawdown: {metrics.max_drawdown:.2f} units")
            logger.info(f"  Brier Score: {metrics.brier_score:.4f}")
        
        # Player props
        prop_types = self.PLAYER_PROP_TYPES.get(self.league, [])
        for prop_type in prop_types:
            market_type = f'player_prop_{prop_type}'
            prop_data = [p for p in test_prop_calibration if p.get('prop_type') == prop_type]
            if prop_data and market_type in edge_thresholds:
                threshold = edge_thresholds[market_type]
                
                metrics, bets = self._evaluate_threshold(
                    prop_data,
                    threshold,
                    market_type,
                    probability_transforms
                )
                all_bets.extend(bets)
                
                logger.info(f"\nPLAYER PROP ({prop_type.upper()}) Results:")
                logger.info(f"  Threshold: {threshold:.3f}")
                logger.info(f"  Bets: {metrics.total_bets}")
                logger.info(f"  Hit Rate: {metrics.hit_rate:.1%}")
                logger.info(f"  ROI: {metrics.roi:.1%}")
                logger.info(f"  Sharpe: {metrics.sharpe:.2f}")
                logger.info(f"  Max Drawdown: {metrics.max_drawdown:.2f} units")
                logger.info(f"  Brier Score: {metrics.brier_score:.4f}")
        
        # Step 6: Calculate reliability bins
        logger.info("\nCalculating reliability calibration...")
        reliability_bins = self.calculate_reliability_bins(all_bets)
        
        # Step 7: Aggregate metrics
        aggregate_metrics = self._calculate_metrics(all_bets)
        diagnostics = analyze_edge_correlation(all_bets)
        if diagnostics:
            logger.info("\nEdge correlation diagnostics:")
            logger.info(
                "  Spearman (edge vs outcome): %s",
                f"{diagnostics['spearman_correlation']:.3f}"
                if diagnostics.get('spearman_correlation') is not None
                else "n/a"
            )
            logger.info("  Bias: %s", diagnostics.get('bias_label', 'n/a'))
            logger.info("  Mean implied prob: %.3f", diagnostics.get('mean_implied_prob', 0.0))
            logger.info("  Mean outcome: %.3f", diagnostics.get('mean_outcome', 0.0))
        
        logger.info("\n" + "="*60)
        logger.info("BACKTEST COMPLETE")
        logger.info("="*60)
        logger.info(f"Total Bets: {aggregate_metrics.total_bets:,}")
        logger.info(f"Hit Rate: {aggregate_metrics.hit_rate:.1%}")
        logger.info(f"ROI: {aggregate_metrics.roi:.1%}")
        logger.info(f"Sharpe: {aggregate_metrics.sharpe:.2f}")
        logger.info(f"Max Drawdown: {aggregate_metrics.max_drawdown:.2f} units")
        logger.info(f"Brier Score: {aggregate_metrics.brier_score:.4f}")
        logger.info("="*60 + "\n")
        
        return edge_thresholds, aggregate_metrics.to_dict(), reliability_bins, probability_transforms, diagnostics
    
    def generate_calibration_pack(
        self,
        edge_thresholds: Dict[str, float],
        metrics: Dict[str, Any],
        reliability_bins: List[Dict[str, Any]],
        probability_transforms: Dict[str, Any],
        diagnostics: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None
    ) -> CalibrationPack:
        """
        Generate calibration pack for OmegaSportsAgent.
        
        Args:
            edge_thresholds: Tuned edge thresholds
            metrics: Performance metrics
            reliability_bins: Reliability calibration data
            output_path: Optional output file path
            
        Returns:
            CalibrationPack object
        """
        logger.info("Generating calibration pack...")
        
        pack = CalibrationPack(
            version="1.0.0",
            league=self.league,
            generated_at=datetime.now().isoformat(),
            backtest_period={
                'start': self.start_date,
                'end': self.end_date
            },
            train_period={
                'start': self.start_date,
                'end': self.train_end_date
            },
            test_period={
                'start': self.train_end_date,
                'end': self.end_date
            },
            edge_thresholds=edge_thresholds,
            variance_scalars=self.DEFAULT_VARIANCE_SCALARS,
            kelly_policy=self.DEFAULT_KELLY_POLICY,
            probability_transforms={
                'method': 'platt+shrink',
                'markets': probability_transforms
            },
            metrics=metrics,
            reliability_bins=reliability_bins,
            diagnostics=diagnostics,
            notes=[
                f"Calibrated on {self.league} historical data",
                f"Training period: {self.start_date} to {self.train_end_date}",
                f"Test period: {self.train_end_date} to {self.end_date}",
                f"Total test bets: {metrics.get('total_bets', 0):,}",
                f"Test ROI: {metrics.get('roi', 0):.1%}",
                f"Test Sharpe: {metrics.get('sharpe', 0):.2f}",
                "Ready for integration into OmegaSportsAgent"
            ]
        )
        
        if output_path:
            pack.save(output_path)
        
        return pack


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Backtesting & Calibration Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full calibration run
  python -m core.calibration_runner --league NBA --start-date 2020-01-01 --end-date 2024-12-31
  
  # Quick test run
  python -m core.calibration_runner --league NBA --start-date 2023-01-01 --end-date 2023-12-31 --dry-run
  
  # Generate calibration pack
  python -m core.calibration_runner --league NBA --output calibration_pack.json
        """
    )
    
    parser.add_argument(
        '--league',
        type=str,
        default='NBA',
        help='League to calibrate (NBA, NFL, etc.)'
    )
    
    parser.add_argument(
        '--start-date',
        type=str,
        default='2020-01-01',
        help='Backtest window start date (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--end-date',
        type=str,
        default='2024-12-31',
        help='Backtest window end date (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--train-split',
        type=float,
        default=0.7,
        help='Fraction of data for training (0.0-1.0, default: 0.7)'
    )
    
    parser.add_argument(
        '--db',
        type=str,
        default='data/sports_data.db',
        help='SQLite database path'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Output path for calibration pack JSON'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without saving results'
    )
    
    args = parser.parse_args()
    
    # Initialize runner
    runner = CalibrationRunner(
        db_path=args.db,
        league=args.league,
        start_date=args.start_date,
        end_date=args.end_date,
        train_split=args.train_split,
        dry_run=args.dry_run
    )
    
    # Run backtest
    edge_thresholds, metrics, reliability_bins, probability_transforms, diagnostics = runner.run_backtest()
    
    # Generate calibration pack
    if args.output or not args.dry_run:
        output_path = args.output or f"data/experiments/backtests/calibration_pack_{args.league.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        pack = runner.generate_calibration_pack(
            edge_thresholds,
            metrics,
            reliability_bins,
            probability_transforms,
            diagnostics,
            output_path
        )
        
        logger.info(f"\n✅ Calibration complete! Pack saved to: {output_path}")
    else:
        logger.info("\n✅ Dry run complete (no output saved)")


if __name__ == '__main__':
    main()
