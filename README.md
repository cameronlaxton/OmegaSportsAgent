# OmegaSports Headless Simulation Engine

> **🚀 For Perplexity Agents:** See **[GUIDE.md](./GUIDE.md)** for complete setup and usage guide  
> **🗺️ Architecture:** See **[SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md)** for structure, data flows, and automation.

A modular, quantitative sports analytics engine designed as a **headless data & simulation pipeline** for Perplexity Spaces/Agents. This engine identifies +EV (positive expected value) wagers by running Monte Carlo simulations and comparing model probabilities against market-implied probabilities.

## Operator Notes (no LLM instructions required)
- This repo is now human-operated; LLM-facing instruction packs have been removed.
- Run via CLI entrypoint `main.py` (see Canonical Tasks below); outputs are written to `outputs/` and `data/outputs/`.
- Calibration packs live under `config/calibration/`; a universal pack with inline league overrides is the default.
- Scraping is handled by `scraper_engine.py` plus data adapters under `src/data/`.

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (for scraping)
playwright install chromium

# Verify installation
python test_engine.py
```

### Usage

**Canonical Tasks (Recommended):**
```bash
# Generate daily bet recommendations
python main.py --task morning_bets --leagues NBA NFL

# Run weekly calibration
python main.py --task weekly_calibration --league NBA

# Run nightly audit (grading)
python main.py --task nightly_audit
```

**Legacy Commands (Still Supported):**
```bash
# Generate daily bet recommendations
python main.py --morning-bets --leagues NBA NFL

# Analyze a specific matchup
python main.py --analyze "Boston Celtics" "Indiana Pacers" --league NBA

# Analyze player props with Markov simulation
python main.py --markov-props --league NBA --min-edge 5.0

# Scrape live sports data
python main.py --scrape "https://www.espn.com/nba/schedule"
```

### Documentation

- **[GUIDE.md](./GUIDE.md)** - Complete setup, scraping, simulation, and analysis guide
- **[CONTRIBUTING.md](./CONTRIBUTING.md)** - Development workflow and git guidelines
- **[test_engine.py](./test_engine.py)** - Test suite
- **[examples/example_complete_workflow.py](./examples/example_complete_workflow.py)** - Working example
- **[examples/example_markov_simulation.py](./examples/example_markov_simulation.py)** - Markov simulation example

## Overview

OmegaSports is a **headless engine** with no web interface. All operations execute via CLI and output JSON/Markdown files.

## Supported Leagues

- **NBA** - Full support
- **NFL** - Full support  
- **MLB** - Partial support
- **NHL** - Partial support
- **NCAAB** - Full support
- **NCAAF** - Full support

For detailed usage and examples, see **[GUIDE.md](./GUIDE.md)**.

## Key Features

- **Web Scraping**: JavaScript-rendered scraping via `scraper_engine.py`
- **Monte Carlo Simulations**: ≥10,000 iterations per market
- **Markov Play-by-Play Simulation**: Strategic player prop analysis with detailed game modeling
- **Edge Calculation**: Automated +EV identification
- **Kelly Staking**: Bankroll-optimized recommendations
- **File-Based Output**: All results saved as JSON

## Project Structure (Monorepo)

```
OmegaSportsAgent-1/
├── SYSTEM_ARCHITECTURE.md      # Single-source architecture doc
├── main.py                     # Agent CLI entry point
├── omega/                      # Agent source modules
├── config/                     # Calibration packs + loader
├── outputs/                    # Daily recommendations JSON
├── data/                       # Runtime logs/exports/outputs
├── lab/                        # Validation Lab (calibration/audit)
└── tests/                      # Agent tests
```

## Migration (Post-Refactor)

If you're upgrading from the old structure, run the migration script to consolidate legacy data:

```bash
# Dry run (see what would be migrated)
python lab/scripts/migrate_legacy_data.py --dry-run

# Perform migration
python lab/scripts/migrate_legacy_data.py
```

This consolidates:
- Bet logs from multiple locations → `data/exports/BetLog.csv`
- Predictions from multiple locations → `data/logs/predictions.json`
- Output files from `data/outputs/` → `outputs/`
- Tuned parameters → `config/calibration/tuned_parameters_legacy.json` (reference)

## Automation (GitHub Actions)
- Daily predictions: run `python main.py --task morning_bets --leagues NBA NFL`, commit `outputs/`, `data/`.
- Weekly calibration: run `python main.py --task weekly_calibration --league NBA`, commit updated calibration pack.
- Optional daily grading: run `python main.py --task nightly_audit`.

## Environment Variables

| Variable | Purpose | Required | Default |
|----------|---------|----------|---------|
| `PERPLEXITY_API_KEY` | Data enrichment | Optional | None |
| `BALLDONTLIE_API_KEY` | NBA & NFL statistics (All-Star tier) | Optional | Configured |
| `ODDS_API_KEY` | Live odds data | Optional | Configured |

**Note**: API keys for Ball Don't Lie (NBA & NFL) and The Odds API are pre-configured in `src/foundation/api_config.py`. You can override them by setting environment variables:

```bash
export BALLDONTLIE_API_KEY="your_custom_key"
export ODDS_API_KEY="your_custom_key"
```

**Ball Don't Lie All-Star Tier Features**:
- NBA endpoint: `https://api.balldontlie.io/v1`
- NFL endpoint: `https://nfl.balldontlie.io/`
- Teams, games, player stats, and season averages for both leagues

To check current API key status:
```python
from src.foundation.api_config import check_api_keys
print(check_api_keys())
```

## Contributing

Interested in contributing? See **[CONTRIBUTING.md](./CONTRIBUTING.md)** for:
- Development setup instructions
- Git workflow guidelines (fetching, branching, syncing)
- Code style standards
- Testing requirements
- Pull request process

## License

Private repository - for authorized use only.
