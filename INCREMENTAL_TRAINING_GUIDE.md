# Incremental Training Guide

## Overview
The system now uses **smart incremental training** to avoid unnecessary retraining on weekly runs.

## How It Works

### First Run (New System)
- Trains all targets on all leagues
- Saves `models/training_settings.json` with:
  - Current league list
  - Training settings (trials, estimators)
  - Training timestamp

### Subsequent Runs (Same Leagues)
- Checks if anything changed
- **SKIPS RETRAINING** if:
  - Same leagues in features file
  - Same training settings
  - Models less than 7 days old
  - Less than 500 new matches in past 7 days

### When It WILL Retrain
✅ **New leagues detected** → Trains new league models only
✅ **Old training settings format** → One-time update to new format
✅ **Training parameters changed** → Retrains with new settings
✅ **Models older than 7 days** → Full retrain
✅ **500+ new matches** → Major data update detected
✅ **FORCE_RETRAIN=1** → Manual force retrain

## Configuration

### Environment Variables in run_weekly.py

```python
os.environ["FORCE_RETRAIN"] = "0"  # Set to "1" to force retraining
```

### To Force Retrain This Week
Edit `run_weekly.py` line 22:
```python
os.environ["FORCE_RETRAIN"] = "1"  # Force retrain
```

Then run normally. After the run, change it back to `"0"`.

## What Gets Checked

1. **Leagues** - Do you have different leagues than before?
2. **Settings** - Did you change OPTUNA_TRIALS or N_ESTIMATORS?
3. **Model Age** - Are models older than 7 days?
4. **New Data** - Are there 500+ new matches?

## Expected Training Times

- **First run**: 45-75 minutes (full training)
- **Week 2+**: 5-10 minutes (load only, if same leagues)
- **With new league**: 10-20 minutes (incremental)

## Troubleshooting

### Still Retraining Every Week?
Check if:
1. You have >500 new matches in the past 7 days
   - Normal weekly data shouldn't exceed this
   - If so, manually set `FORCE_RETRAIN = "0"` and delete old `training_settings.json`

2. Models are older than 7 days
   - Just means it's been a week, normal behavior

3. `training_settings.json` is missing
   - System will retrain once to recreate it

### To Reset and Force Clean Retrain
```bash
# Delete old training files
rm -f models/*.pkl
rm -f models/*.joblib
rm -f models/training_settings.json
rm -f models/manifest.json

# Next run will do full retrain with new format
```

## Files Involved

- `incremental_trainer.py` - Smart training logic
- `models/training_settings.json` - Tracks what was trained
- `run_weekly.py` line 22 - FORCE_RETRAIN control

## Performance Summary

| Scenario | Time | Models Retrained |
|----------|------|------------------|
| First run | 45-75 min | All |
| Same leagues | 5-10 min | None (loaded) |
| 1 new league | 10-20 min | New league only |
| Forced retrain | 45-75 min | All |
| 7+ days old | 45-75 min | All |

---

**Status**: ✅ Incremental training is ENABLED
**Last Training Settings**: Check `models/training_settings.json`
