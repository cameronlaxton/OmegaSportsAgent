# TASK 2: Daily Grading & Metrics Update

**Status:** ✅ COMPLETE

**Objective:** Grade all "pending" bets from the prior day, update the master bet logs, and append the day's performance to the cumulative metrics history.

---

## Quick Start

### Command Line
```bash
# Grade yesterday's pending bets
python -m omega.workflows.daily_grading

# Grade specific date
python -m omega.workflows.daily_grading --date 2026-01-06

# Save report as JSON
python -m omega.workflows.daily_grading --date 2026-01-06 --output outputs/report.json
```

### Python API
```python
from omega.workflows.daily_grading import DailyGradingWorkflow

workflow = DailyGradingWorkflow()  # Yesterday by default
report = workflow.run_complete_workflow()

print(f"Graded {report['bets_graded']} bets")
print(f"Result: {report['summary']['win_loss_record']}")
print(f"Profit/Loss: {report['summary']['total_profit_loss']}")
```

### Scheduled (Automatic)
```bash
python omega/workflows/scheduler.py results  # Runs at 3 AM ET daily
```

---

## Workflow Overview

```
┌─────────────────────────────────────┐
│ STEP 1: FETCH GAME RESULTS          │
├─────────────────────────────────────┤
│ - ESPN NBA/NFL schedule & scores    │
│ - Box score data                    │
│ - Player stats                      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ STEP 2: GRADE PENDING BETS          │
├─────────────────────────────────────┤
│ - Load predictions.json             │
│ - Find all status="pending" bets    │
│ - Match to game results             │
│ - Determine Win/Loss/Push           │
│ - Calculate profit_loss             │
└──────────────┬──────────────────────┘
               │
        ┌──────┴────────────┬──────────────┐
        ▼                   ▼              ▼
   ┌─────────┐         ┌──────────┐  ┌──────────────┐
   │STEP 3a: │         │STEP 3b:  │  │STEP 3c:      │
   │Update   │         │Update    │  │Update        │
   │.json    │         │.csv      │  │.json metrics │
   └─────────┘         └──────────┘  └──────────────┘
```

---

## Input & Output Files

### Inputs

| File | Purpose | Required |
|------|---------|----------|
| `data/logs/predictions.json` | Pending bet predictions | Yes |
| ESPN APIs | Game scores and box scores | Yes |
| NBA.com/NFL.com | Player stats for props | For props |

### Outputs

| File | Change | Purpose |
|------|--------|----------|
| `data/logs/predictions.json` | **Updated** | Status: pending → graded |
| `data/exports/BetLog.csv` | **Appended** | Daily graded bets |
| `data/logs/cumulative_metrics_report.json` | **Appended** | Daily + cumulative stats |
| `outputs/grading_report_*.json` | **Created** | Optional detailed report |

---

## Data Structures

### Input: Pending Bet (predictions.json)
```json
{
  "bet_id": "bet_12345",
  "date": "2026-01-06",
  "league": "NBA",
  "matchup": "Celtics vs Pacers",
  "bet_type": "moneyline",
  "pick": "Boston Celtics ML",
  "odds": -150,
  "stake": 100.0,
  "edge_pct": 5.2,
  "confidence": "A",
  "status": "pending"  ← This is what we look for
}
```

### Output: Graded Bet
```json
{
  "bet_id": "bet_12345",
  "date": "2026-01-06",
  "league": "NBA",
  "matchup": "Celtics vs Pacers",
  "bet_type": "moneyline",
  "pick": "Boston Celtics ML",
  "odds": -150,
  "stake": 100.0,
  "edge_pct": 5.2,
  "confidence": "A",
  
  "status": "graded",        ← Changed
  "result": "Win",           ← New
  "actual_value": 1.0,       ← New (1.0=win, 0.5=push, 0.0=loss)
  "payout": 166.67,          ← New (stake + profit)
  "profit_loss": 66.67,      ← New (stake × odds_multiplier)
  "graded_date": "2026-01-07T07:06:26Z"  ← New
}
```

### Daily Stats
```python
{
    "date": "2026-01-06",
    "total_bets_graded": 15,
    "wins": 10,
    "losses": 4,
    "pushes": 1,
    "voids": 0,
    "total_stake": 1500.0,
    "total_payout": 1666.50,
    "total_profit_loss": 166.50,
    "win_rate": 0.714,         # 10 wins / (10+4) decided
    "roi": 0.111               # 166.50 / 1500.0
}
```

---

## Bet Grading Logic

### Moneyline
```
Bet:  "Boston Celtics ML" at -150
Game: Celtics 118, Pacers 112
Result: WIN ✓
Calculation: $100 × (100 / 150) = $66.67 profit
```

### Spread
```
Bet:  "Celtics -4.5" at -110
Game: Celtics 118, Pacers 112 (diff: 6)
Result: WIN ✓ (6 > 4.5)
Calculation: $100 × (100 / 110) = $90.91 profit
```

### Total (Over/Under)
```
Bet:  "Over 220.5" at -110
Game: Total: 118 + 112 = 230
Result: WIN ✓ (230 > 220.5)
Calculation: $100 × (100 / 110) = $90.91 profit
```

### Player Props
```
Bet:  "Jayson Tatum Points Over 28.5" at -110
Game: Tatum scored 35 points
Result: WIN ✓ (35 > 28.5)
Calculation: $100 × (100 / 110) = $90.91 profit
```

---

## Workflow Report

### Console Summary
```
================================================================================
GRADING WORKFLOW SUMMARY
================================================================================
{
  "win_loss_record": "10-4",
  "total_stake": "$1500.00",
  "total_profit_loss": "$166.50",
  "roi": "11.10%",
  "win_rate": "71.43%"
}
================================================================================
```

### Full Report (JSON)
```json
{
  "workflow_date": "2026-01-07T07:06:26Z",
  "analysis_date": "2026-01-06",
  "bets_graded": 15,
  "workflow_status": "COMPLETE",
  "duration_seconds": 7.3,
  "daily_stats": {
    "date": "2026-01-06",
    "total_bets_graded": 15,
    "wins": 10,
    "losses": 4,
    "pushes": 1,
    "voids": 0,
    "total_stake": 1500.0,
    "total_payout": 1666.50,
    "total_profit_loss": 166.50,
    "win_rate": 0.714,
    "roi": 0.111
  },
  "graded_bets": [ ... ],
  "summary": {
    "win_loss_record": "10-4",
    "total_stake": "$1500.00",
    "total_profit_loss": "$166.50",
    "roi": "11.10%",
    "win_rate": "71.43%"
  }
}
```

---

## Key Features

✅ **Automatic Status Updates**
- Pending bets automatically marked as "graded" in predictions.json
- Handles Win, Loss, Push, and Void outcomes

✅ **Bet Type Support**
- Moneyline (ML)
- Spread (-4.5, +3.0)
- Total (Over/Under)
- Player Props (Points, Rebounds, Assists, etc.)

✅ **Profit/Loss Calculation**
- American odds conversion
- Push handling (return stake)
- Void handling (return stake)

✅ **Cumulative Tracking**
- BetLog.csv appends daily (never overwritten)
- cumulative_metrics_report.json tracks all days
- Automatic summary calculations

✅ **Error Handling**
- Missing games → Bet remains pending
- Missing player stats → Prop remains pending
- File errors → Graceful failure logging

---

## Scheduled Execution

Automatically runs via **omega/workflows/scheduler.py**:

```bash
# At 3:00 AM ET daily
python omega/workflows/scheduler.py results
```

Integrated with calibration system:
- Grading outcomes feed back to calibration engine
- System auto-tunes parameters based on performance
- Weekly calibration run (Sundays)

---

## File Locations

```
OmegaSportsAgent/
├── omega/
│   ├── workflows/
│   │   ├── daily_grading.py         ← Main workflow
│   │   ├── scheduler.py             ← Automatic scheduler
│   │   └── ...
│   └── ...
├── data/
│   ├── logs/
│   │   ├── predictions.json         ← Input/Output
│   │   └── cumulative_metrics_report.json ← Output
│   └── exports/
│       └── BetLog.csv               ← Output
├── docs/
│   └── DAILY_GRADING_GUIDE.md       ← Detailed guide
├── outputs/                         ← Optional reports
└── ...
```

---

## Documentation

**See [docs/DAILY_GRADING_GUIDE.md](docs/DAILY_GRADING_GUIDE.md) for:**
- Complete workflow documentation
- Step-by-step breakdown
- Data structure specifications
- Error handling & troubleshooting
- Detailed examples
- API reference

---

## Examples

### Example 1: Grade Yesterday
```bash
python -m omega.workflows.daily_grading
```

### Example 2: Grade Specific Date with Report
```bash
python -m omega.workflows.daily_grading --date 2026-01-05 --output outputs/report_01_05.json
```

### Example 3: Python API
```python
from omega.workflows.daily_grading import DailyGradingWorkflow

wf = DailyGradingWorkflow(analysis_date="2026-01-06")
report = wf.run_complete_workflow()

print(f"✓ Graded {report['bets_graded']} bets")
print(f"  Record: {report['summary']['win_loss_record']}")
print(f"  P&L: {report['summary']['total_profit_loss']}")
```

### Example 4: Scheduled (3 AM ET)
```bash
python omega/workflows/scheduler.py results
```

---

## Next Tasks

- **Task 3:** Live betting integration
- **Task 4:** Performance dashboard
- **Task 5:** Calibration & parameter tuning

---

## Support

For questions or issues, refer to [docs/DAILY_GRADING_GUIDE.md](docs/DAILY_GRADING_GUIDE.md) or run:

```bash
python -m omega.workflows.daily_grading --help
```

---

**Status:** ✅ Ready for production use
**Location:** [omega/workflows/daily_grading.py](omega/workflows/daily_grading.py)
**Last Updated:** January 7, 2026
