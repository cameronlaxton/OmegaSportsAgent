# Calibration Packs Directory

This directory contains league-specific calibration packs for OmegaSportsAgent.

## Directory Structure

```
config/calibration/
├── nba_latest.json       # Latest NBA calibration pack
├── nfl_latest.json       # Latest NFL calibration pack (to be added)
├── ncaab_latest.json     # Latest NCAAB calibration pack (to be added)
└── ncaaf_latest.json     # Latest NCAAF calibration pack (to be added)
```

## Calibration Pack Format

Each calibration pack is a JSON file with the following structure:

```json
{
  "version": "v1.0",
  "league": "NBA",
  "description": "Description of this calibration pack",
  "updated_at": "2026-01-05",
  "edge_thresholds": {
    "moneyline": 0.04,
    "spread": 0.04,
    "total": 0.04,
    "player_prop_points": 0.05,
    "player_prop_rebounds": 0.05,
    "player_prop_assists": 0.05,
    "default": 0.04
  },
  "kelly_fraction": 0.25,
  "kelly_policy": "quarter_kelly",
  "probability_transforms": {
    "default": [
      {
        "type": "shrink",
        "params": {
          "factor": 0.625
        }
      }
    ],
    "moneyline": [
      {
        "type": "shrink",
        "params": {
          "factor": 0.625
        }
      }
    ]
  },
  "metadata": {
    "source": "Validation Lab calibration run",
    "notes": "Additional notes about this calibration"
  }
}
```

## Fields Description

### Core Fields

- **version**: Semantic version of the calibration pack (e.g., "v1.0", "v1.1")
- **league**: League identifier (NBA, NFL, NCAAB, NCAAF)
- **description**: Human-readable description of this calibration
- **updated_at**: ISO date of last update (YYYY-MM-DD)

### Edge Thresholds

Edge thresholds determine the minimum edge required to place a bet for each market type.
Values are in decimal format (e.g., 0.04 = 4% edge).

Supported market types:
- `moneyline`: Straight win/loss bets
- `spread`: Point spread bets
- `total`: Over/under total points
- `player_prop_points`: Player points props
- `player_prop_rebounds`: Player rebounds props
- `player_prop_assists`: Player assists props
- `player_prop_receiving_yards`: Player receiving yards (NFL)
- `player_prop_passing_yards`: Player passing yards (NFL)
- `default`: Fallback threshold for unlisted markets

### Kelly Parameters

- **kelly_fraction**: Kelly fraction to use (0.25 = quarter-Kelly, 0.5 = half-Kelly)
- **kelly_policy**: Policy name for documentation (e.g., "quarter_kelly")

### Probability Transforms

Probability transforms adjust model probabilities before calculating edges.
Transforms are applied in sequence (chained).

Supported transform types:

**Shrink** (toward 0.5):
```json
{
  "type": "shrink",
  "params": {
    "factor": 0.625
  }
}
```
Formula: `adjusted = 0.5 + (prob - 0.5) * factor`

**Platt Scaling**:
```json
{
  "type": "platt",
  "params": {
    "A": 1.0,
    "B": 0.0
  }
}
```
Formula: `adjusted = 1 / (1 + exp(-(A * logit(prob) + B)))`

Multiple transforms can be chained:
```json
"moneyline": [
  {
    "type": "platt",
    "params": {"A": 0.9, "B": 0.1}
  },
  {
    "type": "shrink",
    "params": {"factor": 0.7}
  }
]
```

## Update Process

### 1. Generate New Calibration Pack

Use the Validation Lab calibration system to generate calibrated parameters:

```bash
# Run Validation Lab calibration
python validation_lab/calibrate.py --league NBA --output nba_v1.1.json
```

### 2. Validate Calibration Pack

Ensure the JSON format is valid and all required fields are present:

```bash
# Validate JSON
python -m json.tool config/calibration/nba_v1.1.json
```

### 3. Deploy to Latest

Copy the new calibration pack to `{league}_latest.json`:

```bash
cp config/calibration/nba_v1.1.json config/calibration/nba_latest.json
```

### 4. Version Archive (Optional)

Keep historical versions for rollback:

```bash
# Archive old version
mv config/calibration/nba_latest.json config/calibration/archive/nba_v1.0.json
```

### 5. Test Integration

Test that the new calibration pack loads correctly:

```python
from config.calibration_loader import CalibrationLoader

cal = CalibrationLoader("NBA")
print(f"Loaded version: {cal.get_version()}")
print(f"Moneyline threshold: {cal.get_edge_threshold('moneyline')}")
print(f"Kelly fraction: {cal.get_kelly_fraction()}")
```

## Loading Calibration Packs

### In Python Code

```python
from config.calibration_loader import CalibrationLoader

# Load latest NBA calibration
cal = CalibrationLoader("NBA")

# Get edge threshold
threshold = cal.get_edge_threshold("moneyline")

# Get Kelly fraction
kelly = cal.get_kelly_fraction()

# Get probability transform
transform = cal.get_probability_transform("moneyline")
if transform:
    adjusted_prob = transform(model_prob)
```

### Automatic Fallback

If a calibration pack is missing, the system automatically falls back to safe defaults:
- Edge thresholds: 4% for main markets, 5% for props
- Kelly fraction: 0.25 (quarter-Kelly)
- No probability transforms applied

## Best Practices

1. **Version Incrementing**: Increment version for each calibration update
2. **Documentation**: Add descriptive notes in `metadata.notes`
3. **Testing**: Validate new packs on historical data before deployment
4. **Backup**: Keep at least one previous version archived
5. **Consistency**: Use consistent market type naming across packs
6. **Conservative**: Start with conservative thresholds and tighten after validation

## Troubleshooting

**Calibration pack not loading?**
- Check JSON syntax with `python -m json.tool`
- Verify file permissions (must be readable)
- Check filename follows `{league}_latest.json` pattern

**Transforms not applying?**
- Verify transform type is "shrink" or "platt" (case-insensitive)
- Check params are valid (factor: 0-1, A/B: any float)
- Test transform in isolation with `cal.get_probability_transform()`

**Wrong version loading?**
- Verify `{league}_latest.json` points to correct version
- Check `updated_at` field in loaded pack
- Use `cal.get_version()` to confirm loaded version
