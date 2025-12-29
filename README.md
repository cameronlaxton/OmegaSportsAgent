# OmegaSports Headless Simulation Engine

A modular, quantitative sports analytics engine designed as a **headless data & simulation pipeline** for Perplexity Spaces/Agents. This engine identifies +EV (positive expected value) wagers by running Monte Carlo simulations and comparing model probabilities against market-implied probabilities.

## Quick Start

### For Perplexity Agent / External AI

**🚀 NEW USERS START HERE:**

1. **[QUICKSTART.md](./QUICKSTART.md)** - Sandbox-ready examples and step-by-step guide
2. **[MODULE_EXECUTION_ORDER.md](./MODULE_EXECUTION_ORDER.md)** - Detailed workflow execution order
3. **[AGENT_INSTRUCTIONS.md](./AGENT_INSTRUCTIONS.md)** - Complete API reference and integration guide

### For Human Developers

See **[AGENT_INSTRUCTIONS.md](./AGENT_INSTRUCTIONS.md)** for complete integration guide.

### CLI Commands

```bash
# Generate daily bet recommendations
python main.py --morning-bets --leagues NBA NFL

# Analyze a specific matchup
python main.py --analyze "Boston Celtics" "Indiana Pacers" --league NBA

# Run simulations for all games in a league
python main.py --simulate NBA --iterations 10000

# Run backtest audit
python main.py --audit --start-date 2025-01-01 --end-date 2025-01-15

# Scrape live sports data
python main.py --scrape "https://www.espn.com/nba/schedule"
```

## Overview

OmegaSports is a **headless engine** - no web interface, no server. All operations:
1. Execute via `main.py` CLI or direct Python imports
2. Output results as JSON/Markdown files to `outputs/`
3. Are designed for consumption by Perplexity Spaces or external agents via GitHub

### Supported Leagues
- **NBA** - Full support
- **NFL** - Full support
- **MLB** - Partial support
- **NHL** - Partial support
- **NCAAB** - Full support
- **NCAAF** - Full support

## Key Features

- **Monte Carlo Simulations**: ≥10,000 iterations per market with league-specific mechanics
- **Crawl4AI Integration**: JavaScript-rendered web scraping for live data
- **Probability Calibration**: Fixes unrealistic probability extremes
- **Correlated Simulation**: SGP-style correlated market support
- **Edge Calculation**: Automated identification of +EV opportunities
- **Kelly Staking**: Bankroll-optimized stake recommendations
- **File-Based Output**: All results saved as JSON for agent parsing

## Project Structure

```
omega-sports-engine/
├── main.py                    # CLI entry point for all operations
├── scraper_engine.py          # Crawl4AI web scraper for live data
├── AGENT_INSTRUCTIONS.md      # Guide for Perplexity Agent integration
├── omega/                     # Core Python modules
│   ├── simulation/            # Monte Carlo & Markov engines
│   │   ├── simulation_engine.py
│   │   ├── correlated_simulation.py
│   │   └── markov_engine.py
│   ├── data/                  # Data ingestion & APIs
│   │   ├── stats_ingestion.py
│   │   ├── schedule_api.py
│   │   ├── odds_scraper.py
│   │   └── injury_api.py
│   ├── betting/               # Edge evaluation & staking
│   │   ├── odds_eval.py
│   │   ├── kelly_staking.py
│   │   └── parlay_tools.py
│   ├── analytics/             # League baselines & analysis
│   ├── modeling/              # Probability calibration
│   ├── workflows/             # Automated workflows
│   │   └── morning_bets.py
│   └── utilities/             # Logging & persistence
├── logs/                      # Execution logs
├── outputs/                   # Simulation results (JSON)
├── data/                      # Cache & historical data
│   ├── cache/                 # API response cache
│   ├── logs/                  # Bet/simulation logs
│   └── outputs/               # Historical picks
├── config/                    # Agent configuration
├── archive/                   # Documentation & module specs
├── requirements.txt           # Python dependencies
└── pyproject.toml             # Project configuration
```

## Output Locations

| Output Type | Location | Format |
|-------------|----------|--------|
| Morning Bets | `outputs/morning_bets_*.json` | JSON |
| Game Analysis | `outputs/analysis_*.json` | JSON |
| League Simulations | `outputs/simulation_*.json` | JSON |
| Audit Reports | `outputs/audit_report_*.json` | JSON |
| Scrape Results | `outputs/scrape_result_*.json` | JSON |
| Execution Logs | `logs/omega_engine.log` | Text |

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (for JavaScript-rendered scraping)
playwright install chromium
```

## Usage Examples

### Python API

```python
# Fetch live data
from scraper_engine import fetch_sports_markdown
result = fetch_sports_markdown("https://www.espn.com/nba/schedule")

# Generate morning bets
from omega.workflows.morning_bets import run_morning_workflow
picks = run_morning_workflow(leagues=["NBA"], n_iter=10000)

# Run game simulation
from omega.simulation.simulation_engine import run_game_simulation
sim = run_game_simulation(projection, n_iter=10000, league="NBA")

# Evaluate bet edge
from omega.betting.odds_eval import edge_percentage
edge = edge_percentage(model_prob=0.62, implied_prob=0.52)
```

### Output Example

```json
{
  "status": "success",
  "date": "2025-12-27",
  "qualified_bets": [
    {
      "matchup": "Phoenix Suns @ New Orleans Pelicans",
      "pick": "New Orleans Pelicans ML",
      "odds": -110,
      "model_prob": 0.6215,
      "edge_pct": 9.77,
      "ev_pct": 18.65,
      "confidence_tier": "A"
    }
  ]
}
```

## Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `PERPLEXITY_API_KEY` | Data enrichment via Perplexity | Optional |
| `BALLDONTLIE_API_KEY` | NBA statistics fallback | Optional |
| `THE_ODDS_API_KEY` | Live odds data | Optional |

## Data Sources

- **ESPN API** (Free): Game schedules, team/player statistics, injury data
- **The Odds API** (Free Tier): Live betting odds
- **Perplexity API**: Narrative generation and data enrichment (optional)
- **Ball Don't Lie API**: NBA player statistics (fallback)

## Core Modules Reference

### Simulation Engine
- `omega.simulation.simulation_engine.run_game_simulation()` - Monte Carlo game simulation
- `omega.simulation.simulation_engine.run_player_simulation()` - Player prop simulation
- `omega.simulation.correlated_simulation` - SGP-style correlated markets

### Data Ingestion
- `omega.data.schedule_api.get_todays_games(league)` - Today's schedule
- `omega.data.stats_scraper.get_team_stats(team, league)` - Team statistics
- `omega.data.odds_scraper.get_upcoming_games(league)` - Current odds
- `omega.data.injury_api.get_injured_players(team, league)` - Injury status

### Betting Logic
- `omega.betting.odds_eval.edge_percentage(model_prob, implied_prob)` - Edge calculation
- `omega.betting.odds_eval.expected_value_percent(model_prob, odds)` - EV calculation
- `omega.betting.kelly_staking.recommend_stake(prob, odds, bankroll)` - Kelly stake

## Documentation

- **[AGENT_INSTRUCTIONS.md](./AGENT_INSTRUCTIONS.md)** - Perplexity Agent integration guide
- **[config/CombinedInstructions.md](./config/CombinedInstructions.md)** - Complete system documentation
- **[archive/docs/ARCHITECTURE.md](./archive/docs/ARCHITECTURE.md)** - System architecture details

## License

Private repository - for authorized use only.
