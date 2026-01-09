"""
Results analysis for Module 1: Edge Threshold Calibration
"""

import json
from pathlib import Path
from typing import Dict, List, Any


def load_results(results_file: Path) -> Dict[str, Any]:
    """
    Load experiment results from file.

    Args:
        results_file: Path to results JSON file

    Returns:
        Results dictionary
    """
    with open(results_file, "r") as f:
        return json.load(f)


def get_threshold_rankings(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get rankings of thresholds by ROI.

    Args:
        results: Results dictionary

    Returns:
        List of ranked thresholds
    """
    tests = results["results"]["threshold_tests"]
    ranked = sorted(tests, key=lambda x: x["roi"], reverse=True)
    return ranked[:10]  # Top 10


def print_summary(results: Dict[str, Any]) -> None:
    """
    Print results summary.

    Args:
        results: Results dictionary
    """
    print("\n" + "="*80)
    print("Module 1: Edge Threshold Calibration - Results Summary")
    print("="*80)
    print(f"Execution Date: {results['execution_date']}")
    print(f"Duration: {results['duration_seconds']:.1f} seconds")
    print(f"Total Tests: {results['results']['total_tests']}")

    analysis = results["results"]["analysis"]
    print(f"\nOverall Best Threshold: {analysis['overall_best_threshold']}%")

    print("\nBest Threshold by Sport:")
    for sport, best in analysis["sport_best_thresholds"].items():
        print(
            f"  {sport}: {best['threshold']}% (ROI: {best['roi']:.1%}, Hit Rate: {best['hit_rate']:.1%})"
        )

    print("\n" + "="*80)
