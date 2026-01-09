# Calibration Application Guide

**Generated:** 2026-01-05  
**Calibration Pack:** `data/experiments/backtests/calibration_pack_nba_20260105_114445.json`

---

## ✅ Player Props Calibration Status

**Current Status:** Player props calibration is **IMPLEMENTED** but requires betting line data:
- ✅ Moneyline (calibrated)
- ✅ Spread (calibrated)
- ✅ Total (calibrated)
- ⚠️ **Player Props** (framework ready, but no betting line data available)

**Player Props Implementation:**
- Calibration framework is fully implemented
- Supports: points, rebounds, assists (NBA/NCAAB) and passing_yards, rushing_yards, touchdowns (NFL/NCAAF)
- Currently uses default threshold of **0.04 (4%)** because the `player_props` table doesn't have betting lines/odds populated
- Once betting line data is added to `player_props` (over_line, over_odds, under_odds), calibration will run automatically

---

## 📍 Where Are the Calibrated Parameters?

**Location:** `data/experiments/backtests/calibration_pack_nba_20260105_114445.json`

This JSON file contains all the fine-tuned parameters from the backtest calibration.

---

## 📋 Parameters to Manually Apply

### 1. Edge Thresholds

**Location in OmegaSportsAgent:** Likely in `config/thresholds.py` or similar

```python
# From calibration pack:
edge_thresholds = {
    "moneyline": 0.03,    # 3% edge required (was 2% default)
    "spread": 0.095,      # 9.5% edge required (was 3% default)
    "total": 0.01         # 1% edge required (was 3% default)
}

# Player props (NOT calibrated - use default):
# "props": 0.04  # 4% edge required (default)
```

**What to change:**
- Update `MONEYLINE_EDGE_THRESHOLD` from `0.02` to `0.03`
- Update `SPREAD_EDGE_THRESHOLD` from `0.03` to `0.095`
- Update `TOTAL_EDGE_THRESHOLD` from `0.03` to `0.01`
- Keep `PLAYER_PROPS_EDGE_THRESHOLD` at `0.04` (not calibrated)

---

### 2. Variance Scalars

**Location in OmegaSportsAgent:** Likely in `config/variance.py` or similar

```python
# From calibration pack:
variance_scalars = {
    "NBA": 1.0,
    "NFL": 1.0,
    "global": 1.0
}
```

**What to change:**
- These are currently at default values (1.0), so no changes needed unless you had different values

---

### 3. Kelly Staking Policy

**Location in OmegaSportsAgent:** Likely in `config/staking.py` or similar

```python
# From calibration pack:
kelly_policy = {
    "method": "fractional",
    "fraction": 0.25,      # Quarter Kelly (25% of full Kelly)
    "max_stake": 0.05,     # 5% of bankroll max
    "min_stake": 0.01,     # 1% of bankroll min
    "tier_multipliers": {
        "high_confidence": 1.0,
        "medium_confidence": 0.5,
        "low_confidence": 0.25
    }
}
```

**What to change:**
- Update `KELLY_FRACTION` to `0.25` (if different)
- Update `MAX_STAKE` to `0.05` (5% of bankroll)
- Update `MIN_STAKE` to `0.01` (1% of bankroll)
- Update confidence tier multipliers if they exist

---

### 4. Probability Calibration Transforms

**Location in OmegaSportsAgent:** Likely in `config/calibration.py` or similar

These are **Platt scaling + shrinkage** transforms to calibrate model probabilities:

```python
# From calibration pack:
probability_transforms = {
    "method": "platt+shrink",
    "markets": {
        "moneyline": {
            "method": "platt+shrink",
            "platt_coefficients": {
                "a": 0.47147183749459864,
                "b": 0.011427550415523187
            },
            "shrinkage_alpha": 0.25
        },
        "spread": {
            "method": "platt+shrink",
            "platt_coefficients": {
                "a": -0.04183747817960846,
                "b": 0.20826603472690028
            },
            "shrinkage_alpha": 0.1
        },
        "total": {
            "method": "platt+shrink",
            "platt_coefficients": {
                "a": 0.6712940825330339,
                "b": -0.08330411236872515
            },
            "shrinkage_alpha": 0.05
        }
    }
}
```

**What to change:**
- If your agent has probability calibration, update the Platt coefficients (a, b) and shrinkage_alpha for each market type
- If your agent doesn't have probability calibration yet, you'll need to implement the Platt scaling + shrinkage logic

**Implementation reference:**
- See `core/calibration.py` in Validation Lab for the `apply_platt()` and `shrink_toward_market()` functions

---

## 🔧 How to Apply Parameters

### Step 1: Locate Parameter Files in OmegaSportsAgent

Find where these parameters are defined:
- Edge thresholds
- Variance scalars
- Kelly staking policy
- Probability calibration transforms (if implemented)

### Step 2: Read Current Values

Note the current values before making changes (for rollback if needed).

### Step 3: Update Parameters

Update each parameter to match the calibration pack values shown above.

### Step 4: Test Changes

Run your agent's simulation/backtest to verify:
- No syntax errors
- Parameters are being used correctly
- Performance matches expectations

### Step 5: Commit Changes

```bash
git commit -m "Apply calibration pack NBA 20260105_114445

- Updated edge thresholds (moneyline: 0.03, spread: 0.095, total: 0.01)
- Applied probability calibration transforms
- Calibration period: 2019-10-22 to 2024-12-31
- Test ROI: 28.1%, Sharpe: 0.25"
```

---

## 📊 Calibration Performance Summary

**Training Period:** 2019-10-22 to 2023-06-10 (6,008 games)  
**Test Period:** 2023-06-10 to 2024-12-31 (2,552 games)

**Test Set Results:**
- **Total Bets:** 70
- **Hit Rate:** 60.0%
- **ROI:** 28.1%
- **Sharpe Ratio:** 0.25
- **Max Drawdown:** 7.26 units
- **Brier Score:** 0.2549

**By Market Type:**
- **Moneyline:** 22 bets, 36.4% hit rate, 11.5% ROI
- **Spread:** 22 bets, 72.7% hit rate, 39.4% ROI
- **Total:** 26 bets, 69.2% hit rate, 32.6% ROI

---

## 🚀 Future: Auto-Application

There's a stub adapter at `adapters/apply_calibration.py` that will eventually:
1. Read calibration pack JSON
2. Detect current parameter values in OmegaSportsAgent
3. Generate a patch plan
4. Apply changes automatically (with confirmation)

**Status:** Not yet implemented - manual application required for now.

---

## 📝 Notes

- **Player props are NOT calibrated** - they use default 4% threshold
- Calibration is based on **NBA data only** (2019-2024)
- Parameters are optimized for **historical backtest performance**
- Monitor live performance after deployment and adjust if needed
- Consider running calibration for other leagues (NFL, etc.) if you bet on them

---

## 🔗 Related Files

- **Calibration Pack:** `data/experiments/backtests/calibration_pack_nba_20260105_114445.json`
- **Integration Guide:** `docs/integration_guide.md`
- **Calibration Runner:** `core/calibration_runner.py`
- **Calibration Functions:** `core/calibration.py`
- **Apply Adapter (Stub):** `adapters/apply_calibration.py`

