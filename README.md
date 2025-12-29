# OmegaSports Headless Simulation Engine

> **🚀 For Perplexity Agents:** See **[GUIDE.md](./GUIDE.md)** for complete setup and usage guide

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

## Project Structure

```
omega-sports-engine/
├── GUIDE.md                   # Complete usage guide
├── main.py                    # CLI entry point
├── scraper_engine.py          # Web scraper
├── omega/                     # Core modules
│   ├── simulation/            # Monte Carlo & Markov engines
│   ├── api/                   # High-level analysis APIs
│   ├── data/                  # Data ingestion & APIs
│   ├── betting/               # Edge evaluation & staking
│   ├── analytics/             # League baselines
│   ├── modeling/              # Probability calibration
│   ├── workflows/             # Automated workflows
│   └── utilities/             # Logging & persistence
├── outputs/                   # Simulation results (JSON)
└── logs/                      # Execution logs
```

## Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `PERPLEXITY_API_KEY` | Data enrichment | Optional |
| `BALLDONTLIE_API_KEY` | NBA statistics | Optional |
| `THE_ODDS_API_KEY` | Live odds data | Optional |

## License

Private repository - for authorized use only.
