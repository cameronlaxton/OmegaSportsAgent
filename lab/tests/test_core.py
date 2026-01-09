"""
Tests for core modules.
"""

import pytest
from pathlib import Path
from utils.config import LabConfig
from core.performance_tracker import PerformanceTracker, PerformanceMetrics
from core.statistical_validation import StatisticalValidator


class TestLabConfig:
    """Tests for LabConfig."""

    def test_config_initialization(self):
        """Test config can be initialized."""
        config = LabConfig()
        assert config.project_root.exists()

    def test_path_properties(self):
        """Test path properties are accessible."""
        config = LabConfig()
        assert isinstance(config.data_dir, Path)
        assert isinstance(config.historical_data_path, Path)
        assert isinstance(config.experiments_path, Path)

    def test_paths_are_created(self):
        """Test paths are created on access."""
        config = LabConfig()
        assert config.historical_data_path.exists()
        assert config.experiments_path.exists()
        assert config.logs_path.exists()


class TestPerformanceTracker:
    """Tests for PerformanceTracker."""

    def test_tracker_initialization(self):
        """Test tracker can be initialized."""
        tracker = PerformanceTracker()
        assert tracker is not None

    def test_roi_calculation(self):
        """Test ROI calculation."""
        tracker = PerformanceTracker()

        # Test normal case
        roi = tracker.calculate_roi(100.0, 110.0)
        assert roi == pytest.approx(0.1, rel=0.01)

        # Test no change
        roi = tracker.calculate_roi(100.0, 100.0)
        assert roi == pytest.approx(0.0, rel=0.01)

        # Test loss
        roi = tracker.calculate_roi(100.0, 90.0)
        assert roi == pytest.approx(-0.1, rel=0.01)

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        tracker = PerformanceTracker()

        # Test 50% hit rate
        hit_rate = tracker.calculate_hit_rate(5, 10)
        assert hit_rate == pytest.approx(0.5, rel=0.01)

        # Test 100% win
        hit_rate = tracker.calculate_hit_rate(10, 10)
        assert hit_rate == pytest.approx(1.0, rel=0.01)

        # Test 0% win
        hit_rate = tracker.calculate_hit_rate(0, 10)
        assert hit_rate == pytest.approx(0.0, rel=0.01)


class TestStatisticalValidator:
    """Tests for StatisticalValidator."""

    def test_bootstrap_ci(self):
        """Test bootstrap confidence interval."""
        # Create sample data
        data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]

        lower, upper = StatisticalValidator.bootstrap_confidence_interval(
            data, confidence=0.95, n_iterations=1000
        )

        # CI should contain the mean
        mean = sum(data) / len(data)
        assert lower <= mean <= upper
        assert lower < upper

    def test_cohens_d(self):
        """Test Cohen's d effect size calculation."""
        group1 = [1, 2, 3, 4, 5]
        group2 = [2, 3, 4, 5, 6]

        d = StatisticalValidator.effect_size(group1, group2)
        # Should be negative since group1 < group2
        assert d < 0
