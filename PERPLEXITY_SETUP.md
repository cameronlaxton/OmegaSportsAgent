# Perplexity Agent Setup Guide

**Last Updated:** December 29, 2025  
**For:** Perplexity AI Sandbox IDE Mode

This guide helps Perplexity AI agents get started with the OmegaSports engine quickly.

---

## 🚀 Quick Setup (3 Steps)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs all required Python packages (NumPy, Pandas, Pydantic, Playwright, etc.)

### Step 2: Verify Installation

```bash
python test_engine.py
```

Expected output: `✅ All tests passed! Engine is ready for use.`

### Step 3: Run Example

```bash
python example_complete_workflow.py
```

This runs a complete analysis workflow and saves results to `outputs/`

---

## 📚 Documentation Map

Start here based on your needs:

### For Quick Start
- **[QUICKSTART.md](./QUICKSTART.md)** - Sandbox-ready examples with web scraping

### For Step-by-Step Execution
- **[MODULE_EXECUTION_ORDER.md](./MODULE_EXECUTION_ORDER.md)** - Detailed workflow guide with code examples

### For Complete Reference
- **[AGENT_INSTRUCTIONS.md](./AGENT_INSTRUCTIONS.md)** - Full API reference, troubleshooting, and integration guide

### For Project Overview
- **[README.md](./README.md)** - Project structure, features, and CLI commands

---

## ✅ Pre-Flight Checklist

Before running analysis, verify these items:

- [ ] Python 3.10+ installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Test suite passes (`python test_engine.py`)
- [ ] Directories created: `logs/`, `outputs/`, `data/logs/`, `data/outputs/`

---

## 🎯 Common Use Cases

### Use Case 1: Analyze a Game with Manual Data

```python
from omega.schema import GameData, BettingLine
from omega.simulation.simulation_engine import run_game_simulation
from omega.betting.odds_eval import edge_percentage, implied_probability

# 1. Create game data
game = GameData(
    sport="NBA",
    league="NBA",
    home_team="Boston Celtics",
    away_team="Indiana Pacers",
    moneyline={
        "home": BettingLine(sportsbook="DraftKings", price=-150),
        "away": BettingLine(sportsbook="DraftKings", price=130)
    }
)

# 2. Define projections
projection = {
    "off_rating": {"Boston Celtics": 118.5, "Indiana Pacers": 115.2},
    "def_rating": {"Boston Celtics": 110.2, "Indiana Pacers": 112.5},
    "pace": {"Boston Celtics": 99.5, "Indiana Pacers": 101.3},
    "league": "NBA",
    "variance_scalar": 1.0
}

# 3. Run simulation
sim = run_game_simulation(projection, n_iter=10000, league="NBA")

# 4. Calculate edge
home_prob = sim["true_prob_a"]
implied_prob = implied_probability(-150)
edge = edge_percentage(home_prob, implied_prob)

print(f"Edge: {edge:.2f}%")
```

### Use Case 2: Run Full Morning Workflow

```bash
python main.py --morning-bets --leagues NBA
```

Output saved to: `outputs/morning_bets_*.json`

### Use Case 3: Test a Specific Matchup

```bash
python main.py --analyze "Boston Celtics" "Indiana Pacers" --league NBA
```

Output saved to: `outputs/analysis_*.json`

---

## 🛠️ CLI Commands Reference

```bash
# Generate daily bets
python main.py --morning-bets --leagues NBA NFL

# Analyze matchup
python main.py --analyze "Team A" "Team B" --league NBA

# Simulate all games in league
python main.py --simulate NBA --iterations 10000

# Scrape live sports data from the internet
python main.py --scrape "https://www.espn.com/nba/schedule"

# Run backtest audit
python main.py --audit --start-date 2025-01-01 --end-date 2025-01-15

# Run tests
python test_engine.py

# Run example workflow
python example_complete_workflow.py
```

---

## 📁 File Locations

| File Type | Location | Description |
|-----------|----------|-------------|
| Outputs | `outputs/*.json` | Analysis results |
| Logs | `logs/omega_engine.log` | Execution logs |
| Bet Logs | `data/logs/bet_log.json` | Bet tracking |
| Examples | `example_complete_workflow.py` | Working example |
| Tests | `test_engine.py` | Validation suite |

---

## 🌐 Data Collection with scraper_engine.py

**IMPORTANT:** Perplexity should use `scraper_engine.py` to scrape and parse live sports data from the internet. This is the PRIMARY method for obtaining real-time stats, odds, and game information.

### How to Use the Scraper

```python
# Scrape live sports data from websites
from scraper_engine import fetch_sports_markdown

# Fetch ESPN NBA schedule with live data
result = fetch_sports_markdown("https://www.espn.com/nba/schedule")

if result["success"]:
    markdown_content = result["markdown"]
    # Parse the markdown to extract game data, odds, stats, etc.
    print(f"Fetched {len(markdown_content)} characters of data")
else:
    print(f"Error: {result.get('error')}")
```

### Scraper Features

The `scraper_engine.py` provides:
- **JavaScript Rendering** - Uses Playwright to handle dynamic content
- **Fallback Mode** - Automatically falls back to requests for simple pages
- **Markdown Conversion** - Converts HTML to clean, parseable markdown
- **Data Extraction** - Parse odds, stats, schedules, and player data from websites

### Manual Data Fallback (Only if scraping fails)

If internet access is unavailable or scraping fails, use manual data as a fallback:

```python
from omega.schema import GameData, BettingLine
game = GameData(
    sport="NBA",
    league="NBA",
    home_team="Team A",
    away_team="Team B",
    moneyline={"home": BettingLine(sportsbook="DK", price=-150)}
)
```

## ⚠️ Execution Considerations

When running in Perplexity sandbox:

1. **Internet Access** - Use `scraper_engine.py` to fetch live data from sports websites
2. **Limited Execution Time** - Keep simulations to 10,000 iterations
3. **File Persistence** - Results saved to `outputs/` directory
4. **No Database** - Use JSON file logging instead

---

## 🐛 Troubleshooting

### Problem: Module import fails
```bash
# Solution: Install dependencies
pip install -r requirements.txt
```

### Problem: Permission denied on logs/
```python
# Solution: Create directories manually
import os
os.makedirs("logs", exist_ok=True)
os.makedirs("outputs", exist_ok=True)
```

### Problem: Network error when scraping
```python
# Solution: Check error message and retry with different approach
result = fetch_sports_markdown("https://www.espn.com/nba/schedule")
if not result["success"]:
    # Try with fallback method or different URL
    print(f"Scraping error: {result.get('error')}")
    # As last resort, use manual game data (see QUICKSTART.md for examples)
```

### Problem: Simulation returns unexpected keys
```python
# The simulation returns:
# - true_prob_a, true_prob_b (win probabilities)
# - team_a_wins, team_b_wins (simulation counts)
# - a_scores, b_scores (score distributions)

# Example:
sim = run_game_simulation(projection, n_iter=1000, league="NBA")
home_win_prob = sim["true_prob_a"]  # ← Use this
```

---

## 📞 Support

For detailed help, consult:

1. **[QUICKSTART.md](./QUICKSTART.md)** - Quick examples
2. **[MODULE_EXECUTION_ORDER.md](./MODULE_EXECUTION_ORDER.md)** - Step-by-step guide
3. **[AGENT_INSTRUCTIONS.md](./AGENT_INSTRUCTIONS.md)** - Full documentation
4. **Check logs:** `logs/omega_engine.log`

---

## ✨ Next Steps

1. ✅ Run `python test_engine.py` to verify setup
2. ✅ Run `python example_complete_workflow.py` to see it in action
3. ✅ Read [QUICKSTART.md](./QUICKSTART.md) for your first analysis
4. ✅ Explore [MODULE_EXECUTION_ORDER.md](./MODULE_EXECUTION_ORDER.md) for advanced usage

---

**Ready to start?** Run `python example_complete_workflow.py` now!
