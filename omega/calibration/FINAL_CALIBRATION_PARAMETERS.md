# Final Calibration Parameters - NBA

**Generated:** 2026-01-05 12:06:47  
**Calibration Pack:** `data/experiments/backtests/calibration_pack_nba_20260105_120647.json`

---

## 📊 Calibration Summary

**Training Period:** 2019-10-22 to 2023-06-10 (6,008 games, 281,799 player props)  
**Test Period:** 2023-06-10 to 2024-12-31 (2,552 games)  
**Test Performance:** 60.0% hit rate, 28.1% ROI, 0.25 Sharpe ratio

---

## 🎯 Edge Thresholds (CALIBRATED)

These are the **fine-tuned edge thresholds** that maximize ROI:

| Market Type | Threshold | Status |
|------------|-----------|--------|
| **Moneyline** | **0.030** (3.0%) | ✅ Calibrated |
| **Spread** | **0.095** (9.5%) | ✅ Calibrated |
| **Total** | **0.010** (1.0%) | ✅ Calibrated |
| **Player Prop - Points** | **0.030** (3.0%) | ✅ Calibrated |
| **Player Prop - Rebounds** | **0.030** (3.0%) | ✅ Calibrated |
| **Player Prop - Assists** | **0.030** (3.0%) | ✅ Calibrated |

### Implementation in OmegaSportsAgent

```python
# config/thresholds.py or similar
EDGE_THRESHOLDS = {
    "moneyline": 0.03,
    "spread": 0.095,
    "total": 0.01,
    "player_prop_points": 0.03,
    "player_prop_rebounds": 0.03,
    "player_prop_assists": 0.03
}
```

---

## 📈 Probability Calibration Transforms

These transforms calibrate model probabilities to match actual outcomes:

### Moneyline
```python
{
    "method": "platt+shrink",
    "platt_coefficients": {
        "a": 0.47147183749459864,
        "b": 0.011427550415523187
    },
    "shrinkage_alpha": 0.25
}
```

### Spread
```python
{
    "method": "platt+shrink",
    "platt_coefficients": {
        "a": -0.04183747817960846,
        "b": 0.20826603472690028
    },
    "shrinkage_alpha": 0.1
}
```

### Total
```python
{
    "method": "platt+shrink",
    "platt_coefficients": {
        "a": 0.6712940825330339,
        "b": -0.08330411236872515
    },
    "shrinkage_alpha": 0.05
}
```

**Note:** Player props use the same calibration as moneyline (or implement separately if needed).

---

## 💰 Kelly Staking Policy

```python
KELLY_POLICY = {
    "method": "fractional",
    "fraction": 0.25,        # Quarter Kelly (25% of full Kelly)
    "max_stake": 0.05,       # 5% of bankroll maximum
    "min_stake": 0.01,       # 1% of bankroll minimum
    "tier_multipliers": {
        "high_confidence": 1.0,
        "medium_confidence": 0.5,
        "low_confidence": 0.25
    }
}
```

---

## 📊 Variance Scalars

```python
VARIANCE_SCALARS = {
    "NBA": 1.0,
    "NFL": 1.0,
    "global": 1.0
}
```

**Note:** These are at default values (1.0). Future calibration can optimize these.

---

## 📋 Test Performance Metrics

**Overall Performance:**
- Total Bets: 70
- Hit Rate: 60.0%
- ROI: 28.1%
- Sharpe Ratio: 0.25
- Max Drawdown: 7.26 units
- Brier Score: 0.2549

**By Market Type:**
- **Moneyline:** 22 bets, 36.4% hit rate, 11.5% ROI
- **Spread:** 22 bets, 72.7% hit rate, 39.4% ROI
- **Total:** 26 bets, 69.2% hit rate, 32.6% ROI
- **Player Props:** Calibrated but no test data available (test period had 0 props with lines)

---

## 🔧 How to Apply to OmegaSportsAgent

### Step 1: Update Edge Thresholds

Find your threshold configuration file (likely `config/thresholds.py` or similar):

```python
# Before
MONEYLINE_EDGE_THRESHOLD = 0.02
SPREAD_EDGE_THRESHOLD = 0.03
TOTAL_EDGE_THRESHOLD = 0.03
PLAYER_PROPS_EDGE_THRESHOLD = 0.04

# After (from calibration)
MONEYLINE_EDGE_THRESHOLD = 0.03
SPREAD_EDGE_THRESHOLD = 0.095
TOTAL_EDGE_THRESHOLD = 0.01
PLAYER_PROP_POINTS_THRESHOLD = 0.03
PLAYER_PROP_REBOUNDS_THRESHOLD = 0.03
PLAYER_PROP_ASSISTS_THRESHOLD = 0.03
```

### Step 2: Update Probability Calibration

If your agent has probability calibration, update the Platt coefficients and shrinkage values for each market type (see transforms above).

### Step 3: Update Kelly Policy

Update staking configuration:

```python
KELLY_FRACTION = 0.25
MAX_STAKE = 0.05
MIN_STAKE = 0.01
```

### Step 4: Test Changes

Run your agent's simulation/backtest to verify:
- Parameters are being used correctly
- No syntax errors
- Performance matches expectations

---

## 📁 Complete Calibration Pack

**Location:** `data/experiments/backtests/calibration_pack_nba_20260105_120647.json`

This JSON file contains:
- All edge thresholds (game bets + player props)
- Probability calibration transforms
- Kelly staking policy
- Variance scalars
- Performance metrics
- Reliability calibration bins
- Diagnostics

---

## ⚠️ Important Notes

1. **Player Props:** Calibrated on training data (281,799 props) but test period had 0 props with betting lines. Thresholds are calibrated but not validated on test set.

2. **Default Lines:** Player props used default betting lines based on historical averages (not real market lines). For production, fetch real betting lines from The Odds API.

3. **Test Sample Size:** Only 70 test bets total (game bets only). More data would improve confidence.

4. **Calibration Period:** Based on 2019-2024 NBA data. Monitor performance and re-calibrate if market conditions change.

---

## 🚀 Next Steps

1. **Apply parameters** to OmegaSportsAgent (see steps above)
2. **Test in simulation** before live deployment
3. **Monitor performance** and re-calibrate quarterly
4. **Fetch real betting lines** for player props when available
5. **Run calibration for other leagues** (NFL, etc.) if you bet on them

---

**Ready for deployment!** 🎉

