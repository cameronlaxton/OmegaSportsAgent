# Module 2: Simulation Iteration Optimization

## Overview

Empiracally determines the minimum simulation iterations required for stable probability estimates versus computational cost.

## Objectives

1. **Test convergence** - Run same matchups with 1K, 2.5K, 5K, 10K, 25K, 50K iterations
2. **Measure stability** - Compare probability distributions across iteration counts
3. **Analyze efficiency** - Calculate computation time vs. accuracy trade-off
4. **Optimize deployment** - Recommend iteration counts for different use cases

## Methodology

### Experimental Design

- **Iteration counts:** 1000, 2500, 5000, 10000, 25000, 50000
- **Games tested:** 100+ per sport
- **Sports:** NBA, NFL
- **Convergence metric:** Hellinger distance between distributions
- **Accuracy metric:** Mean absolute error vs. 50K iteration baseline

### Key Metrics

- **Convergence rate** - How quickly probabilities stabilize
- **Stability** - Standard deviation of repeated runs
- **Accuracy** - Deviation from high-iteration baseline
- **Computational efficiency** - Time per iteration
- **Cost-benefit ratio** - Accuracy gain per millisecond

## Expected Outputs

1. **results/iteration_convergence.json** - Convergence metrics by iteration count
2. **results/iteration_efficiency.json** - Time and accuracy metrics
3. **plots/convergence_curves.png** - Probability convergence visualization
4. **plots/efficiency_frontier.png** - Accuracy vs. time trade-off

## Running the Module

```bash
python modules/02_iteration_optimization/run_experiment.py
```

## Status

🔄 In Development

## Dependencies

- Module 1 results (for baseline understanding)
- core.simulation_framework
- core.performance_tracker

## Notes

- Iteration optimization can significantly reduce computational requirements
- Results may vary by sport and game type
- Real-time betting use cases may require different iteration counts
