# OmegaSports Validation Lab

> **Systematic Experimental Framework for Sports Betting Edge Detection**

A comprehensive research and testing platform for validating, optimizing, and improving the OmegaSports quantitative sports betting engine. This lab implements rigorous experimental methodology to calibrate model parameters, evaluate betting strategies, and ensure consistent long-term profitability.

## ✅ Issue Resolution Confirmed

**Recent Update (Jan 2, 2026):** All questions from the original issue about repo linking, database storage, and code organization have been fully resolved by PR #9. See:
- **[ISSUE_CONFIRMATION_SUMMARY.md](ISSUE_CONFIRMATION_SUMMARY.md)** - Executive summary of resolution
- **[ISSUE_RESOLUTION_CONFIRMATION.md](ISSUE_RESOLUTION_CONFIRMATION.md)** - Detailed question-by-question mapping
- **Verification Script:** Run `python scripts/verify_issue_resolution.py` to confirm all deliverables

## 🎯 New Here? [START HERE →](START_HERE.md)

**First time in this repository?** Read **[START_HERE.md](START_HERE.md)** for:
- Clear explanation of what this repo does
- How it relates to the OmegaSports Engine
- Navigation guide for 30+ documentation files
- Quick answers to common questions
- Recommended scripts to use (and which to ignore)

## 🎯 Mission

Transform the OmegaSports production engine into a scientific research platform through:
- **Systematic validation** of edge detection algorithms
- **Parameter optimization** across all model components
- **Statistical rigor** in all performance claims
- **Continuous improvement** through iterative experimentation
- **Reproducible research** with full documentation and version control

## 📊 Lab Modules

The lab is organized into 8 experimental modules, each addressing a critical aspect of sports betting optimization:

| Module | Focus | Status |
|--------|-------|--------|
| **Module 1** | Edge Threshold Calibration | ✅ Complete |
| **Module 2** | Simulation Iteration Optimization | 🔄 Stub Ready |
| **Module 3** | Variance Scalar Tuning | 🔄 Planned |
| **Module 4** | Kelly Criterion Validation | 🔄 Planned |
| **Module 5** | Model Combination Testing | 🔄 Planned |
| **Module 6** | Injury Impact Quantification | 🔄 Planned |
| **Module 7** | Market Efficiency Analysis | 🔄 Planned |
| **Module 8** | Backtesting Framework | 🔄 Planned |

## 📁 Project Structure

```
OmegaSports-Validation-Lab/
├── README.md                          # Project overview
├── ARCHITECTURE.md                    # Technical architecture
├── INSTALLATION.md                    # Setup and dependencies
├── EXPERIMENTS.md                     # Experiment protocols
│
├── modules/                           # Lab experimental modules
│   ├── 01_edge_threshold/             # Module 1: Edge Threshold Calibration
│   ├── 02_iteration_optimization/     # Module 2: Iteration Optimization
│   ├── 03_variance_tuning/            # Module 3: Variance Tuning
│   ├── 04_kelly_validation/           # Module 4: Kelly Criterion
│   ├── 05_model_combination/          # Module 5: Model Ensembles
│   ├── 06_injury_impact/              # Module 6: Injury Impact
│   ├── 07_market_efficiency/          # Module 7: Market Analysis
│   └── 08_backtesting/                # Module 8: Backtesting Framework
│
├── core/                              # Core lab infrastructure
│   ├── data_pipeline.py               # Data ingestion and curation
│   ├── simulation_framework.py         # Unified simulation interface
│   ├── performance_tracker.py          # Performance metrics tracking
│   ├── experiment_logger.py            # Experiment logging system
│   └── statistical_validation.py       # Statistical testing utilities
│
├── utils/                             # Utilities and helpers
│   ├── date_utils.py                  # Date and time utilities
│   ├── format_utils.py                # Output formatting
│   ├── viz_utils.py                   # Visualization helpers
│   └── config.py                      # Lab configuration
│
├── data/                              # Data storage
│   ├── historical/                    # Historical game data
│   ├── experiments/                   # Experiment results
│   ├── logs/                          # Execution logs
│   └── cache/                         # Cached API responses
│
├── notebooks/                         # Jupyter notebooks for analysis
│   ├── 01_data_exploration.ipynb
│   ├── 02_baseline_analysis.ipynb
│   ├── 03_module_results.ipynb
│   └── 04_recommendations.ipynb
│
├── tests/                             # Test suite
│   ├── test_data_pipeline.py
│   ├── test_simulation_framework.py
│   ├── test_performance_tracker.py
│   └── test_statistical_validation.py
│
├── requirements.txt                   # Python dependencies
├── setup.py                           # Package installation
└── .github/
    └── workflows/
        ├── daily_experiments.yml      # Automated daily runs
        ├── tests.yml                  # Test automation
        └── report_generation.yml      # Result reporting
```

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.10+
python --version

# Git
git --version
```

### Installation

```bash
# Clone repository
git clone https://github.com/cameronlaxton/OmegaSports-Validation-Lab.git
cd OmegaSports-Validation-Lab

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/
```

### Running Experiments

```bash
# Run all modules
python run_all_modules.py

# Run specific module
python run_all_modules.py --module 01

# Continue on errors
python run_all_modules.py --skip-errors

# Load historical data
python scripts/load_and_validate_games.py --sports NBA NFL

# Check existing data
python scripts/load_and_validate_games.py --check-only
```

## 📚 Documentation

- **[PHASE_2_STATUS.md](./PHASE_2_STATUS.md)** - **NEW** - Current Phase 2 status and next steps
- **[PHASE_1_COMPLETE.md](./PHASE_1_COMPLETE.md)** - Phase 1 completion summary and achievements
- **[PHASE_2_KICKOFF.md](./PHASE_2_KICKOFF.md)** - Phase 2 launch guide and daily checklist
- **[PHASE_2_PLANNING.md](./PHASE_2_PLANNING.md)** - Detailed 4-week Phase 2 timeline
- **[PHASE_2_QUICKSTART.md](./PHASE_2_QUICKSTART.md)** - Daily reference and troubleshooting
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Technical design and system architecture
- **[INSTALLATION.md](./INSTALLATION.md)** - Detailed setup instructions
- **[EXPERIMENTS.md](./EXPERIMENTS.md)** - Experiment protocols and methodologies
- **[PHASE_2_QUICKSTART.md](./PHASE_2_QUICKSTART.md)** - Quick reference for daily Phase 2 tasks

## 🧪 Experimental Modules Overview

### Module 1: Edge Threshold Calibration
Systematically determines optimal edge thresholds for different bet types across various sports to maximize long-term ROI.

**Key Metrics:** ROI by threshold level, hit rate, maximum drawdown
**Expected Outcome:** Dynamic threshold recommendations for production deployment

### Module 2: Simulation Iteration Optimization
Empiricially determines minimum simulation iterations required for stable probability estimates vs. computational cost.

**Key Metrics:** Probability convergence rate, computational efficiency, accuracy by iteration count
**Expected Outcome:** Optimized iteration counts for different use cases

### Module 3: Variance Scalar Tuning
Calibrates variance parameters to match real-world outcome distributions across sports and game contexts.

**Key Metrics:** Kolmogorov-Smirnov test scores, distribution matching, calibration error
**Expected Outcome:** Sport-specific and context-aware variance parameters

### Module 4: Kelly Criterion Validation
Tests whether full Kelly, fractional Kelly, or alternative staking methods maximize bankroll growth with acceptable risk.

**Key Metrics:** Compound annual growth rate, maximum drawdown, probability of ruin
**Expected Outcome:** Optimal staking strategy recommendations

### Module 5: Model Combination Testing
Explores whether ensemble methods combining multiple models improve accuracy beyond single models.

**Key Metrics:** Ensemble accuracy vs. individual models, correlation between models
**Expected Outcome:** Multi-model combination recommendations

### Module 6: Injury Impact Quantification
Develops systematic framework for quantifying and incorporating player injury impacts into probability adjustments.

**Key Metrics:** Accuracy improvement with injury adjustment, impact by player type
**Expected Outcome:** Injury adjustment factors by position and severity

### Module 7: Market Efficiency Analysis
Investigates market inefficiencies to understand where and when betting opportunities exist.

**Key Metrics:** Market timing value, segment efficiency analysis, closing line value
**Expected Outcome:** Strategic focus recommendations for maximum profitability

### Module 8: Backtesting Framework
Implements rigorous backtesting with proper train-test separation to validate all findings.

**Key Metrics:** Out-of-sample performance, statistical significance, reproducibility
**Expected Outcome:** Validated recommendations for production deployment

## 📈 Success Metrics

The lab evaluates success across multiple dimensions:

**Accuracy Improvements:**
- 2-3% absolute improvement in hit rate
- 5-10% reduction in probability calibration error
- 55%+ positive CLV against sharp closing lines

**Profitability Targets:**
- 5%+ ROI on recommended bets
- 90%+ expected value realization
- Maximum drawdown under 20 units

**Operational Efficiency:**
- 30%+ reduction in simulation time
- 99%+ automated experiment uptime
- 95%+ statistical confidence in all improvements

## 🔗 Integration with OmegaSports Engine

This lab is designed as a companion to the [OmegaSports Engine](https://github.com/cameronlaxton/OmegaSports Engine):

- **Data Source:** Leverages OmegaSports scraper engine for live data collection
- **Simulation Base:** Builds on OmegaSports Monte Carlo simulation infrastructure
- **Output Format:** Uses OmegaSports schema and JSON output formats
- **Deployment Target:** Optimizations feed back into OmegaSports production system

## 📊 Historical Data Loading

The lab includes a comprehensive historical data loading system that goes beyond ESPN's scheduler API:

### Features

- **Historical Game Data (2020-2024):** Complete game results with scores
- **Comprehensive Statistics:** Team stats, player performance, advanced metrics
- **Betting Lines:** Moneyline, spreads, totals with historical odds
- **Multiple Sports:** NBA, NFL, NCAAB, NCAAF support
- **Intelligent Caching:** 30-day retention for efficient re-fetching
- **Retry Logic:** Exponential backoff for failed requests

### Quick Start

```bash
# Load all sports (2020-2024)
python scripts/load_and_validate_games.py

# Load specific sports
python scripts/load_and_validate_games.py --sports NBA NFL

# Custom date range
python scripts/load_and_validate_games.py --start-year 2022 --end-year 2024
```

**Documentation:**
- [Historical Data Implementation Guide](HISTORICAL_DATA_IMPLEMENTATION.md)
- [Scripts Documentation](scripts/README.md)
- [Data Structure Guide](data/README.md)

## 📅 Development Timeline

- **Phase 1 (Weeks 1-2):** Infrastructure setup and database initialization
- **Phase 2 (Weeks 3-6):** Baseline establishment and historical replay
- **Phase 3 (Weeks 7-20):** Experimental execution of all 8 modules
- **Phase 4 (Weeks 21-24):** Integration, deployment, and continuous monitoring

## 🤝 Contributing

Contributions welcome! Areas for enhancement:
- Additional experimental modules
- Advanced statistical methods
- Visualization improvements
- Documentation expansion
- Performance optimization

## 📝 License

Private repository - for authorized use only.

## 📞 Contact

Cameron Laxton - [LinkedIn](https://www.linkedin.com/in/cameron-laxton-13956986/)

---

**Status:** ✅ Phase 1 Complete - Ready for Phase 2  
**Last Updated:** December 31, 2025  
**Current Phase:** Transition to Phase 2 (Baseline Establishment)  
**Phase 2 Start Date:** January 6, 2026
