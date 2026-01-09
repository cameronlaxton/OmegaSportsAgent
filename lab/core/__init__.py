"""
Core infrastructure modules for OmegaSports Validation Lab.

This package provides the foundational components for experimental execution:
- data_pipeline: Data ingestion and validation
- historical_data_scraper: Enhanced historical data fetching with comprehensive statistics
- simulation_framework: Unified simulation interface
- performance_tracker: Metrics calculation and tracking
- experiment_logger: Execution logging and result persistence
- statistical_validation: Statistical testing utilities
"""

__version__ = "1.0.0"
__author__ = "Cameron Laxton"

from core.data_pipeline import DataPipeline
from core.historical_data_scraper import HistoricalDataScraper
from core.multi_source_aggregator import MultiSourceAggregator, validate_not_sample_data
from core.simulation_framework import SimulationFramework
from core.performance_tracker import PerformanceTracker
from core.experiment_logger import ExperimentLogger
from core.statistical_validation import StatisticalValidator

__all__ = [
    "DataPipeline",
    "HistoricalDataScraper",
    "MultiSourceAggregator",
    "validate_not_sample_data",
    "SimulationFramework",
    "PerformanceTracker",
    "ExperimentLogger",
    "StatisticalValidator",
]
