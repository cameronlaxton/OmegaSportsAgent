# OmegaSports Validation Lab - Quick Start Guide

## Welcome! 🚀

You now have a complete experimental framework for validating and optimizing the OmegaSports betting engine. This guide will get you running your first experiment in 30 minutes.

## Prerequisites

- Python 3.10 or higher
- Git
- 10GB free disk space
- Stable internet connection

## 5-Minute Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/cameronlaxton/OmegaSports-Validation-Lab.git
cd OmegaSports-Validation-Lab
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Verify Installation

```bash
python -m pytest tests/ -q
```

Expected output: All tests pass ✓

### Step 5: Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings if needed
```

## 🚀 Running Your First Experiment

### Option A: Full Framework Demo (Recommended)

```bash
# Run the main demo script
python run_all_modules.py
```

This will:
- Initialize the lab infrastructure
- Demonstrate the experiment framework
- Show how modules are orchestrated
- Generate sample results

### Option B: Manual Module Execution

```bash
# Run individual module
python modules/01_edge_threshold/run_experiment.py
```

### Option C: Interactive Jupyter Notebook

```bash
# Start Jupyter Lab
jupyter lab

# Open: notebooks/00_getting_started.ipynb
```

Then:
1. Click on notebook
2. Run all cells (Shift+Enter)
3. Follow along with guided setup

## 📄 Documentation Map

### For Quick Starters (You are here!)

- **GETTING_STARTED.md** - This file. Quick start guide.
- **README.md** - Project overview and features.

### For Implementation Details

- **ARCHITECTURE.md** - Technical system design and components.
- **INSTALLATION.md** - Detailed setup for different environments.
- **EXPERIMENTS.md** - Standardized experiment protocols.

### For Module Details

- **modules/01_edge_threshold/README.md** - First experiment details
- **modules/02_iteration_optimization/README.md** - Second experiment
- (More modules added during development)

## 📇 File Structure Reference

```
OmegaSports-Validation-Lab/
├── core/                    # Lab infrastructure
│   ├── data_pipeline.py      # Data ingestion
│   ├── simulation_framework.py # Simulation engine
│   ├── performance_tracker.py  # Metrics tracking
│   ├── experiment_logger.py    # Result logging
│   └── statistical_validation.py # Stats utilities
│
├── modules/                # Experimental modules (8 total)
│   ├── 01_edge_threshold/
│   ├── 02_iteration_optimization/
│   ├── 03_variance_tuning/
│   ├── ...
│   └── 08_backtesting/
│
├── utils/                  # Utilities
│   └── config.py              # Configuration management
│
├── data/                   # Data storage
│   ├── historical/            # Game data (auto-created)
│   ├── experiments/           # Results (auto-created)
│   ├── logs/                  # Execution logs (auto-created)
│   └── cache/                 # API cache (auto-created)
│
├── notebooks/              # Jupyter analysis notebooks
├── tests/                  # Test suite
├── reports/                # Generated reports (auto-created)
│
├── README.md               # Project overview
├── GETTING_STARTED.md      # This file
├── ARCHITECTURE.md         # Technical design
├── INSTALLATION.md         # Setup instructions
├── EXPERIMENTS.md          # Experiment protocols
├── requirements.txt        # Python dependencies
├── setup.py                # Package installer
├── .env.example            # Environment template
└── .gitignore              # Git configuration
```

## ☓ Common Tasks

### Run Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_core.py -v

# Run with coverage
pytest --cov=core --cov=modules tests/
```

### View Results

```bash
# List recent experiment results
ls -lah data/experiments/

# View result file
cat data/experiments/experiment_*.json | python -m json.tool

# View logs
tail -f data/logs/*.log
```

### Update Dependencies

```bash
# Update all packages
pip install -r requirements.txt --upgrade

# Freeze current environment
pip freeze > requirements-locked.txt
```

### Run Jupyter Notebook

```bash
# Start Jupyter Lab
jupyter lab

# Open browser to http://localhost:8888
# Navigate to notebooks/ directory
```

## 🐝 Troubleshooting

### "ModuleNotFoundError: No module named 'core'"

**Solution:** Ensure virtual environment is activated

```bash
# Verify activation (prompt should show (venv))
which python  # macOS/Linux
where python  # Windows

# If not activated:
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate      # Windows
```

### "No such file or directory: '.env'"

**Solution:** Copy environment template

```bash
cp .env.example .env
```

### "Permission denied" errors

**Solution:** Ensure permissions are correct

```bash
chmod +x venv/bin/activate
chmod +x run_all_modules.py
```

### Tests fail with import errors

**Solution:** Reinstall in development mode

```bash
pip install -e .
pip install -r requirements.txt
pytest tests/
```

## 🖤 System Architecture Overview

```
    ┌─ OmegaSports Engine (external)
    │
    └─> Data Pipeline (ingestion & validation)
         │
         └─> Simulation Framework (unified interface)
              │
              └─> 8 Experimental Modules
                   │
                   └─> Performance Tracker (metrics)
                        │
                        └─> Statistical Validator (testing)
                             │
                             └─> Experiment Logger (persistence)
                                  │
                                  └─> GitHub Repository (version control)
```

## 🐖 Lab Phases

### 🎉 Phase 1: Infrastructure Setup (COMPLETE)

Completed:
- Repository created and structured
- Core infrastructure implemented
- Documentation complete
- Testing framework in place

Status: **Ready for Phase 2**

### 🔄 Phase 2: Baseline Establishment (STARTING)

Planned:
- Data pipeline implementation
- Historical data processing
- Baseline metrics calculation
- Module 1 execution

Duration: 4 weeks (January 2026)

### 🧪 Phase 3: Experimental Execution (PLANNED)

Planned:
- Modules 2-8 implementation
- Full experiment suite
- Advanced analysis

Duration: 14 weeks

### 🚀 Phase 4: Deployment (PLANNED)

Planned:
- Production integration
- Continuous monitoring
- Real-time optimization

Duration: 4 weeks

## 📞 Getting Help

### Documentation

1. **Start here:** [README.md](./README.md)
2. **Setup help:** [INSTALLATION.md](./INSTALLATION.md)
3. **Technical details:** [ARCHITECTURE.md](./ARCHITECTURE.md)
4. **Experiment guide:** [EXPERIMENTS.md](./EXPERIMENTS.md)

### Community

- **Issues:** [GitHub Issues](https://github.com/cameronlaxton/OmegaSports-Validation-Lab/issues)
- **Discussions:** Use issue comments for discussion
- **Contact:** Cameron Laxton

### Related Resources

- **OmegaSports Engine:** [https://github.com/cameronlaxton/OmegaSportsAgent](https://github.com/cameronlaxton/OmegaSportsAgent)
- **Sports Betting Concepts:** See references in documentation

## 👋 Next Steps

### Immediate (Next 5 minutes)

1. ✅ Complete installation above
2. ✅ Run: `python -m pytest tests/`
3. ✅ Explore: `ls -la modules/`

### Short-term (Today)

1. Read: [README.md](./README.md) (5 min)
2. Read: [ARCHITECTURE.md](./ARCHITECTURE.md) (10 min)
3. Review: Module 1 [README](./modules/01_edge_threshold/README.md) (5 min)

### Medium-term (This week)

1. Set up OmegaSports engine integration
2. Run first data pipeline test
3. Process sample historical data
4. Generate baseline metrics

### Long-term (Next month)

1. Complete Phase 2: Baseline establishment
2. Run Module 1: Edge Threshold Calibration
3. Document findings
4. Plan Phase 3 experiments

## 💆 Best Practices

### Development

- Always use virtual environment
- Run tests before committing
- Document experimental changes
- Follow existing code style
- Update README when adding features

### Data Management

- Validate all input data
- Cache expensive computations
- Version control results
- Document data sources
- Maintain data integrity checks

### Experimentation

- Define hypothesis before experimenting
- Document methodology
- Validate results independently
- Report confidence intervals
- Acknowledge limitations

## 🎭 Demo Commands

```bash
# Setup (one-time)
git clone https://github.com/cameronlaxton/OmegaSports-Validation-Lab.git
cd OmegaSports-Validation-Lab
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Verify installation
python -m pytest tests/ -q

# Run demo
python run_all_modules.py

# Explore results
ls data/experiments/
cat data/logs/*.log

# Open notebooks
jupyter lab notebooks/
```

## 🙋 Questions?

The lab is fully documented with:
- Comprehensive README files
- Detailed architecture documentation
- Step-by-step installation guide
- Standardized experiment protocols
- Working code examples

Start with the [README.md](./README.md) for high-level overview, then dive into specific documentation based on your needs.

---

**Congratulations!** You have a fully functional experimental framework for sports betting optimization. 🎉

**Happy experimenting!** 🚀
