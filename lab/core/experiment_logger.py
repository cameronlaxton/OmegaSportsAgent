"""
Experiment logging and result persistence.
"""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ExperimentLogger:
    """
    Manages experiment execution logging and result persistence.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize experiment logger.

        Args:
            output_dir: Directory for saving experiment results
        """
        self.output_dir = output_dir or Path("./data/experiments")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.start_time = None
        self.experiment_id = None

    def start_experiment(self, experiment_id: str) -> None:
        """
        Log experiment start.

        Args:
            experiment_id: Unique experiment identifier
        """
        self.start_time = datetime.now()
        self.experiment_id = experiment_id
        logger.info(f"Started experiment: {experiment_id}")

    def end_experiment(self) -> None:
        """
        Log experiment end and save metadata.
        """
        if self.start_time and self.experiment_id:
            duration = (datetime.now() - self.start_time).total_seconds()
            logger.info(f"Ended experiment: {self.experiment_id} (duration: {duration:.1f}s)")

    def save_results(self, results: Dict[str, Any], filename: Optional[str] = None) -> Path:
        """
        Save experiment results to JSON file.

        Args:
            results: Results dictionary
            filename: Output filename. Auto-generated if not provided.

        Returns:
            Path to saved file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"experiment_{self.experiment_id}_{timestamp}.json"

        filepath = self.output_dir / filename
        with open(filepath, "w") as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(f"Saved results to {filepath}")
        return filepath

    def load_results(self, filename: str) -> Dict[str, Any]:
        """
        Load experiment results from JSON file.

        Args:
            filename: Input filename

        Returns:
            Results dictionary
        """
        filepath = self.output_dir / filename
        with open(filepath, "r") as f:
            results = json.load(f)
        logger.info(f"Loaded results from {filepath}")
        return results
