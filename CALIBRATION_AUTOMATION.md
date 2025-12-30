# Automated Calibration Setup Guide

## Overview

The calibration system can run in two modes:
1. **Prediction-Count Mode** (default): Calibrates every N predictions
2. **Time-Based Mode** (recommended): Calibrates on a schedule (daily/weekly)

## Recommended Setup: Weekly Calibration on Sundays

### Why Weekly?

**Time-based calibration on Sundays is recommended because:**

✅ **Better Sample Size**: A week of betting gives 20-50+ settled bets for meaningful analysis  
✅ **Avoid Over-Tuning**: Daily calibration can over-react to short-term variance  
✅ **Natural Cycle**: Most sports have weekly schedules (NFL on Sundays, NBA/NHL week cycles)  
✅ **Stability**: Parameters don't change too frequently, allowing you to evaluate their impact  
✅ **Less Resource Intensive**: One calibration per week vs. continuous micro-adjustments

**Prediction-count mode** (every N bets) can cause:
- ❌ Calibration during active betting (mid-week parameter changes)
- ❌ Over-fitting to recent variance
- ❌ Unpredictable timing

---

## Automated Setup Options

### Option 1: GitHub Actions (Recommended for this repo)

Create `.github/workflows/weekly-calibration.yml`:

```yaml
name: Weekly Calibration

on:
  schedule:
    # Run every Sunday at 3 AM ET (8 AM UTC)
    - cron: '0 8 * * 0'
  workflow_dispatch: # Allow manual trigger

jobs:
  calibrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run calibration
        run: |
          python omega/workflows/scheduler.py calibration
      
      - name: Commit calibration results
        run: |
          git config user.name "GitHub Actions Bot"
          git config user.email "actions@github.com"
          git add data/config/tuned_parameters.json outputs/
          git commit -m "chore: weekly calibration $(date +%Y-%m-%d)" || echo "No changes"
          git push
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Option 2: Cron Job (For servers/VPS)

Add to crontab:

```bash
# Run calibration every Sunday at 3 AM
0 3 * * 0 cd /path/to/OmegaSportsAgent && /usr/bin/python3 omega/workflows/scheduler.py calibration >> /var/log/omega_calibration.log 2>&1
```

### Option 3: Perplexity/Agent Scheduled Task

If using Perplexity Spaces or another agent platform with scheduling:

**Daily morning workflow (6 AM):**
```bash
python omega/workflows/scheduler.py morning
```

**Update bet results (3 AM daily):**
```bash
python omega/workflows/scheduler.py results
```

**Weekly calibration (Sundays at 2 AM):**
```bash
python omega/workflows/scheduler.py calibration
```

---

## Configuration

### Time-Based Mode (Recommended)

```python
from omega.calibration import AutoCalibrator, CalibrationConfig, TuningStrategy

config = CalibrationConfig(
    auto_tune_enabled=True,
    auto_tune_mode="time_based",  # KEY: Use time-based instead of count
    auto_tune_schedule="weekly",   # Options: "daily" or "weekly"
    min_samples_for_tuning=30,     # Need at least 30 settled bets
    tuning_strategy=TuningStrategy.ADAPTIVE,
    performance_window=200         # Analyze last 200 predictions
)

calibrator = AutoCalibrator(config=config)
```

### Prediction-Count Mode (Default)

```python
config = CalibrationConfig(
    auto_tune_enabled=True,
    auto_tune_mode="prediction_count",  # Trigger after N predictions
    auto_tune_frequency=100,            # Calibrate every 100 predictions
    min_samples_for_tuning=50,
    tuning_strategy=TuningStrategy.ADAPTIVE
)
```

---

## How It Works (No Manual Intervention Required)

### 1. **Making Predictions** (Automatic)

When your betting workflow runs:

```python
from omega.calibration import get_global_calibrator

calibrator = get_global_calibrator()

# Log every prediction (happens automatically in workflows)
pred_id = calibrator.log_prediction(
    prediction_type="spread",
    league="NBA",
    predicted_probability=0.58,
    edge_pct=6.5,
    stake_amount=20.0
    # ... other params
)

# Store pred_id with your bet record
# (This happens automatically when using omega.workflows.morning_bets)
```

### 2. **Updating Outcomes** (Automatic via Scheduler)

The `results` task automatically:
- Fetches game scores
- Determines bet outcomes (Win/Loss/Push)
- Calculates profit/loss
- **Updates calibration system** with outcomes

```bash
# Run this daily at 3 AM (after games complete)
python omega/workflows/scheduler.py results
```

**The result update automatically calls:**
```python
calibrator.update_outcome(
    prediction_id=pred_id,
    actual_value=actual_value,
    actual_result="Win",  # or "Loss", "Push"
    profit_loss=18.0
)
```

### 3. **Calibration** (Automatic via Scheduler)

The `calibration` task:
- Analyzes performance metrics
- Auto-tunes parameters
- Saves updated parameters
- Generates report

```bash
# Run this weekly on Sundays at 2-3 AM
python omega/workflows/scheduler.py calibration
```

---

## Integration with Existing Workflows

### Morning Bets Workflow

Already integrated! When you run:

```bash
python main.py --morning-bets --leagues NBA NFL
```

It automatically:
1. Uses calibrated parameters (`get_tuned_parameter()`)
2. Logs predictions to calibration system
3. Stores prediction IDs with bet records

### Result Updates Workflow

Enhanced to automatically update calibration:

```bash
python omega/workflows/scheduler.py results
```

Now:
1. Fetches game results
2. Updates bet outcomes
3. **Automatically updates calibration system**
4. No manual intervention needed!

---

## Monitoring & Alerts

### Performance Alerts (Automatic)

The system automatically logs warnings when:
- ROI drops below -10%
- Brier score exceeds 0.25 (poor calibration)

These appear in logs:
```
WARNING - PERFORMANCE ALERT: ROI below threshold (-12.50% < -10.00%)
WARNING - CALIBRATION ALERT: Brier score above threshold (0.268 > 0.250)
```

### Weekly Reports

After each calibration run, check:

```bash
cat outputs/calibration_report_YYYYMMDD_HHMMSS.json
```

Contains:
- Parameters adjusted
- Performance metrics (ROI, win rate, Brier score)
- Detailed breakdowns by league/type

---

## Example Automated Schedule

**Recommended weekly schedule:**

```
Monday-Saturday: Normal betting operations
  - 6:00 AM: Morning bets (uses current calibrated params)
  - 3:00 AM: Result updates (auto-updates calibration with outcomes)

Sunday:
  - 2:00 AM: Weekly calibration (analyzes week's performance, tunes params)
  - 6:00 AM: Morning bets (uses newly calibrated params)
```

---

## Testing the Setup

### 1. Test Result Updates

```bash
# This should update bet outcomes AND calibration
python omega/workflows/scheduler.py results
```

Check logs for:
```
INFO - Updating calibration system with X outcomes...
INFO - Calibration system updated with bet outcomes
```

### 2. Test Calibration

```bash
# Force a calibration run
python omega/workflows/scheduler.py calibration
```

Expected output:
```
INFO - Starting autonomous calibration...
INFO - Calibration completed:
INFO -   Parameters tuned: 2
INFO -   Current ROI: 3.45%
INFO -   Win rate: 54.23%
INFO -   Brier score: 0.187
```

### 3. Verify Parameters Updated

```bash
cat data/config/tuned_parameters.json
```

Should show updated parameter values and timestamps.

---

## FAQ

**Q: Do I need to manually call calibration functions?**  
A: No! Set up the scheduler and it runs automatically.

**Q: What if I want to disable auto-calibration temporarily?**  
A: Set `auto_tune_enabled=False` in config, or just don't run the calibration task.

**Q: Can I still manually trigger calibration?**  
A: Yes! `python omega/workflows/scheduler.py calibration` or use the API directly.

**Q: How does it track prediction IDs across the workflow?**  
A: The morning_bets workflow automatically logs predictions and stores IDs with bet records. The results workflow uses these IDs to update outcomes.

**Q: What happens if there aren't enough settled bets?**  
A: Calibration skips tuning if samples < min_samples_for_tuning (default 30).

**Q: Should I use daily or weekly calibration?**  
A: **Weekly is strongly recommended**. Daily can over-react to variance and change parameters too frequently.

---

## Summary

✅ **Zero manual intervention needed** after setup  
✅ **Weekly calibration on Sundays** recommended  
✅ **Automatic outcome tracking** via results workflow  
✅ **Parameters persist** in `data/config/tuned_parameters.json`  
✅ **System learns continuously** from historical performance  

Just set up the scheduler (GitHub Actions/cron) and the system handles everything!
