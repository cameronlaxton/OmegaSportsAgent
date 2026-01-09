"""
Lab configuration management.
"""

import os
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Auto-configure OmegaSports path on config load
def _setup_omega_path():
    """Automatically set up OmegaSports path when config is loaded."""
    omega_path = os.getenv("OMEGA_ENGINE_PATH")
    if omega_path:
        omega_path_obj = Path(omega_path)
        if omega_path_obj.exists():
            omega_path_str = str(omega_path_obj)
            # Add to end of sys.path so local omega package takes precedence
            if omega_path_str not in sys.path:
                sys.path.append(omega_path_str)


class LabConfig:
    """
    Configuration management for OmegaSports Validation Lab.

    Loads configuration from environment variables and .env file.
    """

    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            env_file: Path to .env file. Defaults to .env in project root.
        """
        if env_file is None:
            env_file = Path(__file__).parent.parent / ".env"

        if Path(env_file).exists():
            load_dotenv(env_file)
        
        # Auto-setup OmegaSports path
        _setup_omega_path()

    # Paths
    @property
    def project_root(self) -> Path:
        """Project root directory."""
        return Path(__file__).parent.parent

    @property
    def data_dir(self) -> Path:
        """Data directory path."""
        return self.project_root / "data"

    @property
    def historical_data_path(self) -> Path:
        """Historical game data directory."""
        path = Path(os.getenv("DATA_HISTORICAL_PATH", self.data_dir / "historical"))
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def experiments_path(self) -> Path:
        """Experiment results directory."""
        path = Path(os.getenv("DATA_EXPERIMENTS_PATH", self.data_dir / "experiments"))
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def logs_path(self) -> Path:
        """Logs directory."""
        path = Path(os.getenv("DATA_LOGS_PATH", self.data_dir / "logs"))
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def cache_path(self) -> Path:
        """Cache directory."""
        path = Path(os.getenv("DATA_CACHE_PATH", self.data_dir / "cache"))
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def notebooks_path(self) -> Path:
        """Notebooks directory."""
        return self.project_root / "notebooks"

    @property
    def reports_path(self) -> Path:
        """Reports directory."""
        path = self.project_root / "reports"
        path.mkdir(exist_ok=True)
        return path

    # OmegaSports Engine
    @property
    def omega_engine_path(self) -> Optional[Path]:
        """Path to OmegaSports engine."""
        path = os.getenv("OMEGA_ENGINE_PATH")
        return Path(path) if path else None

    # API Keys
    @property
    def perplexity_api_key(self) -> Optional[str]:
        """Perplexity API key."""
        return os.getenv("PERPLEXITY_API_KEY")

    @property
    def balldontlie_api_key(self) -> Optional[str]:
        """BallDontLie API key."""
        return os.getenv("BALLDONTLIE_API_KEY")

    @property
    def the_odds_api_key(self) -> Optional[str]:
        """TheOdds API key."""
        return os.getenv("THE_ODDS_API_KEY")

    # Lab Configuration
    @property
    def log_level(self) -> str:
        """Logging level."""
        return os.getenv("LAB_LOG_LEVEL", "INFO")

    @property
    def output_format(self) -> str:
        """Output format (json, csv, markdown)."""
        return os.getenv("LAB_OUTPUT_FORMAT", "json")

    @property
    def parallel_execution(self) -> bool:
        """Whether to enable parallel module execution."""
        return os.getenv("LAB_PARALLEL_EXECUTION", "true").lower() == "true"

    @property
    def max_workers(self) -> int:
        """Maximum number of parallel workers."""
        return int(os.getenv("LAB_MAX_WORKERS", "4"))

    # Experiment Configuration
    @property
    def default_iterations(self) -> int:
        """Default simulation iterations."""
        return int(os.getenv("DEFAULT_ITERATIONS", "10000"))

    @property
    def backtest_start_year(self) -> int:
        """Backtest start year."""
        return int(os.getenv("BACKTEST_START_YEAR", "2020"))

    @property
    def backtest_end_year(self) -> int:
        """Backtest end year."""
        return int(os.getenv("BACKTEST_END_YEAR", "2024"))

    def __repr__(self) -> str:
        """String representation."""
        return f"LabConfig(project_root={self.project_root})"


# Global config instance
config = LabConfig()
