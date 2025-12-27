# OMEGA Sports Betting Simulation - Architecture Documentation

## Overview

OMEGA is a modular sports analytics engine designed for quantitative sports betting analysis. The system uses a Python-in-LLM pattern where instruction modules (`.md` files) contain executable Python code blocks that are extracted and run in a sandbox environment.

## System Architecture

### Core Design Principles

1. **Modularity**: Each module is self-contained with clear responsibilities
2. **League-Agnostic Core**: Common abstractions support multiple sports
3. **Deterministic Simulations**: Reproducible results via seeded random number generation
4. **Module-Based Calculations**: All quantitative outputs must come from module functions, not ad-hoc LLM reasoning
5. **Sandbox-Compatible**: No external APIs or databases; file-based storage only

### Entry Points

The system has three main entry points:

1. **Pre-Game Analysis**: Full simulation and bet recommendation pipeline
2. **Live Betting**: In-game probability updates and edge recalculation
3. **Model Audit**: Performance tracking and calibration

### Module Loading Order

Modules must be loaded in this exact order:

1. `modules/foundation/model_config.md` - Configuration and thresholds
2. `modules/foundation/league_config.md` - League-specific configuration parameters
3. `modules/foundation/core_abstractions.md` - League-agnostic core abstractions (Team, Player, Game, State)
4. `modules/analytics/universal_analytics.md` - Universal models (Pythagorean, Elo/Glicko)
5. `modules/analytics/league_baselines.md` - League-specific baselines (Four Factors, EPA, RE, xG)
6. `modules/analytics/market_analysis.md` - Market intelligence
7. `modules/modeling/realtime_context.md` - Context normalization
8. `modules/adjustments/injury_adjustments.md` - Injury impact modeling
9. `modules/modeling/projection_model.md` - Baseline and contextual projections
10. `modules/modeling/probability_calibration.md` - Probability calibration system
11. `modules/simulation/simulation_engine.md` - Monte Carlo simulations
12. `modules/simulation/correlated_simulation.md` - Correlated simulation for SGP support
13. `modules/betting/odds_eval.md` - Odds conversion and EV calculation
14. `modules/betting/parlay_tools.md` - Correlation and parlay evaluation
15. `modules/betting/kelly_staking.md` - Bankroll management
16. `modules/utilities/model_audit.md` - Performance tracking
17. `modules/utilities/data_logging.md` - Data logging
18. `modules/utilities/sandbox_persistence.md` - Persistent bet tracking and backtesting
19. `modules/utilities/output_formatter.md` - Standardized output generation

## Directory Structure

```
omega-betting-agent/
├── modules/                    # Core execution modules
│   ├── foundation/            # Foundation modules (load first)
│   ├── analytics/             # Analytics modules
│   ├── modeling/              # Modeling modules
│   ├── simulation/            # Simulation modules
│   ├── betting/               # Betting logic modules
│   ├── adjustments/           # Adjustment modules
│   └── utilities/             # Utility modules
├── config/                    # Configuration files
│   ├── CombinedInstructions.md
│   └── AGENT_SPACE_INSTRUCTIONS.md
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md
│   ├── bet_log_template.md
│   └── SETUP.md
├── data/                      # Data files (gitignored)
│   ├── logs/                  # Generated logs
│   ├── exports/               # CSV exports
│   └── audits/                # Audit reports
├── examples/                  # Example data files
├── .gitignore
├── README.md
└── MODULE_LOAD_ORDER.md
```

## Module Responsibilities

### Foundation Modules

#### `modules/foundation/model_config.md`
- Edge thresholds (spread/total ≥ 3%, moneyline ≥ 3%, props ≥ 5%)
- Variance scalars per league/stat
- Blend weights for baseline vs. context
- Confidence tier definitions
- Simulation parameters

#### `modules/foundation/league_config.md`
- League-specific parameters (periods, clock rules, scoring)
- Typical possession counts
- Key numbers (NFL: 3, 7; NBA: 3, 7, etc.)
- Home advantage factors

#### `modules/foundation/core_abstractions.md`
- `Team`, `Player`, `Game`, `State` base classes
- League-specific subclasses
- Common interfaces for all leagues

### Analytics Modules

#### `modules/analytics/universal_analytics.md`
- Pythagorean expectation (configurable exponent per league)
- Elo/Glicko rating systems
- Home-field/court/ice adjustments
- K-factor configuration

#### `modules/analytics/league_baselines.md`
- NBA: Four Factors (eFG%, TOV%, ORB%, FTR)
- NFL: EPA interface (simplified, with TODOs for regression-based)
- MLB: Run Expectancy interface (simplified RE table)
- NHL: xG interface (simplified formula)

#### `modules/analytics/market_analysis.md`
- Market intelligence gathering
- Line movement tracking
- Public betting percentages (if available)

### Modeling Modules

#### `modules/modeling/realtime_context.md`
- Weather normalization (temperature, wind, precipitation)
- Rest adjustments (days rest, back-to-back, travel)
- Pace adjustments
- Venue factors (altitude, home advantage)

#### `modules/modeling/projection_model.md`
- Baseline projections from historical data
- Context-adjusted projections
- Blend weights application
- Variance calculation

#### `modules/modeling/probability_calibration.md`
- Shrinkage toward 0.5
- Reasonable caps (max 0.85, min 0.15)
- Historical performance mapping (when available)
- Isotonic calibration (if historical data exists)

### Simulation Modules

#### `modules/simulation/simulation_engine.md`
- Monte Carlo simulation wrapper
- League-specific mechanics:
  - NFL: Drive-based
  - NBA: Possession-based
  - MLB: Inning-based
  - NHL: Shift-based
- Distribution selection (Normal vs. Poisson)
- Minimum 10,000 iterations per market

#### `modules/simulation/correlated_simulation.md`
- Team-level outcome simulation first
- Player stat derivation via allocation rules
- Correlation maintenance for SGP support
- Usage rate, target share, TOI allocation

### Betting Modules

#### `modules/betting/odds_eval.md`
- American to decimal odds conversion
- Implied probability calculation
- Expected value calculation
- Edge percentage

#### `modules/betting/parlay_tools.md`
- Joint probability calculation
- Correlation adjustments
- EV calculation for parlays
- Correlation matrix validation

#### `modules/betting/kelly_staking.md`
- Full Kelly fraction calculation
- Fractional Kelly (quarter-Kelly default)
- Bankroll caps
- Drawdown controls
- Unit conversion

### Adjustment Modules

#### `modules/adjustments/injury_adjustments.md`
- League-aware injury redistributions
- Team projection adjustments
- Player projection adjustments
- Usage reallocation

### Utility Modules

#### `modules/utilities/model_audit.md`
- Brier score calculation
- Closing Line Value (CLV) tracking
- ROI calculation
- Win rate tracking
- Breakdowns by league, confidence tier, bet type

#### `modules/utilities/data_logging.md`
- Log simulation outputs
- Log bet recommendations
- Load past logs
- Export to CSV

#### `modules/utilities/sandbox_persistence.md`
- Persistent bet tracking for Perplexity Spaces
- Swappable storage backend (default: `data/logs/` and `data/exports/`)
- File attachment persistence strategy
- Backtesting and audit capabilities
- Thread fallback for data retrieval

#### `modules/utilities/output_formatter.md`
- Standardized table generation
- Narrative analysis formatting
- Required Output Format compliance
- Module citation tracking

## Data Flow

```
Input (Game/Player Data)
    ↓
Context Normalization (realtime_context)
    ↓
Injury Adjustments (injury_adjustments)
    ↓
Baseline Projections (projection_model)
    ↓
Context-Adjusted Projections (projection_model)
    ↓
Probability Calibration (probability_calibration)
    ↓
Monte Carlo Simulation (simulation_engine)
    ↓
Edge Calculation (odds_eval)
    ↓
Edge Filtering (model_config thresholds)
    ↓
Stake Recommendation (kelly_staking)
    ↓
Output Formatting (output_formatter)
    ↓
Required Tables (Required Output Format)
```

## Data Storage

### Storage Strategy (Perplexity Spaces)

**Swappable Storage Backend**: Default paths are `data/logs/` and `data/exports/` (persist in Spaces if uploaded/synced).

Implemented in `modules/utilities/sandbox_persistence.md`:

- **Swappable Storage Backend**: Default paths are `data/logs/` and `data/exports/`
  - `data/logs/bet_log.json` - All bet recommendations and results
  - `data/logs/simulation_log.json` - All simulation results
  - `data/logs/audit_log.json` - Audit history
  - `data/exports/BetLog.csv` - Cumulative bet log export
  - Files persist in Spaces if uploaded/synced

- **Persistence Strategy**: Three-layer approach
  - Session: Write to `data/logs/` and `data/exports/` during task execution
  - End of session: Export files as attachments for long-term storage
  - Future sessions: Load from previous task attachments or Space files

### Data Interfaces

- `log_simulation_result()` - Log simulation results (to session storage)
- `log_bet_recommendation()` - Log bet recommendations (to session storage)
- `update_pending_bets_and_export()` - Update results and export cumulative CSV
- `load_from_thread_fallback()` - Load data from previous task attachments
- `export_to_csv()` - CSV export (BetLog.csv format supported)
- `run_backtest_audit()` - Run audit on loaded bet data

## League Support

### Currently Supported

- **NFL**: Drive-based simulation, EPA metrics, weather impact
- **NBA**: Possession-based, Four Factors, pace adjustments
- **MLB**: Inning-based, run expectancy, weather critical
- **NHL**: Shift-based, xG metrics, goalie adjustments
- **NCAAF/NCAAB**: High-variance, tempo-based

### Adding New Leagues

1. Add league config to `modules/foundation/league_config.md` (periods, clock rules, scoring, key numbers)
2. Add league-specific baseline to `modules/analytics/league_baselines.md` (if applicable)
3. Add variance scalars to `modules/foundation/model_config.md`
4. Update distribution selection in `modules/simulation/simulation_engine.md`
5. Add context multipliers in `modules/modeling/realtime_context.md`
6. Add allocation rules to `modules/simulation/correlated_simulation.md` (for player props)

## Output Protocol

**CRITICAL**: All analysis outputs MUST follow this exact structure. 

**Required Output:**
1. Full Suggested Summary Table (all markets)
 1a. Game Bets Table (spread/total/ML only/Game Props)
 1b. Player Props Table
2. SGP Mentionables *if applicable for the day*
3. Context Drivers Narrative Briefing
4. Risk & Stake Table (if staking recommendations made)
5. Game/Performance/Metrics/Context Narrative Breakdown Analysis for ending.

### Narrative Requirements

- Analytical, concise tone
- Explicit module function citations
- Clear statement of assumptions
- Risk caveats
- Explicit threshold satisfaction statements

## GitHub Integration

### Repository Structure

The repository is organized for easy navigation and module loading:
- Modules organized by category in `modules/` subdirectories
- Configuration files in `config/`
- Documentation in `docs/`
- Generated data files in `data/` (gitignored)

### Perplexity Space Integration

1. Space reads `config/CombinedInstructions.md` from GitHub
2. Space loads modules in order from `modules/` directories
3. Space executes Python blocks extracted from .md files
4. Space generates results and saves to `data/logs/` and `data/exports/` (default paths)
5. Space delivers files as attachments
6. User commits attachments to GitHub (manual or via MCP)

### Module Path References

All module references use paths relative to repository root:
- `modules/foundation/model_config.md`
- `modules/analytics/universal_analytics.md`
- etc.

See `MODULE_LOAD_ORDER.md` for complete list.

## Extension Points

### Adding New Models

1. Create new module in appropriate `modules/` subdirectory
2. Add to module loading order in `config/CombinedInstructions.md`
3. Update `MODULE_LOAD_ORDER.md`
4. Document in this file

### Adding New Bet Types

1. Extend `modules/betting/odds_eval.md` for new odds formats
2. Update edge thresholds in `modules/foundation/model_config.md`
3. Add simulation support in `modules/simulation/simulation_engine.md`

### Adding New Metrics

1. Add calculation to appropriate analytics module
2. Integrate into projection pipeline
3. Update output formatter if needed

## References

- `config/CombinedInstructions.md` - Primary instruction file
- `MODULE_LOAD_ORDER.md` - Module loading reference
- `docs/SETUP.md` - GitHub setup and integration guide
- Module-specific `.md` files - Detailed function documentation

