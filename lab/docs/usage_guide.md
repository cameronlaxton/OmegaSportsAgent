# Usage Guide: OmegaSports Validation Lab

**Version:** 1.0.0  
**Last Updated:** 2026-01-05  
**Prerequisites:** Python 3.10+, SQLite, numpy, scipy

---

## Quick Start

### 1. Check Database Status

```bash
# See what data you have
python cli.py db-status
```

**Output:**
```
DATABASE STATUS
Games:                9,093
Player Props:         884,922
Odds History:         3,570
...
DATA COVERAGE:
  NBA: 9,093 games (2019-10-22 to 2025-06-22)
```

### 2. Run Repository Audit

```bash
# Review repo cleanup and recommendations
python cli.py audit
```

### 3. Run Calibration (Dry-Run First)

```bash
# Test run without saving results
python cli.py backtest \
    --league NBA \
    --start-date 2023-01-01 \
    --end-date 2023-12-31 \
    --dry-run
```

### 4. Generate Calibration Pack

```bash
# Full calibration with output
python cli.py generate-pack \
    --league NBA \
    --output calibration_pack_nba.json
```

---

## CLI Reference

### Command: `audit`

**Purpose:** Show repository audit summary

**Usage:**
```bash
python cli.py audit
```

**Output:** Summary of deprecated scripts, data status, recommended actions

---

### Command: `db-status`

**Purpose:** Show database statistics and data coverage

**Usage:**
```bash
python cli.py db-status [--db PATH]
```

**Options:**
- `--db PATH`: Database path (default: `data/sports_data.db`)

**Example:**
```bash
python cli.py db-status
```

---

### Command: `backtest`

**Purpose:** Run backtesting and calibration pipeline

**Usage:**
```bash
python cli.py backtest \
    --league LEAGUE \
    --start-date YYYY-MM-DD \
    --end-date YYYY-MM-DD \
    [--train-split FRACTION] \
    [--output PATH] \
    [--dry-run]
```

**Options:**
- `--league`: League to calibrate (NBA, NFL, etc.) - **Required**
- `--start-date`: Backtest window start date - Default: `2020-01-01`
- `--end-date`: Backtest window end date - Default: `2024-12-31`
- `--train-split`: Fraction for training (0.0-1.0) - Default: `0.7`
- `--db`: Database path - Default: `data/sports_data.db`
- `--output`: Output path for calibration pack - Optional
- `--dry-run`: Don't save results - Optional

**Examples:**

```bash
# Full 5-year calibration
python cli.py backtest \
    --league NBA \
    --start-date 2020-01-01 \
    --end-date 2024-12-31

# Quick test (1 year, dry-run)
python cli.py backtest \
    --league NBA \
    --start-date 2023-01-01 \
    --end-date 2023-12-31 \
    --dry-run

# Custom train/test split (80/20)
python cli.py backtest \
    --league NBA \
    --train-split 0.8 \
    --output pack_nba_80_20.json
```

**Output:**
- Console: Metrics, thresholds, reliability curves
- File: Calibration pack JSON (if `--output` specified)

---

### Command: `generate-pack`

**Purpose:** Generate calibration pack from calibration run

**Usage:**
```bash
python cli.py generate-pack \
    --league LEAGUE \
    --output PATH \
    [--start-date YYYY-MM-DD] \
    [--end-date YYYY-MM-DD] \
    [--train-split FRACTION]
```

**Options:**
- `--league`: League to calibrate - **Required**
- `--output`: Output JSON file path - **Required**
- `--start-date`: Backtest start date - Default: `2020-01-01`
- `--end-date`: Backtest end date - Default: `2024-12-31`
- `--train-split`: Train fraction - Default: `0.7`
- `--db`: Database path - Default: `data/sports_data.db`

**Examples:**

```bash
# Generate NBA calibration pack
python cli.py generate-pack \
    --league NBA \
    --output calibration_pack_nba.json

# Generate with custom date range
python cli.py generate-pack \
    --league NBA \
    --start-date 2022-01-01 \
    --end-date 2024-12-31 \
    --output pack_nba_2022_2024.json
```

**Output File Structure:**
```json
{
  "version": "1.0.0",
  "league": "NBA",
  "edge_thresholds": {
    "moneyline": 0.02,
    "spread": 0.03,
    "total": 0.03
  },
  "kelly_policy": {...},
  "metrics": {
    "roi": 0.053,
    "sharpe": 1.25,
    "hit_rate": 0.523
  },
  "reliability_bins": [...]
}
```

---

### Command: `apply-pack`

**Purpose:** Generate patch plan for applying calibration pack to OmegaSportsAgent

**Usage:**
```bash
python cli.py apply-pack \
    --pack PATH \
    --agent-repo PATH \
    [--apply]
```

**Options:**
- `--pack`: Calibration pack JSON file - **Required**
- `--agent-repo`: Path to OmegaSportsAgent repository - **Required**
- `--apply`: Actually apply changes (experimental, not implemented) - Optional

**Examples:**

```bash
# Generate patch plan (dry-run, safe)
python cli.py apply-pack \
    --pack calibration_pack_nba.json \
    --agent-repo ~/OmegaSportsAgent

# Attempt to apply (not yet implemented)
python cli.py apply-pack \
    --pack calibration_pack_nba.json \
    --agent-repo ~/OmegaSportsAgent \
    --apply
```

**Output:**
- Patch plan showing what parameters would change
- Manual application instructions
- Future: Automated application with confirmation

---

## Common Workflows

### Workflow 1: Initial Setup & Calibration

**Goal:** Set up lab and generate first calibration pack

```bash
# Step 1: Check data availability
python cli.py db-status

# Step 2: Review audit
python cli.py audit

# Step 3: Test calibration (dry-run)
python cli.py backtest --league NBA --dry-run

# Step 4: Generate calibration pack
python cli.py generate-pack \
    --league NBA \
    --output calibration_pack_nba_v1.json

# Step 5: Review pack
cat calibration_pack_nba_v1.json | jq '.metrics'

# Step 6: Generate patch plan
python cli.py apply-pack \
    --pack calibration_pack_nba_v1.json \
    --agent-repo ~/OmegaSportsAgent
```

### Workflow 2: Re-Calibration After New Data

**Goal:** Update calibration with latest data

```bash
# Step 1: Check data coverage
python cli.py db-status

# Step 2: Run calibration on recent period
python cli.py backtest \
    --league NBA \
    --start-date 2023-01-01 \
    --end-date 2024-12-31 \
    --output pack_nba_recent.json

# Step 3: Compare metrics with previous pack
jq '.metrics' pack_nba_v1.json
jq '.metrics' pack_nba_recent.json

# Step 4: If better, generate patch plan
python cli.py apply-pack \
    --pack pack_nba_recent.json \
    --agent-repo ~/OmegaSportsAgent
```

### Workflow 3: Testing Different Split Ratios

**Goal:** Find optimal train/test split

```bash
# Test 60/40 split
python cli.py backtest \
    --league NBA \
    --train-split 0.6 \
    --output pack_60_40.json

# Test 70/30 split (default)
python cli.py backtest \
    --league NBA \
    --train-split 0.7 \
    --output pack_70_30.json

# Test 80/20 split
python cli.py backtest \
    --league NBA \
    --train-split 0.8 \
    --output pack_80_20.json

# Compare results
echo "60/40:" && jq '.metrics' pack_60_40.json
echo "70/30:" && jq '.metrics' pack_70_30.json
echo "80/20:" && jq '.metrics' pack_80_20.json
```

### Workflow 4: Multi-League Calibration

**Goal:** Generate calibration packs for multiple leagues

```bash
# NBA calibration
python cli.py generate-pack \
    --league NBA \
    --output pack_nba.json

# NFL calibration (when data available)
python cli.py generate-pack \
    --league NFL \
    --output pack_nfl.json

# Compare edge thresholds
jq '.edge_thresholds' pack_nba.json
jq '.edge_thresholds' pack_nfl.json
```

---

## Advanced Usage

### Using Python Module Directly

**Alternative to CLI:** Import calibration runner as module

```python
from core.calibration_runner import CalibrationRunner

# Initialize
runner = CalibrationRunner(
    league="NBA",
    start_date="2020-01-01",
    end_date="2024-12-31",
    train_split=0.7,
    dry_run=False
)

# Run calibration
edge_thresholds, metrics, reliability_bins = runner.run_backtest()

# Generate pack
pack = runner.generate_calibration_pack(
    edge_thresholds,
    metrics,
    reliability_bins,
    "calibration_pack.json"
)

# Access results
print(f"ROI: {metrics['roi']:.1%}")
print(f"Sharpe: {metrics['sharpe']:.2f}")
print(f"Hit Rate: {metrics['hit_rate']:.1%}")
```

### Custom Calibration Parameters

**Modify default parameters in `calibration_runner.py`:**

```python
# In CalibrationRunner class
DEFAULT_EDGE_THRESHOLDS = {
    'moneyline': 0.025,  # Increase from 0.02
    'spread': 0.035,     # Increase from 0.03
    'total': 0.035,      # Increase from 0.03
    'props': 0.045       # Increase from 0.04
}

DEFAULT_KELLY_POLICY = {
    'method': 'fractional',
    'fraction': 0.2,     # Change from 0.25 (more conservative)
    'max_stake': 0.03,   # Change from 0.05
    'min_stake': 0.01
}
```

### Batch Processing

**Run multiple calibrations with shell script:**

```bash
#!/bin/bash
# batch_calibrate.sh

LEAGUES=("NBA" "NFL")
START="2020-01-01"
END="2024-12-31"

for league in "${LEAGUES[@]}"; do
  echo "Calibrating $league..."
  python cli.py generate-pack \
    --league $league \
    --start-date $START \
    --end-date $END \
    --output "pack_${league,,}.json"
done

echo "All calibrations complete!"
```

---

## Interpreting Results

### Metrics Explained

**ROI (Return on Investment)**
- Formula: `(Total Profit / Total Staked) * 100%`
- Good: >5%
- Excellent: >10%

**Sharpe Ratio**
- Formula: `(Mean Profit / Std Dev of Profits)`
- Good: >1.0
- Excellent: >2.0

**Hit Rate**
- Formula: `(Winning Bets / Total Bets) * 100%`
- Breakeven (at -110): ~52.4%
- Good: >54%
- Excellent: >56%

**Brier Score**
- Formula: `Mean of (Predicted Prob - Actual Outcome)²`
- Range: 0.0 (perfect) to 1.0 (worst)
- Good: <0.25
- Excellent: <0.15

**Max Drawdown**
- Maximum peak-to-trough loss in units
- Good: <20 units
- Acceptable: <30 units

### Edge Thresholds

**Interpreting tuned thresholds:**

```json
{
  "moneyline": 0.02,  // 2% edge required (e.g., 52% prob vs 50% market)
  "spread": 0.03,     // 3% edge required
  "total": 0.03,      // 3% edge required
  "props": 0.04       // 4% edge required (higher due to variance)
}
```

**Higher thresholds = More selective = Fewer bets but higher quality**

### Reliability Bins

**Example:**
```json
{
  "prob_range": "0.50-0.60",
  "predicted_prob": 0.55,
  "empirical_rate": 0.53,
  "count": 234,
  "calibration_error": 0.02
}
```

**Interpretation:**
- Bets predicted at 55% actually won 53% of the time
- Calibration error is 2% (good if <5%)
- 234 bets in this probability range

**Good calibration:** Predicted prob ≈ Empirical rate across all bins

---

## Troubleshooting

### Issue: No data found for date range

**Symptoms:**
```
ValueError: No training data found for period 2023-01-01 to 2023-12-31
```

**Solutions:**
1. Check data coverage: `python cli.py db-status`
2. Adjust date range to match available data
3. Use default dates (2020-2024)

### Issue: Insufficient data for calibration

**Symptoms:**
```
WARNING: Only 50 bets found, need at least 100 for reliable calibration
```

**Solutions:**
1. Increase date range (more games)
2. Lower edge threshold (more bets qualify)
3. Combine multiple market types

### Issue: Poor calibration (high Brier score)

**Symptoms:**
```
Brier Score: 0.45 (high = poor calibration)
```

**Solutions:**
1. Check if enough historical data
2. Verify odds data quality
3. Consider implementing probability transforms (isotonic regression)
4. Increase training data size

### Issue: Low ROI despite good hit rate

**Symptoms:**
```
Hit Rate: 54.2% (good)
ROI: 1.3% (low)
```

**Solutions:**
1. Check stake sizing (Kelly policy)
2. Verify odds calculation
3. Review bet selection (edge threshold too low?)
4. Check for edge decay (old calibration?)

---

## Best Practices

### 1. Always Start with Dry-Run

```bash
# Test first
python cli.py backtest --league NBA --dry-run

# Then run for real
python cli.py backtest --league NBA --output pack.json
```

### 2. Use Recent Data for Re-Calibration

```bash
# Good: Recent 2 years
python cli.py backtest \
    --start-date 2023-01-01 \
    --end-date 2024-12-31

# Less ideal: Very old data
python cli.py backtest \
    --start-date 2010-01-01 \
    --end-date 2015-12-31
```

### 3. Version Your Calibration Packs

```bash
# Use versioned filenames
python cli.py generate-pack \
    --league NBA \
    --output pack_nba_v1.0.0_20260105.json

# Keep old versions for rollback
git add pack_nba_*.json
git commit -m "Add calibration pack v1.0.0"
```

### 4. Monitor Performance Over Time

```bash
# Re-calibrate monthly
python cli.py backtest --league NBA --output pack_nba_jan.json  # Jan
python cli.py backtest --league NBA --output pack_nba_feb.json  # Feb

# Compare metrics
jq '.metrics.roi' pack_nba_*.json
```

### 5. Test Before Deploying

```bash
# 1. Generate pack
python cli.py generate-pack --league NBA --output pack_test.json

# 2. Review metrics
jq '.metrics' pack_test.json

# 3. Generate patch plan
python cli.py apply-pack --pack pack_test.json --agent-repo ~/OmegaSportsAgent

# 4. Only apply if metrics improve
```

---

## Getting Help

**Documentation:**
- [README.md](../README.md) - Project overview
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System design
- [docs/audit_repo.md](audit_repo.md) - Repo cleanup details
- [docs/integration_guide.md](integration_guide.md) - Agent integration

**CLI Help:**
```bash
# General help
python cli.py --help

# Command-specific help
python cli.py backtest --help
python cli.py generate-pack --help
python cli.py apply-pack --help
```

**Examples:**
- See `examples/` directory for Jupyter notebooks
- Review test files in `tests/` for usage patterns

---

**Last Updated:** 2026-01-05  
**Status:** ✅ Fully Implemented - Ready for Use
