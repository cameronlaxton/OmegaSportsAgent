# OmegaSports Headless Simulation Engine

> **🚀 For Perplexity Agents:** See **[GUIDE.md](./GUIDE.md)** for complete setup and usage guide  
> **🗺️ Architecture:** See **[SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md)** for structure, data flows, and automation.

A modular, quantitative sports analytics engine designed as a **headless data & simulation pipeline** for Perplexity Spaces/Agents. This engine identifies +EV (positive expected value) wagers by running Monte Carlo simulations and comparing model probabilities against market-implied probabilities.

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
- **[example_complete_workflow.py](./example_complete_workflow.py)** - Working example
- **[example_markov_simulation.py](./example_markov_simulation.py)** - Markov simulation example

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

## Automation (GitHub Actions)
- Daily predictions: run `python main.py --morning-bets --leagues NBA NFL`, commit `outputs/`, `data/`.
- Weekly calibration: run `lab/core/calibration_runner.py --use-agent-outputs --output ../config/calibration/nba_latest.json`, commit updated calibration pack.
- Optional daily grading: run `python -m omega.workflows.daily_grading`.

## Environment Variables

| Variable | Purpose | Required | Default |
|----------|---------|----------|---------|
| `PERPLEXITY_API_KEY` | Data enrichment | Optional | None |
| `BALLDONTLIE_API_KEY` | NBA & NFL statistics (All-Star tier) | Optional | Configured |
| `ODDS_API_KEY` | Live odds data | Optional | Configured |

**Note**: API keys for Ball Don't Lie (NBA & NFL) and The Odds API are pre-configured in `omega/foundation/api_config.py`. You can override them by setting environment variables:

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
from omega.foundation.api_config import check_api_keys
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
