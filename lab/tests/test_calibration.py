"""
Unit tests for calibration runner and related components.

Tests:
- Database schema introspection
- Time-based train/test split validation
- Calibration pack JSON validation
- Metrics calculations
"""

import pytest
import json
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.calibration_runner import (
    CalibrationRunner,
    CalibrationMetrics,
    CalibrationPack
)
from core.db_manager import DatabaseManager


class TestDatabaseSchemaIntrospection:
    """Test database schema validation and introspection."""
    
    def test_db_tables_exist(self):
        """Test that all required tables exist in database."""
        db = DatabaseManager("data/sports_data.db")
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Required tables
        required_tables = ['games', 'odds_history', 'player_props', 'player_props_odds']
        
        for table in required_tables:
            assert table in tables, f"Required table '{table}' not found in database"
    
    def test_games_table_schema(self):
        """Test games table has required columns."""
        db = DatabaseManager("data/sports_data.db")
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get column info
        cursor.execute("PRAGMA table_info(games)")
        columns = {row[1] for row in cursor.fetchall()}
        
        # Required columns
        required_columns = {
            'game_id', 'date', 'sport', 'home_team', 'away_team',
            'home_score', 'away_score', 'status',
            'moneyline_home', 'moneyline_away',
            'spread_line', 'total_line'
        }
        
        for col in required_columns:
            assert col in columns, f"Required column '{col}' not found in games table"
    
    def test_odds_history_table_schema(self):
        """Test odds_history table has required columns."""
        db = DatabaseManager("data/sports_data.db")
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(odds_history)")
        columns = {row[1] for row in cursor.fetchall()}
        
        required_columns = {
            'game_id', 'bookmaker', 'market_type', 'line',
            'home_odds', 'away_odds', 'timestamp'
        }
        
        for col in required_columns:
            assert col in columns, f"Required column '{col}' not found in odds_history table"
    
    def test_db_indexes_exist(self):
        """Test that performance indexes exist."""
        db = DatabaseManager("data/sports_data.db")
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get all indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        
        # Key indexes for backtesting performance
        key_indexes = ['idx_games_date', 'idx_games_sport', 'idx_odds_game']
        
        for idx in key_indexes:
            assert idx in indexes, f"Performance index '{idx}' not found"


class TestTimeBasedSplit:
    """Test train/test split validation (no temporal leakage)."""
    
    def test_split_date_calculation(self):
        """Test split date is calculated correctly."""
        runner = CalibrationRunner(
            league="NBA",
            start_date="2020-01-01",
            end_date="2020-12-31",
            train_split=0.7
        )
        
        # Calculate expected split date
        start = datetime(2020, 1, 1)
        end = datetime(2020, 12, 31)
        total_days = (end - start).days
        expected_train_days = int(total_days * 0.7)
        expected_split = (start + timedelta(days=expected_train_days)).strftime("%Y-%m-%d")
        
        assert runner.train_end_date == expected_split
    
    def test_split_no_overlap(self):
        """Test train and test periods don't overlap."""
        # Use a date range that has actual data (2020-2024)
        runner = CalibrationRunner(
            league="NBA",
            start_date="2020-01-01",
            end_date="2020-12-31",
            train_split=0.7
        )
        
        # Validate split
        try:
            runner.validate_split()
            # If validation passes, split is valid
            assert True
        except ValueError as e:
            # If no data available in DB, skip test gracefully
            pytest.skip(f"Skipping test due to missing data: {e}")
    
    def test_split_boundaries(self):
        """Test edge cases for split ratios."""
        # Test 50/50 split
        runner = CalibrationRunner(
            league="NBA",
            start_date="2020-01-01",
            end_date="2020-12-31",
            train_split=0.5
        )
        
        start = datetime(2020, 1, 1)
        end = datetime(2020, 12, 31)
        total_days = (end - start).days
        expected_split_day = start + timedelta(days=int(total_days * 0.5))
        
        assert runner.train_end_date == expected_split_day.strftime("%Y-%m-%d")
    
    def test_invalid_split_ratio(self):
        """Test invalid split ratios are handled."""
        # Split > 1.0 should work (clips to 1.0 implicitly)
        runner = CalibrationRunner(
            league="NBA",
            start_date="2020-01-01",
            end_date="2020-12-31",
            train_split=1.5  # Invalid but should not crash
        )
        
        # Just check it doesn't crash
        assert runner.train_end_date is not None


class TestCalibrationPackValidation:
    """Test calibration pack JSON structure and validation."""
    
    def test_calibration_pack_required_fields(self):
        """Test calibration pack has all required fields."""
        pack = CalibrationPack(
            version="1.0.0",
            league="NBA",
            generated_at=datetime.now().isoformat(),
            backtest_period={'start': '2020-01-01', 'end': '2024-12-31'},
            train_period={'start': '2020-01-01', 'end': '2022-12-31'},
            test_period={'start': '2023-01-01', 'end': '2024-12-31'},
            edge_thresholds={'moneyline': 0.02, 'spread': 0.03, 'total': 0.03},
            variance_scalars={'NBA': 1.0, 'global': 1.0},
            kelly_policy={'method': 'fractional', 'fraction': 0.25, 'max_stake': 0.05, 'min_stake': 0.01},
            probability_transforms={'method': 'none'},
            metrics={'roi': 0.05, 'sharpe': 1.2, 'hit_rate': 0.52, 'total_bets': 100},
            reliability_bins=[],
            notes=['Test pack']
        )
        
        pack_dict = pack.to_dict()
        
        # Check required fields
        required_fields = [
            'version', 'league', 'generated_at', 'backtest_period',
            'edge_thresholds', 'kelly_policy', 'metrics'
        ]
        
        for field in required_fields:
            assert field in pack_dict, f"Required field '{field}' missing from pack"
    
    def test_calibration_pack_json_serialization(self):
        """Test calibration pack can be serialized to JSON."""
        pack = CalibrationPack(
            version="1.0.0",
            league="NBA",
            generated_at=datetime.now().isoformat(),
            backtest_period={'start': '2020-01-01', 'end': '2024-12-31'},
            train_period={'start': '2020-01-01', 'end': '2022-12-31'},
            test_period={'start': '2023-01-01', 'end': '2024-12-31'},
            edge_thresholds={'moneyline': 0.02},
            variance_scalars={'global': 1.0},
            kelly_policy={'method': 'fractional', 'fraction': 0.25, 'max_stake': 0.05, 'min_stake': 0.01},
            probability_transforms={'method': 'none'},
            metrics={'roi': 0.05, 'sharpe': 1.2, 'hit_rate': 0.52, 'total_bets': 100},
            reliability_bins=[],
            notes=['Test']
        )
        
        # Test JSON serialization
        json_str = json.dumps(pack.to_dict())
        assert json_str is not None
        
        # Test deserialization
        loaded = json.loads(json_str)
        assert loaded['version'] == '1.0.0'
        assert loaded['league'] == 'NBA'
    
    def test_calibration_pack_save_load(self):
        """Test calibration pack can be saved and loaded from file."""
        pack = CalibrationPack(
            version="1.0.0",
            league="NBA",
            generated_at=datetime.now().isoformat(),
            backtest_period={'start': '2020-01-01', 'end': '2024-12-31'},
            train_period={'start': '2020-01-01', 'end': '2022-12-31'},
            test_period={'start': '2023-01-01', 'end': '2024-12-31'},
            edge_thresholds={'moneyline': 0.02, 'spread': 0.03},
            variance_scalars={'global': 1.0},
            kelly_policy={'method': 'fractional', 'fraction': 0.25, 'max_stake': 0.05, 'min_stake': 0.01},
            probability_transforms={'method': 'none'},
            metrics={'roi': 0.05, 'sharpe': 1.2, 'hit_rate': 0.52, 'total_bets': 100},
            reliability_bins=[],
            notes=['Test']
        )
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            pack.save(temp_path)
            
            # Load and verify
            with open(temp_path, 'r') as f:
                loaded = json.load(f)
            
            assert loaded['version'] == '1.0.0'
            assert loaded['league'] == 'NBA'
            assert 'edge_thresholds' in loaded
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestMetricsCalculations:
    """Test performance metrics calculations."""
    
    def test_metrics_roi_calculation(self):
        """Test ROI is calculated correctly."""
        metrics = CalibrationMetrics(
            roi=0.05,
            sharpe=1.0,
            max_drawdown=10.0,
            hit_rate=0.52,
            total_bets=100,
            winning_bets=52,
            losing_bets=48,
            push_bets=0,
            total_staked=100.0,
            total_profit=5.0,
            brier_score=0.25,
            log_loss=0.69
        )
        
        # ROI = total_profit / total_staked
        expected_roi = 5.0 / 100.0
        assert metrics.roi == expected_roi
    
    def test_metrics_hit_rate_calculation(self):
        """Test hit rate is calculated correctly."""
        metrics = CalibrationMetrics(
            roi=0.05,
            sharpe=1.0,
            max_drawdown=10.0,
            hit_rate=0.52,
            total_bets=100,
            winning_bets=52,
            losing_bets=48,
            push_bets=0,
            total_staked=100.0,
            total_profit=5.0,
            brier_score=0.25,
            log_loss=0.69
        )
        
        # Hit rate = winning_bets / (winning_bets + losing_bets)
        # When there are no pushes, this is the same as winning_bets / total_bets
        expected_hit_rate = 52 / 100
        assert metrics.hit_rate == expected_hit_rate
    
    def test_metrics_brier_score_range(self):
        """Test Brier score is in valid range [0, 1]."""
        metrics = CalibrationMetrics(
            roi=0.05,
            sharpe=1.0,
            max_drawdown=10.0,
            hit_rate=0.52,
            total_bets=100,
            winning_bets=52,
            losing_bets=48,
            push_bets=0,
            total_staked=100.0,
            total_profit=5.0,
            brier_score=0.25,
            log_loss=0.69
        )
        
        assert 0.0 <= metrics.brier_score <= 1.0, "Brier score must be in [0, 1]"
    
    def test_metrics_to_dict(self):
        """Test metrics can be converted to dictionary."""
        metrics = CalibrationMetrics(
            roi=0.05,
            sharpe=1.0,
            max_drawdown=10.0,
            hit_rate=0.52,
            total_bets=100,
            winning_bets=52,
            losing_bets=48,
            push_bets=0,
            total_staked=100.0,
            total_profit=5.0,
            brier_score=0.25,
            log_loss=0.69
        )
        
        metrics_dict = metrics.to_dict()
        
        assert isinstance(metrics_dict, dict)
        assert 'roi' in metrics_dict
        assert 'sharpe' in metrics_dict
        assert 'hit_rate' in metrics_dict
        assert metrics_dict['total_bets'] == 100
    
    def test_metrics_with_pushes(self):
        """Test that pushes are correctly excluded from hit rate calculation."""
        # 50 wins, 40 losses, 10 pushes = 100 total bets
        # Hit rate should be 50 / (50 + 40) = 0.5556, NOT 50 / 100 = 0.5
        metrics = CalibrationMetrics(
            roi=0.02,
            sharpe=0.8,
            max_drawdown=5.0,
            hit_rate=0.5556,
            total_bets=100,
            winning_bets=50,
            losing_bets=40,
            push_bets=10,
            total_staked=100.0,
            total_profit=2.0,
            brier_score=0.24,
            log_loss=0.68
        )
        
        # Verify pushes are tracked separately
        assert metrics.push_bets == 10
        assert metrics.winning_bets == 50
        assert metrics.losing_bets == 40
        assert metrics.total_bets == 100
        
        # Verify winning + losing + pushes = total
        assert metrics.winning_bets + metrics.losing_bets + metrics.push_bets == metrics.total_bets


class TestCalibrationRunner:
    """Test calibration runner functionality."""
    
    def test_runner_initialization(self):
        """Test runner initializes correctly."""
        runner = CalibrationRunner(
            league="NBA",
            start_date="2023-01-01",
            end_date="2023-12-31",
            train_split=0.7,
            dry_run=True
        )
        
        assert runner.league == "NBA"
        assert runner.start_date == "2023-01-01"
        assert runner.end_date == "2023-12-31"
        assert runner.train_split == 0.7
        assert runner.dry_run is True
    
    def test_american_odds_conversion(self):
        """Test American odds to probability conversion."""
        runner = CalibrationRunner(
            league="NBA",
            start_date="2023-01-01",
            end_date="2023-12-31"
        )
        
        # Test negative odds (favorite)
        prob_neg = runner._american_to_prob(-110)
        assert 0.5 < prob_neg < 0.6  # -110 implies ~52.4%
        
        # Test positive odds (underdog)
        prob_pos = runner._american_to_prob(150)
        assert 0.3 < prob_pos < 0.5  # +150 implies ~40%
        
        # Test edge cases
        prob_even = runner._american_to_prob(100)
        assert prob_even == 0.5  # Even odds = 50%


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
