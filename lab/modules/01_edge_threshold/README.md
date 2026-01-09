# Module 1: Edge Threshold Calibration

## Overview

This module systematically determines optimal edge thresholds for different bet types across various sports to maximize long-term ROI.

## Objectives

1. **Identify optimal thresholds** - Test edge thresholds from 1% to 10% across sports
2. **Compare performance** - Measure ROI, hit rate, and drawdown for each threshold
3. **Segment analysis** - Determine if thresholds should vary by sport, bet type, or market condition
4. **Generate recommendations** - Produce threshold recommendations for production deployment

## Methodology

### Experimental Design

- **Thresholds tested:** 1.0%, 1.5%, 2.0%, 2.5%, 3.0%, 3.5%, 4.0%, 4.5%, 5.0%+
- **Sports:** NBA, NFL, MLB, NCAAB, NCAAF
- **Bet types:** Moneyline, Spread, Total
- **Historical period:** 2020-2024 (backtesting), 2025 (validation)
- **Sample size:** 1,000+ games per sport per threshold

### Key Metrics

- **Hit Rate** - Percentage of winning predictions
- **ROI** - Return on investment from betting at each threshold
- **Maximum Drawdown** - Largest consecutive loss period
- **Profit Factor** - Gross profit divided by gross loss
- **Expected Value** - Mean profit per bet

### Statistical Validation

- Bootstrap confidence intervals (95% level)
- T-tests for comparing threshold groups
- Effect size analysis (Cohen's d)
- Multiple comparison corrections (Bonferroni)

## Expected Outputs

1. **results/edge_thresholds_by_sport.json** - Threshold performance by sport
2. **results/edge_thresholds_by_bet_type.json** - Threshold performance by bet type
3. **results/optimal_thresholds.json** - Final recommendations
4. **plots/threshold_roi_curve.png** - ROI vs. threshold visualization
5. **plots/threshold_hit_rate_curve.png** - Hit rate vs. threshold visualization

## Running the Module

```bash
# Run single module
python modules/01_edge_threshold/run_experiment.py

# Run with specific parameters
python modules/01_edge_threshold/run_experiment.py --sport NBA --start-year 2020 --end-year 2024

# Generate visualizations
python modules/01_edge_threshold/visualization.py
```

## Status

🔄 In Development

## Dependencies

- core.data_pipeline
- core.simulation_framework
- core.performance_tracker
- core.statistical_validation

## Notes

- Module 1 must complete before Module 2 (thresholds inform iteration optimization)
- Results heavily influence production edge threshold settings
- Historical data validation critical for accuracy
