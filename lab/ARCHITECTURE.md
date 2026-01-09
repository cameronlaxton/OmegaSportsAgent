# OmegaSports Validation Lab: Technical Architecture

## System Overview

The OmegaSports Validation Lab is a modular experimental framework built on three core layers:

1. **Data Pipeline Layer** - Ingestion, curation, and validation of sports data
2. **Simulation Framework Layer** - Monte Carlo simulation engines with standardized interfaces
3. **Analysis & Reporting Layer** - Performance tracking, statistical validation, and result generation

## Architecture Diagram

```
┌────────────────────────────────────────┐
│        EXTERNAL DATA SOURCES                              │
│  ESPN | Pro-Football-Reference | TeamRankings | Covers    │
└────────────────────────────────────────┘
                        │
                        ↓
        ┌───────────────────────────────────┐
        │  DATA PIPELINE LAYER (core/data_pipeline.py)  │
        │                                                  │
        │  ✔️ Data Collection     ✔️ Data Validation     │
        │  ✔️ Data Curation       ✔️ Quality Assurance    │
        └───────────────────────────────────┘
                        │
                        ↓
┌────────────────────────────────────────┐
│   DATABASE LAYER (data/historical/, data/experiments/)      │
│                                                              │
│   - Historical game data (JSON)                              │
│   - Experiment results (JSON)                                │
│   - Cached API responses                                    │
│   - Execution logs                                          │
└────────────────────────────────────────┘
                        │
                        ↓
        ┌───────────────────────────────────┐
        │ SIMULATION FRAMEWORK LAYER                          │
        │ (core/simulation_framework.py)                       │
        │                                                      │
        │ ✔️ Unified Simulation Interface                     │
        │ ✔️ Parameter Management                           │
        │ ✔️ Experiment Orchestration                      │
        └───────────────────────────────────┘
                        │
        ┌───────────────────────────────────┐
        │ 8 EXPERIMENTAL MODULES                             │
        │                                                      │
        │ 01_edge_threshold/          02_iteration_optimization/│
        │ 03_variance_tuning/         04_kelly_validation/     │
        │ 05_model_combination/       06_injury_impact/        │
        │ 07_market_efficiency/       08_backtesting/          │
        └───────────────────────────────────┘
                        │
                        ↓
        ┌───────────────────────────────────┐
        │ ANALYSIS & REPORTING LAYER                        │
        │ (core/performance_tracker.py)                     │
        │                                                      │
        │ ✔️ Performance Metrics                          │
        │ ✔️ Statistical Validation                       │
        │ ✔️ Result Visualization                         │
        │ ✔️ Report Generation                            │
        └───────────────────────────────────┘
                        │
                        ↓
        ┌───────────────────────────────────┐
        │ OUTPUT FORMATS                                    │
        │                                                      │
        │ ✔️ JSON Result Files   ✔️ Markdown Reports          │
        │ ✔️ Jupyter Notebooks   ✔️ CSV Exports              │
        └───────────────────────────────────┘
```

## Core Modules

### Data Pipeline Layer (`core/data_pipeline.py`)

Responsibilities:
- **Data Collection** - Integrate with OmegaSports scraper engine
- **Data Validation** - Validate game data against schema requirements
- **Data Curation** - Maintain historical archives for reproducibility
- **Cache Management** - Cache API responses to reduce external dependencies

Key Classes:
- `DataPipeline` - Main data ingestion interface
- `DataValidator` - Validates game data against schema
- `HistoricalDatabase` - Manages historical game archive
- `CacheManager` - Handles API response caching

### Simulation Framework Layer (`core/simulation_framework.py`)

Responsibilities:
- **Unified Interface** - Abstract OmegaSports engine details
- **Parameter Management** - Standardize configuration across modules
- **Experiment Orchestration** - Coordinate module execution
- **Result Collection** - Aggregate results from simulations

Key Classes:
- `SimulationFramework` - Unified simulation interface
- `ExperimentConfig` - Configuration for experiment parameters
- `ResultCollector` - Aggregates simulation results
- `ExperimentOrchestrator` - Coordinates multi-module experiments

### Performance Tracking Layer (`core/performance_tracker.py`)

Responsibilities:
- **Metric Calculation** - Compute accuracy, ROI, CLV, and risk metrics
- **Statistical Analysis** - Apply statistical tests to validate results
- **Visualization** - Generate charts and graphs for results
- **Report Generation** - Produce comprehensive analysis reports

Key Classes:
- `PerformanceTracker` - Main metrics calculation engine
- `AccuracyMetrics` - Hit rate, calibration, CLV calculations
- `ProfitabilityMetrics` - ROI, EV, bankroll growth tracking
- `StatisticalValidator` - Significance testing and confidence intervals

### Experiment Logger (`core/experiment_logger.py`)

Responsibilities:
- **Execution Logging** - Track all experiment activity
- **Result Persistence** - Save results to versioned storage
- **Error Handling** - Graceful error recovery and reporting
- **Debugging Support** - Comprehensive logging for troubleshooting

Key Classes:
- `ExperimentLogger` - Main logging interface
- `ExperimentRegistry` - Tracks experiment metadata
- `ResultPersistence` - Handles file I/O and versioning

### Statistical Validation (`core/statistical_validation.py`)

Responsibilities:
- **Significance Testing** - Determine if results exceed random chance
- **Confidence Intervals** - Bootstrap confidence interval calculation
- **Effect Size** - Measure practical significance of improvements
- **Multiple Comparison** - Account for multiple testing corrections

Key Functions:
- `bootstrap_confidence_interval()` - Calculate CI from samples
- `permutation_test()` - Test significance via permutation
- `effect_size()` - Measure practical significance
- `multiple_comparison_correction()` - Bonferroni/Holm correction

## Data Schema

All experiments use standardized JSON schemas for consistency:

### Game Data Schema
```json
{
  "game_id": "nba_2025_jan_01_bos_vs_ind",
  "date": "2025-01-01",
  "sport": "NBA",
  "home_team": "Boston Celtics",
  "away_team": "Indiana Pacers",
  "home_score": 115,
  "away_score": 108,
  "moneyline": {
    "home": {"sportsbook": "DraftKings", "price": -150},
    "away": {"sportsbook": "DraftKings", "price": 130}
  },
  "spread": {
    "home": {"sportsbook": "DraftKings", "value": -4.5, "price": -110},
    "away": {"sportsbook": "DraftKings", "value": 4.5, "price": -110}
  },
  "total": {
    "over": {"sportsbook": "DraftKings", "value": 220.5, "price": -110},
    "under": {"sportsbook": "DraftKings", "value": 220.5, "price": -110}
  }
}
```

### Experiment Result Schema
```json
{
  "experiment_id": "module_01_edge_threshold_001",
  "module": "01_edge_threshold",
  "execution_date": "2025-12-31",
  "duration_seconds": 3600,
  "parameters": {
    "edge_threshold": 3.0,
    "sport": "NBA",
    "iterations": 10000
  },
  "results": {
    "qualified_bets": 42,
    "total_bets": 156,
    "hit_rate": 0.586,
    "roi": 0.048,
    "max_drawdown": -0.127
  },
  "statistics": {
    "confidence_level": 0.95,
    "confidence_interval_lower": 0.041,
    "confidence_interval_upper": 0.055,
    "p_value": 0.002
  },
  "status": "completed"
}
```

## Module Structure

Each experimental module follows a standardized structure:

```
modules/01_edge_threshold/
├── __init__.py
├── run_experiment.py          # Main experiment entry point
├── analysis.py                # Results analysis
├── visualization.py           # Result plots and charts
├── config.py                  # Module configuration
├── test_module.py             # Unit tests
└── README.md                  # Module documentation
```

Standard module interface:

```python
class Module:
    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.logger = ExperimentLogger()
        self.framework = SimulationFramework()
        self.tracker = PerformanceTracker()
    
    def run(self) -> ExperimentResult:
        """Run the experiment."""
        self.logger.start_experiment()
        try:
            results = self._execute_experiment()
            self.logger.log_results(results)
            return results
        finally:
            self.logger.end_experiment()
    
    def _execute_experiment(self) -> ExperimentResult:
        """Implementation-specific experiment logic."""
        raise NotImplementedError
    
    def analyze_results(self) -> dict:
        """Analyze experiment results."""
        raise NotImplementedError
    
    def visualize_results(self) -> None:
        """Generate result visualizations."""
        raise NotImplementedError
```

## Execution Flow

### Daily Experiment Execution

```
1. GitHub Actions triggers daily_experiments.yml workflow
2. Checkout code and setup environment
3. Run run_all_modules.py
   a. Initialize lab infrastructure
   b. Execute Module 1-8 sequentially
   c. Collect and validate results
   d. Generate reports
4. Commit results to GitHub
5. Notify user of completion
```

### Individual Module Execution

```
1. User runs: python modules/01_edge_threshold/run_experiment.py
2. Module loads configuration and initializes infrastructure
3. Data Pipeline fetches required historical data
4. Simulation Framework executes experiments
5. Performance Tracker calculates metrics
6. Results saved to data/experiments/
7. Visualizations and reports generated
```

## Data Flow

### Input Data Flow

```
OmegaSports Engine
     │
     │ Game data
     │ Historical results
     │ Betting lines
     ↓
Data Pipeline
     │
     │ Validated data
     │
     ↓
Historical Database
     │
     │ Query by date/sport
     │
     ↓
Experimental Modules
```

### Output Data Flow

```
Experimental Modules
     │
     │ Simulation results
     │
     ↓
Performance Tracker
     │
     │ Calculated metrics
     │
     ↓
Report Generator
     │
     │ JSON, CSV, Markdown
     │
     ↓
GitHub Repository
```

## Dependency Management

### Internal Dependencies

```
core/data_pipeline.py
    └─ Depends on: None (foundation)

core/simulation_framework.py
    └─ Depends on: data_pipeline

core/performance_tracker.py
    └─ Depends on: simulation_framework

core/statistical_validation.py
    └─ Depends on: None (utilities)

core/experiment_logger.py
    └─ Depends on: None (utilities)

Modules (01-08)
    └─ Depend on: All core modules
```

### External Dependencies

- `pandas` - Data manipulation
- `numpy` - Numerical computing
- `scipy` - Statistical functions
- `matplotlib` - Visualization
- `requests` - HTTP requests
- `pytest` - Testing framework
- `python-dotenv` - Environment configuration

## Error Handling Strategy

1. **Data Validation Errors** - Log and skip corrupted data
2. **Simulation Errors** - Retry with increased iterations
3. **Network Errors** - Use cached data and continue
4. **Computation Errors** - Graceful failure with detailed logging
5. **File I/O Errors** - Ensure data persistence and recovery

## Performance Considerations

- **Parallel Execution** - Run modules in parallel when possible
- **Caching Strategy** - Cache expensive computations
- **Database Optimization** - Index historical data by date/sport
- **Memory Management** - Stream large datasets to avoid OOM

## Monitoring & Observability

Each module logs:
- Execution start/end timestamps
- Parameter values
- Intermediate results
- Error conditions
- Performance metrics

All logs aggregated to `data/logs/` with daily rotation.
