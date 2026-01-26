# OmegaSports Engine

A modular sports analytics and simulation engine for identifying +EV betting opportunities.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Generate daily bet recommendations
python main.py --task morning_bets --leagues NBA NFL

# Analyze a specific matchup
python main.py --analyze "Team A" "Team B" --league NBA
```

## Project Structure

```
OmegaSportsAgent/
├── main.py              # CLI entry point
├── src/                 # Core modules
│   ├── data/            # Data collection & APIs
│   ├── simulation/      # Monte Carlo & Markov engines
│   ├── betting/         # Odds evaluation & staking
│   ├── analysis/        # Game analysis pipeline
│   └── workflows/       # Scheduled workflows
├── config/              # Configuration files
└── tests/               # Test suite
```

## Supported Leagues

- NBA, NFL, NCAAB, NCAAF (full support)
- MLB, NHL (partial support)

## License

Private repository - authorized use only.
