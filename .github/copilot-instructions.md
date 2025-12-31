# Copilot Instructions - OmegaSportsAgent

## Repository Overview

**OmegaSportsAgent** is a headless sports analytics and simulation engine built in Python. It performs Monte Carlo and Markov chain simulations for sports betting analysis, identifying positive expected value (+EV) wagers by comparing model probabilities against market-implied probabilities.

### Key Characteristics
- **Language**: Python 3.11+ (tested with Python 3.12.3)
- **Type**: CLI-based data processing and simulation pipeline (no web UI)
- **Size**: Small (~3.1MB, 73 Python files)
- **Architecture**: Modular, headless engine with file-based output (JSON/Markdown)
- **Primary Use Case**: Sports betting analysis via Monte Carlo/Markov simulations

### Supported Leagues
- **Full Support**: NBA, NFL, NCAAB, NCAAF
- **Partial Support**: MLB, NHL

---

## Build & Test Instructions

### Prerequisites

**Python Version**: Python 3.11+ required (Python 3.12.3 tested and working)

### Environment Setup (ALWAYS DO THIS FIRST)

**ALWAYS run these commands in this exact order before making any code changes:**

```bash
# 1. Install Python dependencies (REQUIRED - takes ~60 seconds)
pip install -r requirements.txt

# 2. Install Playwright browsers for web scraping (REQUIRED - takes ~60 seconds)
playwright install chromium
```

**IMPORTANT**: These steps are REQUIRED even if you've run them before in a previous session. The environment is not persistent.

### Validation & Testing

**ALWAYS run tests before and after making changes to ensure nothing breaks:**

```bash
# Run test suite (takes ~0.7 seconds)
python test_engine.py

# Expected output: "✅ All tests passed! Engine is ready for use."
# Tests validate: environment setup, module imports, schema validation, 
# simulation, betting analysis, configuration, and CLI
```

**Test the main CLI:**
```bash
# Verify main CLI works
python main.py --help

# Expected: Shows usage and examples
```

**Test example workflow (optional validation):**
```bash
# Run complete workflow example (takes ~2-3 seconds)
python example_complete_workflow.py

# Expected: "Workflow Complete" message
```

### Running Validations After Changes

**After making code changes, ALWAYS:**

1. Run `python test_engine.py` to ensure core functionality works
2. If you modified CLI/main.py: Run `python main.py --help`
3. If you modified simulation/betting logic: Run `python example_complete_workflow.py`

### No Build Step Required

This is a Python project with no compilation step. Changes to `.py` files take effect immediately.

### Timing Expectations

- **Dependency installation**: ~60 seconds (pip install)
- **Playwright browsers**: ~60 seconds (playwright install)
- **Test suite**: ~0.7 seconds (python test_engine.py)
- **Example workflow**: ~2-3 seconds
- **Simple CLI commands**: <1 second

---

## Project Structure

### Root Directory Files

```
/
├── main.py                          # CLI entry point - main command interface
├── scraper_engine.py                # Web scraper using Playwright for live data
├── test_engine.py                   # Test suite - ALWAYS run before/after changes
├── example_complete_workflow.py     # Working example of complete analysis
├── example_markov_simulation.py     # Markov chain simulation example
├── example_autonomous_calibration.py # Calibration system example
├── test_calibration.py              # Calibration tests
├── test_markov_api.py               # Markov API tests
├── requirements.txt                 # Python dependencies
├── pyproject.toml                   # Project metadata
├── package.json                     # Node.js dependencies (@octokit/rest)
├── alembic.ini                      # Database migration config
├── final_validation.sh              # Comprehensive validation script
├── README.md                        # Project overview
├── GUIDE.md                         # Complete usage guide (623 lines)
├── CALIBRATION_AUTOMATION.md        # Calibration setup guide
├── CHANGES_SUMMARY.md               # Documentation changes log
└── .gitignore                       # Git ignore patterns
```

### Core Module Structure (`omega/`)

```
omega/
├── schema.py                        # Core data structures (GameData, BettingLine, PropBet)
├── foundation/                      # Base configuration (NO dependencies)
│   ├── model_config.py             # Edge thresholds, simulation params
│   ├── league_config.py            # League-specific settings (periods, overtime)
│   └── core_abstractions.py        # Team class
├── data/                           # Data ingestion APIs
│   ├── schedule_api.py             # Get today's games
│   ├── stats_scraper.py            # Team statistics
│   ├── odds_scraper.py             # Betting odds
│   ├── injury_api.py               # Player injuries
│   ├── nba_stats_api.py            # NBA-specific stats
│   └── player_game_log.py          # Player performance logs
├── simulation/                     # Monte Carlo & Markov engines
│   ├── simulation_engine.py        # Main Monte Carlo simulation (10k+ iterations)
│   ├── markov_engine.py            # Play-by-play Markov chains
│   └── correlated_simulation.py    # Correlated market simulations
├── betting/                        # Edge calculation & staking
│   ├── odds_eval.py                # Edge percentage, implied probability
│   ├── kelly_staking.py            # Kelly criterion bankroll management
│   ├── correlation_engine.py       # Correlation analysis
│   └── parlay_tools.py             # Parlay calculations
├── calibration/                    # Autonomous learning system
│   ├── auto_calibrator.py          # Main calibration coordinator
│   ├── parameter_tuner.py          # Parameter auto-tuning
│   └── performance_tracker.py      # Prediction/outcome tracking
├── api/                            # High-level analysis APIs
│   ├── unified_game_analysis.py    # Complete game analysis
│   ├── markov_analysis.py          # Player prop analysis with Markov
│   ├── props_slate.py              # Multiple props analysis
│   └── derivative_edges_api.py     # Derivative market edges
├── workflows/                      # Automated workflows
│   ├── morning_bets.py             # Daily bet recommendations
│   └── scheduler.py                # Scheduled tasks (morning/results/calibration)
├── analytics/                      # League-specific analytics
│   ├── league_baselines.py         # League baseline metrics
│   └── universal_analytics.py      # Cross-league analytics
├── modeling/                       # Probability modeling
│   ├── probability_calibration.py  # Probability adjustments
│   └── projection_model.py         # Team projections
├── utilities/                      # Helper utilities
│   ├── output_formatter.py         # JSON/Markdown formatting
│   ├── data_logging.py             # Bet logging
│   └── sandbox_persistence.py      # Cache management
├── db/                            # Database (PostgreSQL via SQLAlchemy)
│   ├── database.py                 # Database connection
│   ├── models.py                   # SQLAlchemy models
│   └── alembic/                    # Database migrations
└── narratives/                    # Narrative generation
    └── narrative_engine.py         # Bet narrative text generation
```

### Module Loading Order (IMPORTANT)

**ALWAYS import modules in this order to avoid circular dependencies:**

1. **Foundation** (no dependencies): `omega.schema`, `omega.foundation.*`
2. **Data** (depends on foundation): `omega.data.*`
3. **Simulation** (depends on foundation + data): `omega.simulation.*`
4. **Betting** (depends on simulation): `omega.betting.*`
5. **Utilities** (depends on all above): `omega.utilities.*`

### Output Directories

```
outputs/                            # Simulation results (JSON/Markdown)
├── morning_bets_*.json             # Daily bet recommendations
├── analysis_*.json                 # Game analysis results
├── simulation_*.json               # Simulation data
├── markov_props_*.json             # Markov prop analysis
└── audit_report_*.json             # Backtest audits

logs/                               # Execution logs
└── omega_engine.log                # Main log file

data/                               # Persistent data
├── config/                         # Configuration
│   └── tuned_parameters.json       # Auto-tuned parameters
├── logs/                           # Calibration logs
│   ├── predictions.json            # Logged predictions
│   └── scheduler/                  # Scheduled task logs
└── outputs/                        # Archived outputs
```

**NOTE**: `outputs/`, `logs/`, and most of `data/` are in `.gitignore` - do NOT commit these directories.

---

## Configuration Files

### Edge Thresholds & Simulation Parameters

Located in `omega/foundation/model_config.py`:
- Default edge thresholds (moneyline: 3%, spread: 3%, total: 3%, props: 5%)
- Simulation iterations (default: 10,000)
- Kelly fraction for staking (default: 0.25)

### League-Specific Configuration

Located in `omega/foundation/league_config.py`:
- NBA: 4 periods, 5 minutes overtime
- NFL: 4 quarters, 10 minutes overtime
- MLB: 9 innings (no overtime concept)
- NHL: 3 periods, 5 minutes overtime

### Calibration Configuration

Located in calibration system:
- Auto-tuning enabled/disabled
- Tuning strategy (Adaptive, Conservative, Gradient Descent)
- Performance thresholds (ROI alerts, Brier score limits)

---

## Common Commands

### Analysis Commands

```bash
# Generate daily bet recommendations for NBA & NFL
python main.py --morning-bets --leagues NBA NFL

# Analyze specific matchup
python main.py --analyze "Boston Celtics" "Indiana Pacers" --league NBA

# Analyze player props with Markov simulation
python main.py --markov-props --league NBA --min-edge 5.0

# Simulate game with play-by-play Markov chains
python main.py --markov-game "Boston Celtics" "Indiana Pacers" --league NBA

# Scrape live sports data
python main.py --scrape "https://www.espn.com/nba/schedule"

# Run backtest audit
python main.py --audit --start-date 2025-01-01 --end-date 2025-01-15
```

### Workflow Commands

```bash
# Run scheduled morning bets workflow
python omega/workflows/scheduler.py morning

# Update bet results (after games complete)
python omega/workflows/scheduler.py results

# Run weekly calibration
python omega/workflows/scheduler.py calibration
```

---

## Key Technical Details

### Dependencies

**Core Libraries** (from requirements.txt):
- `numpy>=2.0.0` - Numerical computations
- `pandas>=2.0.0` - Data manipulation
- `pydantic>=2.0.0` - Data validation
- `sqlalchemy>=2.0.0` - Database ORM
- `playwright>=1.40.0` - Web scraping with JavaScript rendering
- `beautifulsoup4>=4.12.0` - HTML parsing
- `requests>=2.31.0,<2.32.3` - HTTP requests

**Database**:
- PostgreSQL via `psycopg2-binary>=2.9.0`
- Alembic for migrations

**AI/ML** (optional):
- `crawl4ai>=0.4.0` - Advanced web crawling

### Data Flow

1. **Data Collection**: `scraper_engine.py` fetches live data via Playwright
2. **Data Validation**: `scraper_engine.validate_game_data()` validates structure
3. **Simulation**: `omega.simulation.simulation_engine.run_game_simulation()` runs Monte Carlo
4. **Edge Analysis**: `omega.betting.odds_eval.edge_percentage()` calculates edges
5. **Filtering**: Compare against thresholds from `omega.foundation.model_config`
6. **Output**: Save to `outputs/` directory as JSON/Markdown

### Simulation Types

**Monte Carlo** (for game outcomes):
- Default: 10,000 iterations
- Used for: Moneyline, spread, total bets
- Fast: ~0.1-0.5 seconds per game

**Markov Chain** (for player props):
- Play-by-play state transitions
- Tracks individual player involvement
- Used for: Player points, rebounds, assists, receiving yards
- Slower: ~1-3 seconds per player

---

## Common Pitfalls & Workarounds

### Import Errors

**Problem**: `ModuleNotFoundError` when importing omega modules

**Solution**: 
- Ensure you're in the repository root directory
- Run `pip install -r requirements.txt` first
- Check module loading order (foundation → data → simulation → betting → utilities)

### Playwright Errors

**Problem**: `Playwright browser not found` or network errors during `playwright install`

**Solution**:
- ALWAYS run `playwright install chromium` after installing dependencies
- If blocked by proxy, Playwright automatically retries from Microsoft CDN
- Wait for full download (~110 MB for chromium)

### Missing Output Directories

**Problem**: `FileNotFoundError` when saving outputs

**Solution**: 
- The test suite creates required directories automatically
- Manually create: `mkdir -p logs outputs data/logs data/outputs data/config`

### Test Failures

**Problem**: Tests fail with simulation errors

**Solution**:
- Ensure all dependencies installed (`pip install -r requirements.txt`)
- Check Python version (must be 3.11+)
- Review test output for specific module import failures

### Calibration Data Persistence

**Problem**: Tuned parameters not persisting across runs

**Solution**:
- Ensure `data/config/` directory exists
- Check file permissions on `data/config/tuned_parameters.json`
- Don't delete or gitignore `data/config/` directory

---

## Validation Checklist

**Before committing changes, ALWAYS verify:**

1. ✅ Run `python test_engine.py` - all tests must pass
2. ✅ Run `python main.py --help` - CLI must work
3. ✅ Check for import errors - no circular dependencies
4. ✅ Verify output files created correctly in `outputs/`
5. ✅ Review changes don't break module loading order
6. ✅ Ensure no secrets/credentials added to code
7. ✅ Check `.gitignore` excludes `outputs/`, `logs/`, `__pycache__/`

**Optional deeper validation:**
- Run `./final_validation.sh` for comprehensive checks
- Run `python example_complete_workflow.py` for end-to-end test
- Test specific features modified

---

## CI/CD & Automation

**Current Setup**: 
- No GitHub Actions workflows currently configured
- No automated CI/CD pipeline
- Manual validation via test scripts

**Automation Scripts**:
- `final_validation.sh` - Comprehensive validation (checks modules, tests, docs, CLI)
- `scripts/cron_runner.sh` - Scheduled task runner for production deployments

**Future CI/CD**: When setting up GitHub Actions, recommended workflow:
```yaml
# .github/workflows/test.yml (EXAMPLE - not currently present)
- Run: pip install -r requirements.txt
- Run: playwright install chromium  
- Run: python test_engine.py
- Run: python main.py --help
```

---

## Documentation Resources

**Primary Documentation** (read these for deep understanding):
- `README.md` - Project overview, quick start (100 lines)
- `GUIDE.md` - Complete usage guide, all features (1000+ lines) - **MOST COMPREHENSIVE**
- `CALIBRATION_AUTOMATION.md` - Autonomous calibration setup

**Code Examples**:
- `example_complete_workflow.py` - Full analysis workflow
- `example_markov_simulation.py` - Markov chain simulation
- `example_autonomous_calibration.py` - Calibration system usage
- `test_engine.py` - Test suite with usage patterns

**Module Documentation** (in archive/):
- Older architectural docs preserved in `archive/` directory
- Contains detailed module specifications (may be outdated)

---

## Important Notes for Coding Agents

### DO:
- ✅ **ALWAYS** run `pip install -r requirements.txt` first
- ✅ **ALWAYS** run `playwright install chromium` after pip install
- ✅ **ALWAYS** run `python test_engine.py` before and after changes
- ✅ Follow module loading order (foundation → data → simulation → betting)
- ✅ Save outputs to `outputs/` directory
- ✅ Use existing test patterns from `test_engine.py`
- ✅ Import from `omega.schema` for data structures
- ✅ Import from `omega.foundation` for configuration
- ✅ Check GUIDE.md for API usage examples

### DON'T:
- ❌ **NEVER** commit `outputs/`, `logs/`, or `__pycache__/` directories
- ❌ **NEVER** skip dependency installation (environment is not persistent)
- ❌ **NEVER** assume modules load in any order (respect dependency hierarchy)
- ❌ Don't add new dependencies without updating `requirements.txt`
- ❌ Don't modify edge thresholds without understanding impact
- ❌ Don't break the CLI interface in `main.py`
- ❌ Don't add pytest/unittest frameworks (this project uses custom test script)

### Performance Expectations:
- Test suite should complete in < 1 second
- Single game simulation: < 1 second (Monte Carlo)
- Player prop simulation: 1-3 seconds (Markov)
- Morning bets workflow: 5-30 seconds depending on # of games

---

## Trust These Instructions

These instructions have been **validated** by running all commands and verifying:
- ✅ Dependency installation works (pip + playwright)
- ✅ Test suite passes (7/7 tests in 0.7s)
- ✅ Example workflows execute successfully
- ✅ CLI commands function correctly
- ✅ Module imports follow correct order
- ✅ Output directories structure confirmed

**Only search for additional information if:**
- These instructions are incomplete for your specific task
- You encounter errors not covered in "Common Pitfalls"
- You need deeper understanding of specific algorithms/logic
- Documentation appears outdated or contradictory

Otherwise, **trust these instructions** and follow them precisely to minimize exploration time and command failures.
