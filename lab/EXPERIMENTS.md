# OmegaSports Validation Lab: Experiment Protocols

## Overview

This document defines the standardized protocols for running all experimental modules in the OmegaSports Validation Lab.

## Experiment Lifecycle

Every experiment follows a consistent 5-phase lifecycle:

```
1. DESIGN
   ↓
2. EXECUTION
   ↓
3. ANALYSIS
   ↓
4. VALIDATION
   ↓
5. DOCUMENTATION
```

### Phase 1: Design

Before running any experiment:

1. **Define Hypothesis** - Write testable prediction
   ```
   Example: "Increasing edge threshold from 3% to 4% will improve long-term ROI
            without significantly reducing bet volume."
   ```

2. **Specify Variables** - Document independent, dependent, and control variables
   ```
   Independent: Edge threshold (1%, 2%, 3%, ... 10%)
   Dependent: ROI, hit rate, max drawdown
   Control: Sport (NBA), bet type (moneyline), period (2020-2024)
   ```

3. **Design Sample** - Determine data requirements
   ```
   Minimum 1,000 games per threshold level
   Stratified by date (even distribution across years)
   Balanced across home/away teams
   ```

4. **Plan Analysis** - Define statistical methods
   ```
   Primary: Descriptive statistics + confidence intervals
   Secondary: Hypothesis testing + effect sizes
   Validation: Sensitivity analysis + robustness checks
   ```

### Phase 2: Execution

1. **Initialize Environment**
   ```python
   from core.data_pipeline import DataPipeline
   from core.simulation_framework import SimulationFramework
   from core.experiment_logger import ExperimentLogger
   from utils.config import LabConfig

   config = LabConfig()
   pipeline = DataPipeline()
   framework = SimulationFramework()
   logger = ExperimentLogger()
   ```

2. **Load Data**
   ```python
   games = pipeline.fetch_historical_games(
       sport="NBA",
       start_date="2020-01-01",
       end_date="2024-12-31"
   )
   ```

3. **Run Simulation**
   ```python
   for threshold in [1.0, 2.0, 3.0, ..., 10.0]:
       config = ExperimentConfig(
           module_name="01_edge_threshold",
           sport="NBA",
           parameters={"edge_threshold": threshold}
       )
       results = framework.run_simulation(config, games)
       logger.save_results(results)
   ```

4. **Log Activity**
   ```python
   logger.start_experiment("module_01_threshold_calibration")
   try:
       # ... experiment code ...
   finally:
       logger.end_experiment()
   ```

### Phase 3: Analysis

1. **Calculate Metrics**
   ```python
   from core.performance_tracker import PerformanceTracker

   tracker = PerformanceTracker()
   metrics = tracker.calculate_metrics(results)
   ```

2. **Perform Statistical Tests**
   ```python
   from core.statistical_validation import StatisticalValidator

   lower, upper = StatisticalValidator.bootstrap_confidence_interval(
       roi_values, confidence=0.95
   )
   ```

3. **Generate Visualizations**
   ```python
   import matplotlib.pyplot as plt

   plt.figure(figsize=(12, 6))
   plt.plot(thresholds, roi_values)
   plt.xlabel('Edge Threshold (%)')
   plt.ylabel('ROI (%)')
   plt.title('ROI vs Edge Threshold')
   plt.savefig('roi_curve.png')
   ```

### Phase 4: Validation

1. **Sanity Checks**
   - Results should be within expected ranges
   - Sample sizes must be sufficient
   - No data quality issues

2. **Sensitivity Analysis**
   - Test robustness to parameter changes
   - Verify findings hold across subgroups
   - Check for outlier impacts

3. **Reproducibility**
   - Document all parameters and seeds
   - Verify results are consistent
   - Ensure others can replicate

### Phase 5: Documentation

1. **Write Results Summary**
   ```markdown
   ## Module 1 Results Summary

   **Hypothesis:** Optimal edge threshold is 3.5%

   **Key Findings:**
   - ROI maximized at 3.5% threshold (4.8% ROI)
   - Hit rate stable across 2-4% range (57-59%)
   - NBA thresholds differ from NFL (need separate tuning)

   **Recommendations:**
   - Deploy 3.5% threshold for NBA
   - Re-run for NFL separately
   - Monitor threshold performance in live trading
   ```

2. **Save Results**
   - All JSON results to `data/experiments/`
   - All visualizations to `reports/`
   - Analysis notebooks to `notebooks/`

3. **Create Issues**
   - Flag anomalies or unexpected findings
   - Document follow-up experiments needed
   - Link to related modules

## Standardized Module Template

Each module should follow this structure:

```python
# modules/XX_module_name/run_experiment.py

from pathlib import Path
from core.data_pipeline import DataPipeline
from core.simulation_framework import SimulationFramework, ExperimentConfig
from core.performance_tracker import PerformanceTracker
from core.experiment_logger import ExperimentLogger
from core.statistical_validation import StatisticalValidator

class Module:
    """Description of module purpose."""

    def __init__(self, config):
        self.config = config
        self.pipeline = DataPipeline()
        self.framework = SimulationFramework()
        self.tracker = PerformanceTracker()
        self.validator = StatisticalValidator()
        self.logger = ExperimentLogger()

    def run(self):
        """Execute the experiment."""
        self.logger.start_experiment(self.__class__.__name__)
        try:
            # Phase 1: Load data
            games = self.pipeline.fetch_historical_games(...)

            # Phase 2: Run simulations
            results = self._run_simulations(games)

            # Phase 3: Analyze results
            analysis = self._analyze_results(results)

            # Phase 4: Validate findings
            validation = self._validate_results(analysis)

            # Phase 5: Save and document
            self.logger.save_results({
                "results": results,
                "analysis": analysis,
                "validation": validation
            })

            return analysis
        finally:
            self.logger.end_experiment()

    def _run_simulations(self, games):
        """Run simulation experiments."""
        # Implementation
        pass

    def _analyze_results(self, results):
        """Perform statistical analysis."""
        # Implementation
        pass

    def _validate_results(self, analysis):
        """Validate findings."""
        # Implementation
        pass


if __name__ == "__main__":
    from utils.config import LabConfig
    config = LabConfig()
    module = Module(config)
    results = module.run()
```

## Data Requirements

### Minimum Sample Size

| Sport | Minimum Games | Recommended | Period |
|-------|---------------|-------------|--------|
| NBA | 1,000 | 2,000+ | 2020-2024 |
| NFL | 500 | 1,000+ | 2020-2024 |
| NCAAB | 500 | 1,000+ | 2020-2024 |
| NCAAF | 300 | 500+ | 2020-2024 |

### Data Quality Standards

- **Missing Values**: < 5% across all fields
- **Duplicates**: 0% - must be removed
- **Outliers**: Flagged and documented
- **Temporal Distribution**: Balanced across years
- **Validation**: Schema compliance 100%

## Result Documentation Standards

### JSON Result Structure

```json
{
  "experiment_id": "module_01_edge_threshold_001",
  "module": "01_edge_threshold",
  "execution_date": "2025-12-31T10:00:00Z",
  "duration_seconds": 3600.5,
  "parameters": {
    "sport": "NBA",
    "thresholds": [1.0, 2.0, 3.0],
    "iterations": 10000
  },
  "results": {
    "by_threshold": [
      {
        "threshold": 3.0,
        "hit_rate": 0.586,
        "roi": 0.048,
        "max_drawdown": -0.127,
        "num_bets": 42
      }
    ]
  },
  "statistics": {
    "confidence_level": 0.95,
    "p_values": [0.002, 0.001],
    "effect_sizes": [0.45, 0.52]
  },
  "validation": {
    "data_quality_score": 0.97,
    "reproducible": true,
    "anomalies": []
  },
  "status": "completed"
}
```

## Error Handling

All modules should implement graceful error handling:

```python
try:
    # Experiment code
    pass
except DataError as e:
    logger.error(f"Data error: {e}")
    # Fall back to cached data
    games = pipeline.get_cached_games()
except ComputationError as e:
    logger.error(f"Computation error: {e}")
    # Retry with reduced iterations
    results = framework.run_simulation(reduced_config, games)
except Exception as e:
    logger.critical(f"Unexpected error: {e}")
    # Ensure partial results are saved
    logger.save_partial_results(partial_results)
    raise
```

## Collaboration & Review

### Code Review Checklist

- [ ] Hypothesis clearly defined
- [ ] Sample sizes adequate
- [ ] Statistical methods appropriate
- [ ] Results validated
- [ ] Edge cases handled
- [ ] Documentation complete
- [ ] Reproducible

### Results Review Checklist

- [ ] Results make intuitive sense
- [ ] Findings support hypothesis
- [ ] Confidence intervals reported
- [ ] Limitations acknowledged
- [ ] Follow-up actions identified
- [ ] Results saved to version control

## Publishing Results

Once experiment is complete:

1. **Create Pull Request** - For code and documentation
2. **Add GitHub Issue** - Link results and identify next steps
3. **Update README** - Document findings and status
4. **Commit Results** - Save all outputs with descriptive commit message
5. **Create Release Note** - For significant findings

## Continuous Improvement

After each module:

1. **Retrospective** - What went well? What could improve?
2. **Lessons Learned** - Document for future modules
3. **Process Improvements** - Update templates and protocols
4. **Knowledge Sharing** - Present findings to team

---

**Ready to run your first experiment?** Start with [Module 1: Edge Threshold Calibration](./modules/01_edge_threshold/README.md)
