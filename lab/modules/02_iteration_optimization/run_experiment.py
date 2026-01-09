#!/usr/bin/env python
"""
Module 2: Simulation Iteration Optimization

Systematically determines the minimum simulation iterations required for
stable probability estimates while balancing computational cost.

Tests iteration counts: 1000, 2500, 5000, 10000, 25000, 50000
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from dataclasses import dataclass, asdict

from core.data_pipeline import DataPipeline
from core.simulation_framework import SimulationFramework, ExperimentConfig
from core.performance_tracker import PerformanceTracker
from core.experiment_logger import ExperimentLogger
from utils.config import config

logger = logging.getLogger(__name__)


@dataclass
class IterationResult:
    """Result for single iteration count test."""
    
    iterations: int
    sport: str
    convergence_score: float
    stability_score: float
    execution_time: float
    num_games: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class IterationOptimizationModule:
    """
    Systematic iteration count optimization experiment.
    
    Determines minimum iterations needed for stable probability estimates.
    """
    
    # Iteration counts to test
    ITERATION_COUNTS = [1000, 2500, 5000, 10000, 25000, 50000]
    
    # Sports to test
    SPORTS = ["NBA", "NFL"]
    
    def __init__(self, config_obj=None):
        """
        Initialize iteration optimization module.
        
        Args:
            config_obj: Configuration object (defaults to global config)
        """
        self.config = config_obj or config
        self.pipeline = DataPipeline(
            cache_dir=self.config.cache_path,
            data_dir=self.config.historical_data_path,
        )
        self.framework = SimulationFramework()
        self.tracker = PerformanceTracker()
        self.logger = ExperimentLogger(self.config.experiments_path)
        
        self.results: List[IterationResult] = []
        
        logger.info("IterationOptimizationModule initialized")
    
    def run(self) -> Dict[str, Any]:
        """
        Run the complete iteration optimization experiment.
        
        Returns:
            Results dictionary
        """
        self.logger.start_experiment("module_02_iteration_optimization")
        start_time = datetime.now()
        
        logger.info("Starting Module 2: Iteration Optimization")
        logger.info(f"Testing iteration counts: {self.ITERATION_COUNTS}")
        logger.info(f"Sports: {self.SPORTS}")
        
        # Phase 1: Load sample games for testing
        logger.info("\n=== Phase 1: Loading Sample Games ===")
        sample_games = self._load_sample_games()
        
        # Phase 2: Test each iteration count
        logger.info("\n=== Phase 2: Testing Iteration Counts ===")
        for sport in self.SPORTS:
            games = sample_games.get(sport, [])
            if not games:
                logger.warning(f"No games available for {sport}, skipping")
                continue
            
            for iterations in self.ITERATION_COUNTS:
                logger.info(f"Testing {sport} with {iterations} iterations")
                result = self._test_iteration_count(sport, games, iterations)
                self.results.append(result)
        
        # Phase 3: Analyze results
        logger.info("\n=== Phase 3: Analyzing Results ===")
        analysis = self._analyze_results()
        
        # Phase 4: Generate report
        logger.info("\n=== Phase 4: Generating Report ===")
        report = self._generate_report(analysis)
        
        # Save results
        self._save_results(report)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"\nModule 2 completed in {elapsed:.2f}s")
        
        self.logger.end_experiment(report)
        
        return report
    
    def _load_sample_games(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load sample games for each sport.
        
        Returns:
            Dictionary of sport -> games list
        """
        sample_games = {}
        
        for sport in self.SPORTS:
            try:
                # Try to load cached games
                games = self.pipeline.fetch_and_cache_games(
                    sport=sport,
                    start_year=2024,
                    end_year=2024,
                    force_refresh=False
                )
                
                # Limit to 100 games for testing
                sample_games[sport] = games[:100] if games else []
                logger.info(f"Loaded {len(sample_games[sport])} games for {sport}")
            except Exception as e:
                logger.warning(f"Could not load games for {sport}: {e}")
                sample_games[sport] = []
        
        return sample_games
    
    def _test_iteration_count(
        self, 
        sport: str, 
        games: List[Dict[str, Any]], 
        iterations: int
    ) -> IterationResult:
        """
        Test a specific iteration count.
        
        Args:
            sport: Sport name
            games: List of games to test
            iterations: Number of iterations to use
            
        Returns:
            IterationResult with metrics
        """
        start_time = datetime.now()
        
        # Create experiment config
        exp_config = ExperimentConfig(
            module_name="iteration_optimization",
            sport=sport,
            iterations=iterations
        )
        
        # Run simulation
        sim_results = self.framework.run_simulation(exp_config, games)
        
        # Calculate metrics (stub implementation)
        convergence_score = self._calculate_convergence(sim_results)
        stability_score = self._calculate_stability(sim_results)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        return IterationResult(
            iterations=iterations,
            sport=sport,
            convergence_score=convergence_score,
            stability_score=stability_score,
            execution_time=elapsed,
            num_games=len(games)
        )
    
    def _calculate_convergence(self, sim_results: Dict[str, Any]) -> float:
        """
        Calculate convergence score.
        
        Stub implementation - returns placeholder value.
        Real implementation would measure distribution stability.
        """
        # TODO: Implement Hellinger distance or similar metric
        return 0.95
    
    def _calculate_stability(self, sim_results: Dict[str, Any]) -> float:
        """
        Calculate stability score.
        
        Stub implementation - returns placeholder value.
        Real implementation would measure repeated run variance.
        """
        # TODO: Implement variance measurement across repeated runs
        return 0.92
    
    def _analyze_results(self) -> Dict[str, Any]:
        """
        Analyze experiment results.
        
        Returns:
            Analysis dictionary
        """
        if not self.results:
            return {"message": "No results to analyze"}
        
        # Group by sport
        by_sport = {}
        for result in self.results:
            sport = result.sport
            if sport not in by_sport:
                by_sport[sport] = []
            by_sport[sport].append(result)
        
        # Find optimal iteration counts
        recommendations = {}
        for sport, sport_results in by_sport.items():
            # Find minimum iterations with acceptable convergence
            optimal = None
            for result in sorted(sport_results, key=lambda x: x.iterations):
                if result.convergence_score >= 0.90 and result.stability_score >= 0.85:
                    optimal = result
                    break
            
            recommendations[sport] = {
                "optimal_iterations": optimal.iterations if optimal else 50000,
                "convergence": optimal.convergence_score if optimal else 0.0,
                "stability": optimal.stability_score if optimal else 0.0,
                "avg_time_per_game": optimal.execution_time / optimal.num_games if optimal else 0.0
            }
        
        return {
            "recommendations": recommendations,
            "total_tests": len(self.results),
            "sports_tested": list(by_sport.keys())
        }
    
    def _generate_report(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate final report.
        
        Args:
            analysis: Analysis results
            
        Returns:
            Complete report dictionary
        """
        return {
            "module": "02_iteration_optimization",
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "results": [r.to_dict() for r in self.results],
            "analysis": analysis,
            "summary": {
                "total_tests": len(self.results),
                "iteration_counts_tested": self.ITERATION_COUNTS,
                "sports": self.SPORTS
            }
        }
    
    def _save_results(self, report: Dict[str, Any]) -> None:
        """
        Save results to disk.
        
        Args:
            report: Report dictionary to save
        """
        output_dir = self.config.experiments_path / "module_02"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"iteration_optimization_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")


def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    module = IterationOptimizationModule()
    results = module.run()
    
    print("\n" + "="*80)
    print("Module 2: Iteration Optimization - Complete")
    print("="*80)
    print(json.dumps(results["analysis"], indent=2))
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
