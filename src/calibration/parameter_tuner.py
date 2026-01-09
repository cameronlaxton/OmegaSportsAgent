"""
Parameter Tuner Module

Autonomously adjusts model parameters based on performance feedback.
Uses multiple tuning strategies to optimize prediction accuracy.
"""

from __future__ import annotations
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from src.calibration.performance_tracker import PerformanceTracker


class TuningStrategy(Enum):
    """Available parameter tuning strategies."""
    GRADIENT_DESCENT = "gradient_descent"  # Adjust toward better performance
    BAYESIAN = "bayesian"  # Bayesian optimization
    GRID_SEARCH = "grid_search"  # Systematic grid search
    ADAPTIVE = "adaptive"  # Adaptive based on recent performance
    CONSERVATIVE = "conservative"  # Small, safe adjustments


@dataclass
class ParameterConfig:
    """
    Configuration for a tunable parameter.
    
    Attributes:
        name: Parameter name
        current_value: Current value
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        step_size: Size of adjustments
        priority: Higher priority parameters are tuned first
    """
    name: str
    current_value: float
    min_value: float
    max_value: float
    step_size: float
    priority: int = 1


class ParameterTuner:
    """
    Autonomous parameter tuning engine.
    
    This system continuously adjusts model parameters to optimize performance.
    It learns from historical outcomes and makes data-driven adjustments.
    """
    
    def __init__(
        self,
        tracker: PerformanceTracker,
        config_path: str = "config/calibration/tuned_parameters.json"
    ):
        """
        Initialize the parameter tuner.
        
        Args:
            tracker: PerformanceTracker instance for accessing historical data
            config_path: Path to JSON file storing tuned parameters
        """
        self.tracker = tracker
        self.config_path = config_path
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Load or initialize parameter configuration
        self.parameters = self._load_or_initialize_parameters()
    
    def _load_or_initialize_parameters(self) -> Dict[str, ParameterConfig]:
        """Load existing parameter config or create default."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    return {
                        name: ParameterConfig(**config)
                        for name, config in data.items()
                    }
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        # Default parameters for various models
        return self._get_default_parameters()
    
    def _get_default_parameters(self) -> Dict[str, ParameterConfig]:
        """Get default tunable parameters across all models."""
        return {
            # Markov simulation parameters
            "markov_shot_allocation_star": ParameterConfig(
                name="markov_shot_allocation_star",
                current_value=0.30,
                min_value=0.20,
                max_value=0.45,
                step_size=0.02,
                priority=2
            ),
            "markov_possession_adjustment_factor": ParameterConfig(
                name="markov_possession_adjustment_factor",
                current_value=1.0,
                min_value=0.7,
                max_value=1.3,
                step_size=0.05,
                priority=3
            ),
            
            # Monte Carlo simulation parameters
            "monte_carlo_iterations": ParameterConfig(
                name="monte_carlo_iterations",
                current_value=10000,
                min_value=5000,
                max_value=50000,
                step_size=5000,
                priority=1
            ),
            "monte_carlo_variance_multiplier": ParameterConfig(
                name="monte_carlo_variance_multiplier",
                current_value=1.0,
                min_value=0.8,
                max_value=1.5,
                step_size=0.1,
                priority=2
            ),
            
            # Edge threshold parameters
            "edge_threshold_spread": ParameterConfig(
                name="edge_threshold_spread",
                current_value=3.0,
                min_value=2.0,
                max_value=6.0,
                step_size=0.5,
                priority=3
            ),
            "edge_threshold_prop": ParameterConfig(
                name="edge_threshold_prop",
                current_value=5.0,
                min_value=3.0,
                max_value=8.0,
                step_size=0.5,
                priority=3
            ),
            
            # Kelly staking parameters
            "kelly_fraction": ParameterConfig(
                name="kelly_fraction",
                current_value=0.25,
                min_value=0.10,
                max_value=0.50,
                step_size=0.05,
                priority=1
            ),
            
            # Probability calibration parameters
            "calibration_shrink_factor": ParameterConfig(
                name="calibration_shrink_factor",
                current_value=0.70,
                min_value=0.50,
                max_value=0.95,
                step_size=0.05,
                priority=2
            ),
            "calibration_cap_max": ParameterConfig(
                name="calibration_cap_max",
                current_value=0.85,
                min_value=0.75,
                max_value=0.95,
                step_size=0.02,
                priority=2
            ),
            "calibration_cap_min": ParameterConfig(
                name="calibration_cap_min",
                current_value=0.15,
                min_value=0.05,
                max_value=0.25,
                step_size=0.02,
                priority=2
            )
        }
    
    def save_parameters(self) -> None:
        """Save current parameter configuration to disk."""
        data = {
            name: {
                "name": config.name,
                "current_value": config.current_value,
                "min_value": config.min_value,
                "max_value": config.max_value,
                "step_size": config.step_size,
                "priority": config.priority
            }
            for name, config in self.parameters.items()
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_parameter(self, name: str) -> float:
        """Get current value of a parameter."""
        if name in self.parameters:
            return self.parameters[name].current_value
        return None
    
    def auto_tune(
        self,
        strategy: TuningStrategy = TuningStrategy.ADAPTIVE,
        min_samples: int = 50,
        recent_window: int = 100
    ) -> Dict[str, Any]:
        """
        Autonomously tune parameters based on recent performance.
        
        This is the main entry point for autonomous calibration.
        It analyzes recent performance and adjusts parameters to improve accuracy.
        
        Args:
            strategy: Tuning strategy to use
            min_samples: Minimum settled predictions required before tuning
            recent_window: Number of recent predictions to analyze
        
        Returns:
            Dict with tuning results and parameter changes
        """
        # Get recent performance data
        records = self.tracker.get_records(settled_only=True, limit=recent_window)
        
        if len(records) < min_samples:
            return {
                "status": "insufficient_data",
                "message": f"Need {min_samples} settled predictions, have {len(records)}",
                "parameters_tuned": 0
            }
        
        # Get current performance metrics
        current_performance = self.tracker.get_performance_summary(recent_n=recent_window)
        
        if strategy == TuningStrategy.ADAPTIVE:
            results = self._adaptive_tuning(records, current_performance)
        elif strategy == TuningStrategy.CONSERVATIVE:
            results = self._conservative_tuning(records, current_performance)
        else:
            results = self._gradient_tuning(records, current_performance)
        
        # Save updated parameters
        self.save_parameters()
        
        return results
    
    def _adaptive_tuning(
        self,
        records: List,
        current_performance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Adaptive tuning based on recent performance trends.
        
        This strategy makes larger adjustments when performance is poor,
        and smaller adjustments when performance is good.
        """
        adjustments = []
        
        roi = current_performance.get("roi", 0)
        win_rate = current_performance.get("win_rate", 0.5)
        brier_score = current_performance.get("brier_score", 0.25)
        
        # Determine adjustment magnitude based on performance
        if roi < -5:  # Losing money
            magnitude_multiplier = 2.0  # Aggressive adjustments
        elif roi < 0:
            magnitude_multiplier = 1.5  # Moderate adjustments
        elif roi < 5:
            magnitude_multiplier = 1.0  # Standard adjustments
        else:  # Making good money
            magnitude_multiplier = 0.5  # Conservative adjustments
        
        # Tune edge thresholds based on win rate
        if win_rate < 0.48:  # Win rate too low
            # Increase edge thresholds (be more selective)
            for param_name in ["edge_threshold_spread", "edge_threshold_prop"]:
                if param_name in self.parameters:
                    param = self.parameters[param_name]
                    adjustment = param.step_size * magnitude_multiplier
                    new_value = min(param.max_value, param.current_value + adjustment)
                    
                    if new_value != param.current_value:
                        adjustments.append({
                            "parameter": param_name,
                            "old_value": param.current_value,
                            "new_value": new_value,
                            "reason": f"Win rate low ({win_rate:.2%}), increasing selectivity"
                        })
                        param.current_value = new_value
        
        elif win_rate > 0.55:  # Win rate good but maybe being too conservative
            # Decrease edge thresholds slightly (be more aggressive)
            for param_name in ["edge_threshold_spread", "edge_threshold_prop"]:
                if param_name in self.parameters:
                    param = self.parameters[param_name]
                    adjustment = param.step_size * 0.5  # Small adjustment when doing well
                    new_value = max(param.min_value, param.current_value - adjustment)
                    
                    if new_value != param.current_value:
                        adjustments.append({
                            "parameter": param_name,
                            "old_value": param.current_value,
                            "new_value": new_value,
                            "reason": f"Win rate high ({win_rate:.2%}), can be more aggressive"
                        })
                        param.current_value = new_value
        
        # Tune calibration based on Brier score
        if brier_score > 0.20:  # Poor calibration
            # Increase shrinkage
            param = self.parameters.get("calibration_shrink_factor")
            if param:
                adjustment = param.step_size * magnitude_multiplier
                new_value = max(param.min_value, param.current_value - adjustment)
                
                if new_value != param.current_value:
                    adjustments.append({
                        "parameter": "calibration_shrink_factor",
                        "old_value": param.current_value,
                        "new_value": new_value,
                        "reason": f"Brier score high ({brier_score:.3f}), increasing shrinkage"
                    })
                    param.current_value = new_value
        
        # Tune Kelly fraction based on ROI volatility
        # (Would need variance calculation here - simplified for now)
        
        return {
            "status": "success",
            "strategy": "adaptive",
            "parameters_tuned": len(adjustments),
            "adjustments": adjustments,
            "performance_metrics": current_performance,
            "timestamp": datetime.now().isoformat()
        }
    
    def _conservative_tuning(
        self,
        records: List,
        current_performance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Conservative tuning that makes small, safe adjustments.
        
        Use this strategy when you want minimal changes to stable parameters.
        """
        adjustments = []
        
        # Only make adjustments if performance is clearly problematic
        roi = current_performance.get("roi", 0)
        brier_score = current_performance.get("brier_score", 0.25)
        
        if roi < -10:  # Significant losses
            # Small increase to edge thresholds
            param = self.parameters.get("edge_threshold_spread")
            if param:
                new_value = min(param.max_value, param.current_value + param.step_size * 0.5)
                if new_value != param.current_value:
                    adjustments.append({
                        "parameter": "edge_threshold_spread",
                        "old_value": param.current_value,
                        "new_value": new_value,
                        "reason": f"ROI very negative ({roi:.1f}%), small defensive adjustment"
                    })
                    param.current_value = new_value
        
        if brier_score > 0.25:  # Very poor calibration
            # Small adjustment to calibration
            param = self.parameters.get("calibration_shrink_factor")
            if param:
                new_value = max(param.min_value, param.current_value - param.step_size * 0.5)
                if new_value != param.current_value:
                    adjustments.append({
                        "parameter": "calibration_shrink_factor",
                        "old_value": param.current_value,
                        "new_value": new_value,
                        "reason": f"Brier score very high ({brier_score:.3f}), small adjustment"
                    })
                    param.current_value = new_value
        
        return {
            "status": "success",
            "strategy": "conservative",
            "parameters_tuned": len(adjustments),
            "adjustments": adjustments,
            "performance_metrics": current_performance,
            "timestamp": datetime.now().isoformat()
        }
    
    def _gradient_tuning(
        self,
        records: List,
        current_performance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Gradient-based tuning using parameter performance analysis.
        
        This examines which parameter values led to best outcomes and
        adjusts toward those values.
        """
        adjustments = []
        
        # Analyze performance by parameter value for key parameters
        priority_params = sorted(
            self.parameters.values(),
            key=lambda p: p.priority
        )[:5]  # Top 5 priority parameters
        
        for param in priority_params:
            perf_analysis = self.tracker.get_parameter_performance(param.name)
            
            if not perf_analysis:
                continue
            
            # Find parameter value with best ROI
            best_value = None
            best_roi = float('-inf')
            
            for value_str, metrics in perf_analysis.items():
                if metrics['count'] >= 10:  # Need sufficient sample size
                    if metrics['roi'] > best_roi:
                        best_roi = metrics['roi']
                        best_value = float(value_str)
            
            # Adjust toward best performing value
            if best_value is not None and best_roi > 0:
                direction = 1 if best_value > param.current_value else -1
                adjustment = param.step_size * direction * 0.5  # Move halfway
                new_value = param.current_value + adjustment
                new_value = max(param.min_value, min(param.max_value, new_value))
                
                if abs(new_value - param.current_value) > 0.001:
                    adjustments.append({
                        "parameter": param.name,
                        "old_value": param.current_value,
                        "new_value": new_value,
                        "reason": f"Gradient toward better ROI ({best_roi:.1f}% at {best_value})"
                    })
                    param.current_value = new_value
        
        return {
            "status": "success",
            "strategy": "gradient_descent",
            "parameters_tuned": len(adjustments),
            "adjustments": adjustments,
            "performance_metrics": current_performance,
            "timestamp": datetime.now().isoformat()
        }
